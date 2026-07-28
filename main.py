"""MEXC Futures Kripto Analiz Botu - Telegram + Mistral AI + Strateji Motoru."""

import logging
import os
import time
import threading
import json
import httpx
from flask import Flask

import config
from mistral_ai import MistralAI
from analyzer import run_analysis
from signal_tracker import SignalTracker
from mexc_api import search_symbol, validate_symbol

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============ FLASK (Render PORT binding) ============

flask_app = Flask(__name__)


@flask_app.route("/")
def health():
    return "OK", 200


@flask_app.route("/health")
def health_check():
    return "OK", 200


# ============ GLOBAL INSTANCES ============

ai = MistralAI()
tracker = SignalTracker(ai)
chat_sessions: dict[int, list[dict]] = {}  # ProTrader AI sohbet oturumları

BOT_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


# ============ TELEGRAM HELPERS ============

def send_message(chat_id: int, text: str, parse_mode: str = None):
    """Telegram mesaj gönder. Uzun mesajları böl."""
    if len(text) > 4000:
        # Mesajı parçalara böl
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            _send_single(chat_id, part, parse_mode)
            time.sleep(0.3)
    else:
        _send_single(chat_id, text, parse_mode)


def _send_single(chat_id: int, text: str, parse_mode: str = None):
    """Tek mesaj gönder."""
    try:
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        httpx.post(f"{BOT_API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Mesaj gönderme hatası: {e}")


def send_typing(chat_id: int):
    """Yazıyor... göster."""
    try:
        httpx.post(f"{BOT_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except:
        pass


# ============ KOMUT İŞLEYİCİLER ============

def handle_start(chat_id: int):
    send_message(chat_id, """🤖 MEXC Futures Analiz Botu

Komutlar:
/analiz [parite] - Detaylı analiz (tüm TF'ler)
/scalp [parite] - Scalp sinyal (1m-1h)
/swing [parite] - Swing sinyal (30m-1W)
/sinyaller - Aktif sinyalleri göster
/hata_tara - Bot sağlık kontrolü
/protrader_ai - AI sohbet başlat
/stop_chat - AI sohbet bitir
/help - Yardım

Örnek: /analiz btcusdt
Örnek: /scalp ethusdt
Örnek: /swing solusdt""")


def handle_help(chat_id: int):
    send_message(chat_id, """📖 KULLANIM KILAVUZU

/analiz [parite]
→ Tüm zaman dilimlerini analiz eder
→ Her TF'yi yeşil/kırmızı/nötr olarak sınıflandırır
→ Strateji seviyelerini hesaplar
→ Potansiyel giriş, kısa ve uzun vadeli hedef verir
→ Yeni coin (<30 gün) ise özel LN seviyeleri de çizer

/scalp [parite]
→ 1m, 5m, 15m, 30m, 1h (biraz 4h) odaklı
→ Nokta atışı giriş, dar stop, kısa hedef
→ Sinyal takip sistemi aktif (giriş bekle → aktif → TP/SL)

/swing [parite]
→ 30m, 1h, 4h, 1d (biraz 1W) odaklı
→ Geniş hedef, makul stop
→ Sinyal takip sistemi aktif

/sinyaller
→ Bekleyen ve aktif sinyalleri listeler

/hata_tara
→ API bağlantıları, key durumu, sinyal sistemi kontrolü

/protrader_ai
→ Strateji uzmanı AI ile sohbet başlat
→ Trade fikirleri tartış, sorular sor

/stop_chat
→ AI sohbet oturumunu kapat

Parite formatı: btcusdt, ethusdt, solusdt vb.""")


def handle_analiz(chat_id: int, args: str):
    if not args.strip():
        send_message(chat_id, "❌ Parite adı gerekli.\nÖrnek: /analiz btcusdt")
        return

    symbol = search_symbol(args.strip())
    send_typing(chat_id)
    send_message(chat_id, f"🔍 {symbol} analiz ediliyor... (tüm timeframe'ler)")

    if not validate_symbol(symbol):
        send_message(chat_id, f"❌ {symbol} MEXC Futures'da bulunamadı. Parite adını kontrol et.")
        return

    send_typing(chat_id)
    result = run_analysis(symbol, mode="analiz")
    send_message(chat_id, result["text"])

    if result["signal"]:
        sig = result["signal"]
        tracker.add_signal(
            chat_id, symbol, sig["direction"], sig["entry"],
            sig["tp"], sig["sl"], sig["level_code"], "analiz"
        )
        send_message(chat_id, "✅ Sinyal takibe alındı! Giriş fiyatına geldiğinde bildirim alacaksın.")


def handle_scalp(chat_id: int, args: str):
    if not args.strip():
        send_message(chat_id, "❌ Parite adı gerekli.\nÖrnek: /scalp btcusdt")
        return

    symbol = search_symbol(args.strip())
    send_typing(chat_id)
    send_message(chat_id, f"⚡ {symbol} scalp analizi yapılıyor...")

    if not validate_symbol(symbol):
        send_message(chat_id, f"❌ {symbol} MEXC Futures'da bulunamadı.")
        return

    send_typing(chat_id)
    result = run_analysis(symbol, mode="scalp")
    send_message(chat_id, result["text"])

    if result["signal"]:
        sig = result["signal"]
        tracker.add_signal(
            chat_id, symbol, sig["direction"], sig["entry"],
            sig["tp"], sig["sl"], sig["level_code"], "scalp"
        )
        send_message(chat_id, "✅ Scalp sinyali takibe alındı! Giriş fiyatına geldiğinde bildirim alacaksın.")


def handle_swing(chat_id: int, args: str):
    if not args.strip():
        send_message(chat_id, "❌ Parite adı gerekli.\nÖrnek: /swing btcusdt")
        return

    symbol = search_symbol(args.strip())
    send_typing(chat_id)
    send_message(chat_id, f"🌊 {symbol} swing analizi yapılıyor...")

    if not validate_symbol(symbol):
        send_message(chat_id, f"❌ {symbol} MEXC Futures'da bulunamadı.")
        return

    send_typing(chat_id)
    result = run_analysis(symbol, mode="swing")
    send_message(chat_id, result["text"])

    if result["signal"]:
        sig = result["signal"]
        tracker.add_signal(
            chat_id, symbol, sig["direction"], sig["entry"],
            sig["tp"], sig["sl"], sig["level_code"], "swing"
        )
        send_message(chat_id, "✅ Swing sinyali takibe alındı! Giriş fiyatına geldiğinde bildirim alacaksın.")


def handle_sinyaller(chat_id: int):
    active = tracker.get_active_signals(chat_id)
    if not active:
        send_message(chat_id, "📭 Aktif sinyal yok.")
        return

    text = "📋 AKTİF SİNYALLER:\n" + "="*30 + "\n"
    for i, s in enumerate(active, 1):
        status_emoji = "⏳" if s["status"] == "BEKLEMEDE" else "🟢"
        text += (
            f"\n{i}. {status_emoji} {s['symbol']} | {s['direction']} | {s['signal_type'].upper()}\n"
            f"   Giriş: {s['entry']:.6g} | TP: {s['tp']:.6g} | SL: {s['sl']:.6g}\n"
            f"   Seviye: {s['level_code']} | Durum: {s['status']}\n"
        )
    send_message(chat_id, text)


def handle_hata_tara(chat_id: int):
    """Bot sağlık kontrolü."""
    issues = []
    ok_items = []

    # Mistral key kontrolü
    if config.MISTRAL_KEYS:
        ok_items.append(f"✅ Mistral AI: {len(config.MISTRAL_KEYS)} key aktif")
    else:
        issues.append("❌ Mistral API key'leri ayarlanmamış!")

    # MEXC API kontrolü
    try:
        resp = httpx.get(f"{config.MEXC_BASE}/ticker?symbol=BTC_USDT", timeout=5)
        data = resp.json()
        if data.get("success"):
            ok_items.append(f"✅ MEXC API: Bağlantı OK (BTC: {data['data']['lastPrice']})")
        else:
            issues.append("❌ MEXC API yanıt hatası")
    except Exception as e:
        issues.append(f"❌ MEXC API bağlantı hatası: {e}")

    # Sinyal takip kontrolü
    if tracker.running:
        ok_items.append(f"✅ Sinyal takip: Aktif ({len(tracker.get_active_signals())} sinyal)")
    else:
        issues.append("⚠️ Sinyal takip sistemi çalışmıyor")

    # Telegram bot kontrolü
    ok_items.append("✅ Telegram Bot: Çalışıyor")

    text = "🔍 BOT SAĞLIK KONTROLÜ\n" + "="*30 + "\n\n"
    for item in ok_items:
        text += item + "\n"
    if issues:
        text += "\n⚠️ SORUNLAR:\n"
        for issue in issues:
            text += issue + "\n"
    else:
        text += "\n🎉 Tüm sistemler çalışıyor!"

    send_message(chat_id, text)


def handle_protrader_ai(chat_id: int):
    """AI sohbet oturumu başlat."""
    chat_sessions[chat_id] = []
    send_message(chat_id, """🤖 ProTrader AI sohbet oturumu başlatıldı!

Strateji hakkında sorular sorabilir, trade fikirleri tartışabilir, analiz isteyebilirsin.

Oturumu kapatmak için: /stop_chat

Örnek sorular:
- "BTC şu an hangi seviyede, ne yapmalıyım?"
- "L4 seviyesi ne anlama geliyor?"
- "Scalp için en iyi timeframe hangisi?"
- "Son sinyalim neden stop oldu?"
""")


def handle_stop_chat(chat_id: int):
    """AI sohbet oturumunu kapat."""
    if chat_id in chat_sessions:
        del chat_sessions[chat_id]
        send_message(chat_id, "👋 ProTrader AI sohbet oturumu kapatıldı.")
    else:
        send_message(chat_id, "ℹ️ Aktif sohbet oturumu yok.")


def handle_chat_message(chat_id: int, text: str):
    """ProTrader AI sohbet mesajı."""
    send_typing(chat_id)

    chat_sessions[chat_id].append({"role": "user", "content": text})

    # Son 10 mesajı tut
    if len(chat_sessions[chat_id]) > 20:
        chat_sessions[chat_id] = chat_sessions[chat_id][-20:]

    response = ai.protrader_chat(chat_sessions[chat_id])
    chat_sessions[chat_id].append({"role": "assistant", "content": response})

    send_message(chat_id, response)


# ============ UPDATE İŞLEME ============

def handle_update(update: dict):
    """Gelen Telegram update'ini işle."""
    message = update.get("message", {})
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    if not chat_id or not text:
        return

    # Komutları işle
    if text == "/start":
        handle_start(chat_id)
    elif text == "/help":
        handle_help(chat_id)
    elif text.startswith("/analiz"):
        args = text[7:].strip()
        handle_analiz(chat_id, args)
    elif text.startswith("/scalp"):
        args = text[6:].strip()
        handle_scalp(chat_id, args)
    elif text.startswith("/swing"):
        args = text[6:].strip()
        handle_swing(chat_id, args)
    elif text == "/sinyaller":
        handle_sinyaller(chat_id)
    elif text == "/hata_tara":
        handle_hata_tara(chat_id)
    elif text == "/protrader_ai":
        handle_protrader_ai(chat_id)
    elif text == "/stop_chat":
        handle_stop_chat(chat_id)
    elif chat_id in chat_sessions:
        # AI sohbet oturumu aktifse
        handle_chat_message(chat_id, text)
    else:
        # Bilinmeyen mesaj
        send_message(chat_id, "Komut tanınmadı. /help yazarak komutları görebilirsin.")


# ============ TELEGRAM POLLING ============

def polling_loop():
    """Manuel long polling."""
    offset = 0
    logger.info("Telegram polling başlatıldı.")

    # Eski update'leri temizle
    try:
        resp = httpx.get(f"{BOT_API}/getUpdates", params={"offset": -1, "timeout": 0}, timeout=10)
        data = resp.json()
        if data.get("ok") and data.get("result"):
            offset = data["result"][-1]["update_id"] + 1
    except:
        pass

    while True:
        try:
            resp = httpx.get(
                f"{BOT_API}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=30,
            )
            data = resp.json()

            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        handle_update(update)
                    except Exception as e:
                        logger.error(f"Update işleme hatası: {e}")

        except httpx.TimeoutException:
            continue
        except Exception as e:
            logger.error(f"Polling hatası: {e}")
            time.sleep(3)


# ============ MAIN ============

if __name__ == "__main__":
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN ayarlanmamış!")
        exit(1)

    # Sinyal takip sistemini başlat
    tracker.start_tracking()

    # Telegram bot'u arka planda başlat
    bot_thread = threading.Thread(target=polling_loop, daemon=True)
    bot_thread.start()
    logger.info("Telegram bot başlatıldı.")

    # Flask ana thread'de (Render port binding)
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Flask başlatılıyor port {port}...")
    flask_app.run(host="0.0.0.0", port=port)
