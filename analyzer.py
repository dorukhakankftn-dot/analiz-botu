"""Ana analiz modülü - Strateji + MEXC + AI birleştirici."""

import time
import logging
from models import Candle, DrawStructure
from strategy_engine import StructureEngine
from mexc_api import fetch_all_timeframes, get_coin_age_days, fetch_klines
from mistral_ai import MistralAI
from config import (
    TF_SCALP, TF_SWING, TF_ANALIZ,
    NEW_COIN_MAX_DAYS, NEW_COIN_DRAW_DAYS,
)

logger = logging.getLogger(__name__)
engine = StructureEngine()


def _candles_to_summary(candles_by_tf: dict[str, list[Candle]]) -> str:
    """Mum verilerini AI için özet metne çevir."""
    lines = []
    for tf, candles in candles_by_tf.items():
        if not candles:
            continue
        last = candles[-1]
        prev = candles[-2] if len(candles) >= 2 else None

        # Renk ve trend belirleme
        greens = sum(1 for c in candles[-5:] if c.is_green)
        reds = sum(1 for c in candles[-5:] if c.is_red)

        if greens >= 3:
            color = "🟢 YEŞİL"
        elif reds >= 3:
            color = "🔴 KIRMIZI"
        else:
            color = "⚪ NÖTR"

        # Son mumun detayları
        body_pct = (last.body_size / last.open * 100) if last.open > 0 else 0
        line = (
            f"[{tf}] {color} | Son: O:{last.open:.6g} H:{last.high:.6g} "
            f"L:{last.low:.6g} C:{last.close:.6g} | "
            f"Gövde: %{body_pct:.2f} | "
            f"Son 5 mum: {greens}Y/{reds}K"
        )
        lines.append(line)

    return "\n".join(lines)


def _structures_to_summary(structures: list[DrawStructure], current_price: float) -> str:
    """Strateji seviyelerini AI için özet metne çevir."""
    now = time.time()

    # Fiyata yakın seviyeleri filtrele (±%5)
    nearby = []
    for s in structures:
        projected = s.projected_price(now)
        if projected <= 0:
            continue
        distance_pct = abs(projected - current_price) / current_price * 100
        if distance_pct <= 5:
            nearby.append((s, projected, distance_pct))

    # Mesafeye göre sırala
    nearby.sort(key=lambda x: x[2])

    lines = []
    # Üst seviyeler (direnç)
    above = [(s, p, d) for s, p, d in nearby if p > current_price]
    below = [(s, p, d) for s, p, d in nearby if p <= current_price]

    lines.append(f"📍 Anlık Fiyat: {current_price:.6g}")
    lines.append("")
    lines.append("⬆️ DİRENÇ SEVİYELERİ (üstte):")
    for s, p, d in above[:8]:
        lines.append(f"  {s.level_code} [{s.timeframe}] → {p:.6g} (uzaklık: %{d:.2f})")

    lines.append("")
    lines.append("⬇️ DESTEK SEVİYELERİ (altta):")
    for s, p, d in below[:8]:
        lines.append(f"  {s.level_code} [{s.timeframe}] → {p:.6g} (uzaklık: %{d:.2f})")

    return "\n".join(lines)


def run_analysis(symbol: str, mode: str = "analiz") -> dict:
    """Ana analiz fonksiyonu.
    
    mode: "analiz", "scalp", "swing"
    Returns: {"text": str, "signal": dict|None}
    """
    # Timeframe seçimi
    if mode == "scalp":
        timeframes = TF_SCALP
    elif mode == "swing":
        timeframes = TF_SWING
    else:
        timeframes = TF_ANALIZ

    # Coin yaşını kontrol et
    coin_age = get_coin_age_days(symbol)
    is_new_coin = coin_age <= NEW_COIN_MAX_DAYS

    # Mum verilerini çek
    candles_by_tf = fetch_all_timeframes(symbol, timeframes)

    if not candles_by_tf:
        return {"text": f"❌ {symbol} için veri çekilemedi. Parite adını kontrol et.", "signal": None}

    # Yeni coin için günlük veri de ekle
    if is_new_coin and "1d" not in candles_by_tf:
        daily = fetch_klines(symbol, "1d", limit=50)
        if daily:
            candles_by_tf["1d"] = daily

    # Aylık veri (Fibonacci için)
    if "1M" not in candles_by_tf:
        monthly = fetch_klines(symbol, "1M", limit=12)
        if monthly:
            candles_by_tf["1M"] = monthly

    # Strateji seviyelerini hesapla
    structures = engine.build_all(candles_by_tf, is_new_coin)

    # Anlık fiyat
    signal_tf = "5m" if mode == "scalp" else "1h" if mode == "swing" else "15m"
    signal_candles = candles_by_tf.get(signal_tf, [])
    if not signal_candles:
        # Herhangi bir TF'den son fiyatı al
        for tf_candles in candles_by_tf.values():
            if tf_candles:
                signal_candles = tf_candles
                break

    current_price = signal_candles[-1].close if signal_candles else 0

    # Sinyal bul
    now_ts = time.time()
    candidate = engine.find_candidate(signal_candles, structures, now_ts)

    # AI analizi
    ai = MistralAI()
    candles_summary = _candles_to_summary(candles_by_tf)
    structures_summary = _structures_to_summary(structures, current_price)
    ai_analysis = ai.analyze_chart(symbol, candles_summary, structures_summary, mode)

    # Sonuç metni oluştur
    header = {
        "analiz": "📊 DETAYLI ANALİZ",
        "scalp": "⚡ SCALP ANALİZ",
        "swing": "🌊 SWING ANALİZ",
    }[mode]

    coin_status = "🆕 YENİ COİN" if is_new_coin else ""

    text = f"""
{header} - {symbol} {coin_status}
{'='*35}

{candles_summary}

{'='*35}
{structures_summary}

{'='*35}
🤖 AI DEĞERLENDİRME:
{ai_analysis}
"""

    if candidate:
        text += f"""
{'='*35}
🎯 STRATEJİ SİNYALİ:
Yön: {'📈 LONG' if candidate['direction'] == 'BUY' else '📉 SHORT'}
Seviye: {candidate['level_code']}
Giriş: {candidate['entry']:.6g}
Hedef: {candidate['tp']:.6g}
Stop: {candidate['sl']:.6g}
"""

    return {"text": text.strip(), "signal": candidate}
