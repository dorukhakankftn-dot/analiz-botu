"""Günlük piyasa raporu - 07:00 ve 19:00 Türkiye saati."""

import logging
import time
import httpx
from config import MEXC_BASE, TELEGRAM_BOT_TOKEN
from mistral_ai import MistralAI

logger = logging.getLogger(__name__)
BOT_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# MEXC Futures piyasa kategorileri
MARKETS = {
    "Kripto": ["BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT"],
    "Emtia": ["XAU_USDT"],  # Altın
    "Amerikan Borsası": ["MSFTSTOCK_USDT", "CXMTSTOCK_USDT"],
}

# Hızlı tarama için top coinler
TOP_COINS = [
    "BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT",
    "DOGE_USDT", "ADA_USDT", "AVAX_USDT", "LINK_USDT", "DOT_USDT",
    "MATIC_USDT", "UNI_USDT", "ATOM_USDT", "FIL_USDT", "APT_USDT",
]


def _get_ticker(symbol: str) -> dict | None:
    """Parite ticker bilgisi."""
    try:
        resp = httpx.get(f"{MEXC_BASE}/ticker?symbol={symbol}", timeout=5)
        data = resp.json()
        if data.get("success") and data.get("data"):
            return data["data"]
    except:
        pass
    return None


def _get_24h_change(ticker: dict) -> float:
    """24 saatlik değişim yüzdesi."""
    try:
        return float(ticker.get("riseFallRate", 0)) * 100
    except:
        return 0


def _get_market_summary() -> str:
    """Piyasa özeti oluştur - API'yi yormadan."""
    lines = []

    for market_name, symbols in MARKETS.items():
        lines.append(f"\n{'='*20}")
        lines.append(f"📊 {market_name.upper()}")
        lines.append(f"{'='*20}")

        for symbol in symbols:
            ticker = _get_ticker(symbol)
            if not ticker:
                continue
            change = _get_24h_change(ticker)
            price = ticker.get("lastPrice", "?")
            emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
            lines.append(f"{emoji} {symbol.replace('_USDT','')}: ${price} ({change:+.2f}%)")
            time.sleep(0.2)  # API'yi yorma

    return "\n".join(lines)


def _find_best_opportunities() -> str:
    """En iyi 2 fırsat paritesini bul - hızlı tarama."""
    opportunities = []

    for symbol in TOP_COINS[:10]:  # Sadece ilk 10'a bak
        ticker = _get_ticker(symbol)
        if not ticker:
            continue

        change = _get_24h_change(ticker)
        volume = float(ticker.get("volume24", 0))

        # Basit skor: volatilite + hacim
        score = abs(change) * (volume / 1000000)
        opportunities.append({
            "symbol": symbol,
            "change": change,
            "price": ticker.get("lastPrice", "?"),
            "volume": volume,
            "score": score,
        })
        time.sleep(0.2)

    # Skora göre sırala
    opportunities.sort(key=lambda x: x["score"], reverse=True)
    return opportunities[:2] if opportunities else []


def generate_daily_report(ai: MistralAI) -> str:
    """Günlük rapor oluştur."""
    # Piyasa özeti
    market_summary = _get_market_summary()

    # En iyi fırsatlar
    best = _find_best_opportunities()
    best_text = ""
    if best:
        best_text = "\n\n🎯 EN İYİ 2 FIRSAT:\n"
        for i, opp in enumerate(best, 1):
            emoji = "🟢" if opp["change"] > 0 else "🔴"
            best_text += (
                f"{i}. {emoji} {opp['symbol'].replace('_USDT','')}\n"
                f"   Fiyat: ${opp['price']} | 24h: {opp['change']:+.2f}%\n"
            )

    # AI değerlendirmesi (kısa, API'yi yormadan)
    ai_prompt = f"""Piyasa durumu:
{market_summary}

Kısa ve öz değerlendir (max 3 cümle):
1. Genel piyasa yönü (hareketli mi durgun mu)
2. Hangi piyasa daha aktif
3. Bugün dikkat edilmesi gereken şey"""

    ai_comment = ai.chat(
        "Sen kısa ve öz piyasa yorumcususun. Sadece 3 cümle yaz.",
        ai_prompt
    )

    # Rapor birleştir
    hour = time.strftime("%H:%M", time.gmtime(time.time() + 3*3600))
    report = (
        f"📋 GÜNLÜK PİYASA RAPORU ({hour} TR)\n"
        f"{'='*35}\n"
        f"{market_summary}\n"
        f"{best_text}\n"
        f"\n{'='*35}\n"
        f"🤖 AI YORUM:\n{ai_comment}\n"
    )

    return report


def send_report(chat_ids: list[int], ai: MistralAI):
    """Raporu belirtilen chatlere gönder."""
    report = generate_daily_report(ai)
    for chat_id in chat_ids:
        try:
            httpx.post(
                f"{BOT_API}/sendMessage",
                json={"chat_id": chat_id, "text": report},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Rapor gönderme hatası ({chat_id}): {e}")
        time.sleep(0.5)
