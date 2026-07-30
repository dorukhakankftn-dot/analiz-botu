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
from mexc_api import search_symbol, validate_symbol, fetch_klines
from alarm_system import AlarmSystem
from backtest import run_backtest
from daily_report import send_report
from chart_visual import generate_chart
from strategy_engine import StructureEngine
import supabase_db as db

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
alarm_system = AlarmSystem()
chat_sessions: dict[int, list[dict]] = {}
registered_chats: set[int] = set()  # Günlük rapor alacak chatler

BOT_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

# Güven eşiği - %70 altı sinyal gönderilmez
CONFIDENCE_THRESHOLD = 70


# ============ TELEGRAM HELPERS ============

def send_message(chat_id: int, text: str, parse_mode: str = None):
    """Telegram mesaj gönder. Uzun mesajları böl."""
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            _send_single(chat_id, part, parse_mode)
            time.sleep(0.3)
    else:
        _send_single(chat_id, text, parse_mode)


def _send_single(chat_id: int, text: str, parse_mode: str = None):
    try:
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        httpx.post(f"{BOT_API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Mesaj gönderme hatası: {e}")


def send_photo(chat_id: int, photo_bytes, caption: str = ""):
    """Telegram fotoğraf gönder."""
    try:
        files = {"photo": ("chart.png", photo_bytes, "image/png")}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption[:1024]
        httpx.post(f"{BOT_API}/sendPhoto", data=data, files=files, timeout=15)
    except Exception as e:
        logger.error(f"Fotoğraf gönderme hatası: {e}")


def send_typing(chat_id: int):
    try:
        httpx.post(f"{BOT_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except:
        pass


# ============ KOMUT İŞLEYİCİLER ============

def handle_start(chat_id: int):
    registered_chats.add(chat_id)
    send_message(chat_id, """🤖 MEXC Futures Analiz Botu v2.0

📊 ANALİZ:
/analiz [parite] - Detaylı analiz (tüm TF'ler)
/scalp [parite] - Scalp sinyal (1m-1h)
/swing [parite] - Swing sinyal (30m-1W)

📈 TAKİP:
/sinyaller - Aktif sinyalleri göster
/istatistik - Win rate, kar/zarar istatistikleri
/alarm [parite] [fiyat] - Fiyat alarmı kur
/alarmlar - Aktif alarmları göster

🔬 TEST:
/backtest [parite] [mod] - Geçmiş veride test
/hata_tara - Bot sağlık kontrolü

🤖 AI:
/protrader_ai - AI sohbet başlat
/stop_chat - AI sohbet bitir
/rapor - Manuel piyasa raporu

/help - Detaylı yardım

📡 Günlük rapor 07:00 ve 19:00'da otomatik gelir.""")


def handle_help(chat_id: int):
    send_message(chat_id, """📖 DETAYLI KILAVUZ

/analiz btcusdt
→ Tüm TF'leri analiz eder, seviye çizer
→ Yeşil/Kırmızı/Nötr sınıflandırma
→ Grafik resmi + AI değerlendirme
→ Güven %70+ ise sinyal verir

/scalp ethusdt
→ 1m-5m-15m-30m-1h odaklı
→ Dar stop, geniş hedef (min R/R 1:2)
→ Trailing stop: TP1'de SL girişe çekilir

/swing solusdt
→ 30m-1h-4h-1d-1W odaklı
→ Orta vadeli, geniş hedefler

/alarm BTCUSDT 70000
→ Fiyat 70000'e gelince bildirim

/backtest btcusdt scalp
→ Son 200 mumda strateji testi
→ Modlar: scalp, swing, analiz

/rapor
→ Piyasa durumu + en iyi 2 fırsat

SİNYAL TAKİP SİSTEMİ:
1. Sinyal oluşur → BEKLEMEDE
2. Fiyat girişe gelir → AKTİF (bildirim)
3. TP1'e gelir → SL girişe çekilir (trailing)
4. TP2'ye gelir → HEDEF GELDİ! 🎉
5. SL olursa → AI hata analizi + ders çıkarma

NOT: Güven %70 altı sinyaller gönderilmez.""")


def handle_analiz(chat_id: int, args: str):
    if not args.strip():
        send_message(chat_id, "❌ Parite adı gerekli.\nÖrnek: /analiz btcusdt")
        return

    symbol = search_symbol(args.strip())
    send_typing(chat_id)
    send_message(chat_id, f"🔍 {symbol} analiz ediliyor...")

    if not validate_symbol(symbol):
        send_message(chat_id, f"❌ {symbol} MEXC Futures'da bulunamadı.")
        return

    send_typing(chat_id)
    result = run_analysis(symbol, mode="analiz")
    send_message(chat_id, result["text"])

    # Grafik gönder
    _send_chart(chat_id, symbol, "4h", result.get("signal"))

    if result["signal"]:
        sig = result["signal"]
        confidence = sig.get("rr_ratio", 0) * 25  # R/R bazlı güven tahmini
        if confidence < CONFIDENCE_THRESHOLD:
            send_message(chat_id, f"⚠️ Güven oranı düşük (%{confidence:.0f}). Sinyal takibe alınmadı.")
            return

        tracker.add_signal(
            chat_id, symbol, sig["direction"], sig["entry"],
            sig["tp"], sig["sl"], sig["level_code"], "analiz",
            tp_long=sig.get("tp_long", 0), rr_ratio=sig.get("rr_ratio", 0)
        )
        send_message(chat_id, f"✅ Sinyal takibe alındı!\n📐 R/R: 1:{sig.get('rr_ratio', 0)}\n🎯 Güven: %{confidence:.0f}")


def handle_scalp(chat_id: int, args: str):
    if not args.strip():
        send_message(chat_id, "❌ Parite adı gerekli.\nÖrnek: /scalp btcusdt")
        return

    symbol = search_symbol(args.strip())
    send_typing(chat_id)
    send_message(chat_id, f"⚡ {symbol} scalp analizi...")

    if not validate_symbol(symbol):
        send_message(chat_id, f"❌ {symbol} bulunamadı.")
        return

    send_typing(chat_id)
    result = run_analysis(symbol, mode="scalp")
    send_message(chat_id, result["text"])

    _send_chart(chat_id, symbol, "5m", result.get("signal"))

    if result["signal"]:
        sig = result["signal"]
        confidence = sig.get("rr_ratio", 0) * 25
        if confidence < CONFIDENCE_THRESHOLD:
            send_message(chat_id, f"⚠️ Güven düşük (%{confidence:.0f}). Sinyal gönderilmedi.")
            return

        tracker.add_signal(
            chat_id, symbol, sig["direction"], sig["entry"],
            sig["tp"], sig["sl"], sig["level_code"], "scalp",
            tp_long=sig.get("tp_long", 0), rr_ratio=sig.get("rr_ratio", 0)
        )
        send_message(chat_id, f"✅ Scalp sinyali aktif!\n📐 R/R: 1:{sig.get('rr_ratio', 0)}\n🎯 Güven: %{confidence:.0f}")


def handle_swing(chat_id: int, args: str):
    if not args.strip():
        send_message(chat_id, "❌ Parite adı gerekli.\nÖrnek: /swing btcusdt")
        return

    symbol = search_symbol(args.strip())
    send_typing(chat_id)
    send_message(chat_id, f"🌊 {symbol} swing analizi...")

    if not validate_symbol(symbol):
        send_message(chat_id, f"❌ {symbol} bulunamadı.")
        return

    send_typing(chat_id)
    result = run_analysis(symbol, mode="swing")
    send_message(chat_id, result["text"])

    _send_chart(chat_id, symbol, "1h", result.get("signal"))

    if result["signal"]:
        sig = result["signal"]
        confidence = sig.get("rr_ratio", 0) * 25
        if confidence < CONFIDENCE_THRESHOLD:
            send_message(chat_id, f"⚠️ Güven düşük (%{confidence:.0f}). Sinyal gönderilmedi.")
            return

        tracker.add_signal(
            chat_id, symbol, sig["direction"], sig["entry"],
            sig["tp"], sig["sl"], sig["level_code"], "swing",
            tp_long=sig.get("tp_long", 0), rr_ratio=sig.get("rr_ratio", 0)
        )
        send_message(chat_id, f"✅ Swing sinyali aktif!\n📐 R/R: 1:{sig.get('rr_ratio', 0)}\n🎯 Güven: %{confidence:.0f}")


def _send_chart(chat_id: int, symbol: str, tf: str, signal: dict = None):
    """Grafik oluştur ve gönder."""
    try:
        candles = fetch_klines(symbol, tf, limit=50)
        if not candles:
            return

        entry = signal.get("entry") if signal else None
        tp = signal.get("tp") if signal else None
        sl = signal.get("sl") if signal else None
        tp_long = signal.get("tp_long") if signal else None

        # Seviyeleri hesapla
        engine = StructureEngine()
        structures = engine.build_all({tf: candles}, is_new_coin=False)

        chart = generate_chart(candles, structures, entry, tp, sl, tp_long, symbol, tf)
        if chart:
            send_photo(chat_id, chart, f"📊 {symbol} - {tf}")
    except Exception as e:
        logger.error(f"Grafik gönderme hatası: {e}")


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
            f"   R/R: 1:{s.get('rr_ratio', '?')} | Durum: {s['status']}\n"
        )
    send_message(chat_id, text)


def handle_istatistik(chat_id: int):
    stats = db.get_signal_stats(str(chat_id))
    lessons = db.get_error_lessons(limit=5)

    text = "📊 SİNYAL İSTATİSTİKLERİ\n" + "="*30 + "\n\n"
    text += f"Toplam Sinyal: {stats['total']}\n"
    text += f"✅ TP: {stats['tp']}\n"
    text += f"🛑 SL: {stats['sl']}\n"
    text += f"⏳ Aktif: {stats['active']}\n"
    text += f"📈 Win Rate: %{stats['win_rate']}\n"
    text += f"💰 Ort. Kar: %{stats['avg_profit']}\n"
    text += f"💸 Ort. Zarar: %{stats['avg_loss']}\n"

    if lessons:
        text += "\n\n🧠 SON DERSLER:\n" + "-"*25 + "\n"
        for lesson in lessons[:3]:
            text += f"\n• {lesson.get('content', '')[:150]}\n"

    send_message(chat_id, text)


def handle_alarm(chat_id: int, args: str):
    """Alarm kur."""
    parts = args.strip().split()
    if len(parts) < 2:
        send_message(chat_id, "❌ Kullanım: /alarm [parite] [fiyat]\nÖrnek: /alarm btcusdt 70000")
        return

    symbol = search_symbol(parts[0])
    try:
        target = float(parts[1])
    except ValueError:
        send_message(chat_id, "❌ Geçersiz fiyat.")
        return

    alarm = alarm_system.add_alarm(chat_id, symbol, target)
    direction = "⬆️ üstüne çıkınca" if alarm["direction"] == "above" else "⬇️ altına inince"
    send_message(chat_id, f"🔔 Alarm kuruldu!\n📊 {symbol}\n💰 {target:.6g} {direction}")


def handle_alarmlar(chat_id: int):
    """Aktif alarmları listele."""
    alarms = alarm_system.get_alarms(chat_id)
    if not alarms:
        send_message(chat_id, "📭 Aktif alarm yok.")
        return

    text = "🔔 AKTİF ALARMLAR:\n" + "="*30 + "\n"
    for i, a in enumerate(alarms, 1):
        direction = "⬆️" if a["direction"] == "above" else "⬇️"
        text += f"\n{i}. {a['symbol']} → {a['target_price']:.6g} {direction}\n"
    send_message(chat_id, text)


def handle_backtest(chat_id: int, args: str):
    """Backtest çalıştır."""
    parts = args.strip().split()
    if not parts:
        send_message(chat_id, "❌ Kullanım: /backtest [parite] [mod]\nÖrnek: /backtest btcusdt scalp\nModlar: scalp, swing, analiz")
        return

    symbol = search_symbol(parts[0])
    mode = parts[1] if len(parts) > 1 else "scalp"

    if mode not in ("scalp", "swing", "analiz"):
        mode = "scalp"

    send_typing(chat_id)
    send_message(chat_id, f"🔬 {symbol} backtest yapılıyor ({mode})...")

    if not validate_symbol(symbol):
        send_message(chat_id, f"❌ {symbol} bulunamadı.")
        return

    send_typing(chat_id)
    result = run_backtest(symbol, mode)
    send_message(chat_id, result["summary"])


def handle_rapor(chat_id: int):
    """Manuel piyasa raporu."""
    send_typing(chat_id)
    send_message(chat_id, "📋 Piyasa raporu hazırlanıyor...")
    send_typing(chat_id)
    send_report([chat_id], ai)


def handle_hata_tara(chat_id: int):
    issues = []
    ok_items = []

    if config.MISTRAL_KEYS:
        ok_items.append(f"✅ Mistral AI: {len(config.MISTRAL_KEYS)} key aktif")
    else:
        issues.append("❌ Mistral API key'leri ayarlanmamış!")

    try:
        resp = httpx.get(f"{config.MEXC_BASE}/ticker?symbol=BTC_USDT", timeout=5)
        data = resp.json()
        if data.get("success"):
            ok_items.append(f"✅ MEXC API: OK (BTC: {data['data']['lastPrice']})")
        else:
            issues.append("❌ MEXC API yanıt hatası")
    except Exception as e:
        issues.append(f"❌ MEXC API: {e}")

    if tracker.running:
        ok_items.append(f"✅ Sinyal takip: Aktif ({len(tracker.get_active_signals())} sinyal)")
    else:
        issues.append("⚠️ Sinyal takip çalışmıyor")

    if alarm_system.running:
        ok_items.append(f"✅ Alarm sistemi: Aktif ({len([a for a in alarm_system.alarms if not a['triggered']])} alarm)")
    else:
        issues.append("⚠️ Alarm sistemi çalışmıyor")

    ok_items.append("✅ Telegram Bot: Çalışıyor")
    ok_items.append(f"✅ Güven eşiği: %{CONFIDENCE_THRESHOLD}")

    # Supabase kontrol
    try:
        stats = db.get_signal_stats()
        ok_items.append(f"✅ Supabase: Bağlı ({stats['total']} kayıt)")
    except:
        issues.append("⚠️ Supabase bağlantı sorunu")

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
    chat_sessions[chat_id] = []
    send_message(chat_id, """🤖 ProTrader AI sohbet oturumu başlatıldı!

Strateji hakkında sorular sor, trade fikirleri tartış.

/stop_chat ile kapat.

Örnek:
- "BTC şu an ne yapmalıyım?"
- "L4 seviyesi ne demek?"
- "Son sinyalim neden stop oldu?"
""")


def handle_stop_chat(chat_id: int):
    if chat_id in chat_sessions:
        del chat_sessions[chat_id]
        send_message(chat_id, "👋 Sohbet kapatıldı.")
    else:
        send_message(chat_id, "ℹ️ Aktif sohbet yok.")


def handle_chat_message(chat_id: int, text: str):
    send_typing(chat_id)
    chat_sessions[chat_id].append({"role": "user", "content": text})
    if len(chat_sessions[chat_id]) > 20:
        chat_sessions[chat_id] = chat_sessions[chat_id][-20:]
    response = ai.protrader_chat(chat_sessions[chat_id])
    chat_sessions[chat_id].append({"role": "assistant", "content": response})
    send_message(chat_id, response)


# ============ UPDATE İŞLEME ============

def handle_update(update: dict):
    message = update.get("message", {})
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    if not chat_id or not text:
        return

    # Chat'i kaydet (rapor için)
    registered_chats.add(chat_id)

    if text == "/start":
        handle_start(chat_id)
    elif text == "/help":
        handle_help(chat_id)
    elif text.startswith("/analiz"):
        handle_analiz(chat_id, text[7:].strip())
    elif text.startswith("/scalp"):
        handle_scalp(chat_id, text[6:].strip())
    elif text.startswith("/swing"):
        handle_swing(chat_id, text[6:].strip())
    elif text == "/sinyaller":
        handle_sinyaller(chat_id)
    elif text == "/istatistik":
        handle_istatistik(chat_id)
    elif text.startswith("/alarm "):
        handle_alarm(chat_id, text[7:].strip())
    elif text == "/alarmlar":
        handle_alarmlar(chat_id)
    elif text.startswith("/backtest"):
        handle_backtest(chat_id, text[9:].strip())
    elif text == "/rapor":
        handle_rapor(chat_id)
    elif text == "/hata_tara":
        handle_hata_tara(chat_id)
    elif text == "/protrader_ai":
        handle_protrader_ai(chat_id)
    elif text == "/stop_chat":
        handle_stop_chat(chat_id)
    elif chat_id in chat_sessions:
        handle_chat_message(chat_id, text)
    else:
        send_message(chat_id, "Komut tanınmadı. /help yaz.")


# ============ TELEGRAM POLLING ============

def polling_loop():
    offset = 0
    logger.info("Telegram polling başlatıldı.")

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
                        logger.error(f"Update hatası: {e}")
        except httpx.TimeoutException:
            continue
        except Exception as e:
            logger.error(f"Polling hatası: {e}")
            time.sleep(3)


# ============ GÜNLÜK RAPOR SCHEDULER ============

def report_scheduler():
    """07:00 ve 19:00 TR saatinde rapor gönder."""
    last_report_hour = -1
    while True:
        try:
            # Türkiye saati (UTC+3)
            tr_time = time.gmtime(time.time() + 3 * 3600)
            current_hour = tr_time.tm_hour

            if current_hour in (7, 19) and current_hour != last_report_hour:
                last_report_hour = current_hour
                if registered_chats:
                    logger.info(f"Günlük rapor gönderiliyor ({current_hour}:00 TR)...")
                    send_report(list(registered_chats), ai)
                    logger.info("Rapor gönderildi.")

            time.sleep(60)  # Her dakika kontrol
        except Exception as e:
            logger.error(f"Rapor scheduler hatası: {e}")
            time.sleep(60)


# ============ TRAILING STOP ============

def trailing_stop_loop():
    """TP1'e gelince SL'i girişe çek."""
    while True:
        try:
            for signal in tracker.signals:
                if signal["status"] != "AKTIF":
                    continue
                if signal.get("trailing_activated"):
                    continue

                price = tracker._get_current_price(signal["symbol"])
                if price is None:
                    continue

                # TP1'e %50 yaklaştıysa SL'i girişe çek
                entry = signal["entry"]
                tp = signal["tp"]

                if signal["direction"] == "BUY":
                    halfway = entry + (tp - entry) * 0.5
                    if price >= halfway:
                        signal["sl"] = entry * 1.001  # Girişin %0.1 üstü (komisyon dahil)
                        signal["trailing_activated"] = True
                        tracker._save_signals()
                        tracker._send_notification(
                            signal["chat_id"],
                            f"🔄 <b>TRAILING STOP AKTİF!</b>\n"
                            f"📊 {signal['symbol']}\n"
                            f"SL girişe çekildi: {signal['sl']:.6g}\n"
                            f"💰 Kâr garantisi sağlandı!"
                        )
                else:  # SELL
                    halfway = entry - (entry - tp) * 0.5
                    if price <= halfway:
                        signal["sl"] = entry * 0.999
                        signal["trailing_activated"] = True
                        tracker._save_signals()
                        tracker._send_notification(
                            signal["chat_id"],
                            f"🔄 <b>TRAILING STOP AKTİF!</b>\n"
                            f"📊 {signal['symbol']}\n"
                            f"SL girişe çekildi: {signal['sl']:.6g}\n"
                            f"💰 Kâr garantisi sağlandı!"
                        )

        except Exception as e:
            logger.error(f"Trailing stop hatası: {e}")
        time.sleep(15)


# ============ MAIN ============

if __name__ == "__main__":
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN ayarlanmamış!")
        exit(1)

    # Sistemleri başlat
    tracker.start_tracking()
    alarm_system.start()

    # Arka plan thread'leri
    threading.Thread(target=polling_loop, daemon=True).start()
    threading.Thread(target=report_scheduler, daemon=True).start()
    threading.Thread(target=trailing_stop_loop, daemon=True).start()
    logger.info("Tüm sistemler başlatıldı.")

    # Flask ana thread'de (Render port binding)
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Flask port {port}...")
    flask_app.run(host="0.0.0.0", port=port)
