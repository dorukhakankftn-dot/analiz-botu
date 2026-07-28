"""Sinyal takip sistemi - Giriş bekle, aktif et, TP/SL kontrol et."""

import logging
import time
import json
import os
import threading
import httpx
from models import Signal
from config import MEXC_BASE, TELEGRAM_BOT_TOKEN
from mistral_ai import MistralAI

logger = logging.getLogger(__name__)

SIGNALS_FILE = os.path.join(os.path.dirname(__file__), "active_signals.json")
BOT_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


class SignalTracker:
    def __init__(self, ai: MistralAI):
        self.signals: list[dict] = []
        self.ai = ai
        self.running = False
        self._load_signals()

    def _load_signals(self):
        """Kayıtlı sinyalleri yükle."""
        try:
            if os.path.exists(SIGNALS_FILE):
                with open(SIGNALS_FILE, "r") as f:
                    self.signals = json.load(f)
        except Exception as e:
            logger.error(f"Sinyal yükleme hatası: {e}")
            self.signals = []

    def _save_signals(self):
        """Sinyalleri kaydet."""
        try:
            with open(SIGNALS_FILE, "w") as f:
                json.dump(self.signals, f, indent=2)
        except Exception as e:
            logger.error(f"Sinyal kaydetme hatası: {e}")

    def add_signal(self, chat_id: int, symbol: str, direction: str, entry: float,
                   tp: float, sl: float, level_code: str, signal_type: str,
                   tp_long: float = 0.0, analysis: str = "") -> dict:
        """Yeni sinyal ekle."""
        signal = {
            "chat_id": chat_id,
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "tp_long": tp_long,
            "level_code": level_code,
            "signal_type": signal_type,
            "status": "BEKLEMEDE",
            "analysis": analysis,
            "created_at": time.time(),
            "activated_at": None,
            "closed_at": None,
        }
        self.signals.append(signal)
        self._save_signals()
        return signal

    def get_active_signals(self, chat_id: int = None) -> list[dict]:
        """Aktif sinyalleri getir."""
        active = [s for s in self.signals if s["status"] in ("BEKLEMEDE", "AKTIF")]
        if chat_id:
            active = [s for s in active if s["chat_id"] == chat_id]
        return active

    def _get_current_price(self, symbol: str) -> float | None:
        """Anlık fiyat çek."""
        try:
            resp = httpx.get(f"{MEXC_BASE}/ticker?symbol={symbol}", timeout=5)
            data = resp.json()
            if data.get("success") and data.get("data"):
                return float(data["data"].get("lastPrice", 0))
        except:
            pass
        return None

    def _send_notification(self, chat_id: int, text: str):
        """Telegram bildirimi gönder."""
        try:
            httpx.post(
                f"{BOT_API}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Bildirim hatası: {e}")

    def check_signals(self):
        """Tüm aktif sinyalleri kontrol et."""
        changed = False
        for signal in self.signals:
            if signal["status"] not in ("BEKLEMEDE", "AKTIF"):
                continue

            price = self._get_current_price(signal["symbol"])
            if price is None:
                continue

            # BEKLEMEDE -> Giriş fiyatına geldi mi?
            if signal["status"] == "BEKLEMEDE":
                if signal["direction"] == "BUY":
                    if price <= signal["entry"]:
                        signal["status"] = "AKTIF"
                        signal["activated_at"] = time.time()
                        changed = True
                        self._send_notification(
                            signal["chat_id"],
                            f"🟢 <b>SİNYAL AKTİF!</b>\n"
                            f"📊 {signal['symbol']}\n"
                            f"📈 {signal['direction']} @ {price}\n"
                            f"🎯 TP: {signal['tp']}\n"
                            f"🛑 SL: {signal['sl']}"
                        )
                else:  # SELL
                    if price >= signal["entry"]:
                        signal["status"] = "AKTIF"
                        signal["activated_at"] = time.time()
                        changed = True
                        self._send_notification(
                            signal["chat_id"],
                            f"🔴 <b>SİNYAL AKTİF!</b>\n"
                            f"📊 {signal['symbol']}\n"
                            f"📉 {signal['direction']} @ {price}\n"
                            f"🎯 TP: {signal['tp']}\n"
                            f"🛑 SL: {signal['sl']}"
                        )

            # AKTIF -> TP veya SL'e geldi mi?
            elif signal["status"] == "AKTIF":
                if signal["direction"] == "BUY":
                    if price >= signal["tp"]:
                        signal["status"] = "TP"
                        signal["closed_at"] = time.time()
                        changed = True
                        self._send_notification(
                            signal["chat_id"],
                            f"✅ <b>HEDEF GELDİ!</b> 🎉\n"
                            f"📊 {signal['symbol']}\n"
                            f"📈 BUY @ {signal['entry']} → {price}\n"
                            f"💰 Kar: %{((price - signal['entry']) / signal['entry'] * 100):.2f}"
                        )
                    elif price <= signal["sl"]:
                        signal["status"] = "SL"
                        signal["closed_at"] = time.time()
                        changed = True
                        # AI hata analizi
                        error_analysis = self.ai.analyze_error(
                            json.dumps(signal, default=str),
                            f"STOP LOSS - Fiyat {price}'a düştü"
                        )
                        self._send_notification(
                            signal["chat_id"],
                            f"🛑 <b>STOP LOSS!</b>\n"
                            f"📊 {signal['symbol']}\n"
                            f"📈 BUY @ {signal['entry']} → SL @ {price}\n"
                            f"💸 Zarar: %{((signal['entry'] - price) / signal['entry'] * 100):.2f}\n\n"
                            f"🤖 <b>AI Hata Analizi:</b>\n{error_analysis[:500]}"
                        )

                else:  # SELL
                    if price <= signal["tp"]:
                        signal["status"] = "TP"
                        signal["closed_at"] = time.time()
                        changed = True
                        self._send_notification(
                            signal["chat_id"],
                            f"✅ <b>HEDEF GELDİ!</b> 🎉\n"
                            f"📊 {signal['symbol']}\n"
                            f"📉 SELL @ {signal['entry']} → {price}\n"
                            f"💰 Kar: %{((signal['entry'] - price) / signal['entry'] * 100):.2f}"
                        )
                    elif price >= signal["sl"]:
                        signal["status"] = "SL"
                        signal["closed_at"] = time.time()
                        changed = True
                        error_analysis = self.ai.analyze_error(
                            json.dumps(signal, default=str),
                            f"STOP LOSS - Fiyat {price}'a çıktı"
                        )
                        self._send_notification(
                            signal["chat_id"],
                            f"🛑 <b>STOP LOSS!</b>\n"
                            f"📊 {signal['symbol']}\n"
                            f"📉 SELL @ {signal['entry']} → SL @ {price}\n"
                            f"💸 Zarar: %{((price - signal['entry']) / signal['entry'] * 100):.2f}\n\n"
                            f"🤖 <b>AI Hata Analizi:</b>\n{error_analysis[:500]}"
                        )

        if changed:
            self._save_signals()

    def start_tracking(self):
        """Arka planda sinyal takibi başlat."""
        if self.running:
            return
        self.running = True

        def _loop():
            while self.running:
                try:
                    self.check_signals()
                except Exception as e:
                    logger.error(f"Sinyal takip hatası: {e}")
                time.sleep(10)  # Her 10 saniyede kontrol

        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        logger.info("Sinyal takip sistemi başlatıldı.")

    def stop_tracking(self):
        """Sinyal takibini durdur."""
        self.running = False
