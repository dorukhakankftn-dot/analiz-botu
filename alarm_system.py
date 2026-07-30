"""Fiyat alarm sistemi."""

import logging
import time
import json
import os
import threading
import httpx
from config import MEXC_BASE, TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

ALARMS_FILE = os.path.join(os.path.dirname(__file__), "alarms.json")
BOT_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


class AlarmSystem:
    def __init__(self):
        self.alarms: list[dict] = []
        self.running = False
        self._load()

    def _load(self):
        try:
            if os.path.exists(ALARMS_FILE):
                with open(ALARMS_FILE, "r") as f:
                    self.alarms = json.load(f)
        except:
            self.alarms = []

    def _save(self):
        try:
            with open(ALARMS_FILE, "w") as f:
                json.dump(self.alarms, f, indent=2)
        except:
            pass

    def add_alarm(self, chat_id: int, symbol: str, target_price: float) -> dict:
        """Alarm ekle."""
        # Mevcut fiyatı al - yön belirle
        current = self._get_price(symbol)
        direction = "above" if target_price > (current or 0) else "below"

        alarm = {
            "chat_id": chat_id,
            "symbol": symbol,
            "target_price": target_price,
            "direction": direction,
            "created_at": time.time(),
            "triggered": False,
        }
        self.alarms.append(alarm)
        self._save()
        return alarm

    def get_alarms(self, chat_id: int) -> list[dict]:
        """Aktif alarmları getir."""
        return [a for a in self.alarms if a["chat_id"] == chat_id and not a["triggered"]]

    def remove_alarm(self, chat_id: int, index: int) -> bool:
        """Alarm sil."""
        active = self.get_alarms(chat_id)
        if 0 <= index < len(active):
            active[index]["triggered"] = True
            self._save()
            return True
        return False

    def _get_price(self, symbol: str) -> float | None:
        try:
            resp = httpx.get(f"{MEXC_BASE}/ticker?symbol={symbol}", timeout=5)
            data = resp.json()
            if data.get("success") and data.get("data"):
                return float(data["data"].get("lastPrice", 0))
        except:
            pass
        return None

    def _send_notification(self, chat_id: int, text: str):
        try:
            httpx.post(
                f"{BOT_API}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
        except:
            pass

    def check_alarms(self):
        """Alarmları kontrol et."""
        changed = False
        for alarm in self.alarms:
            if alarm["triggered"]:
                continue

            price = self._get_price(alarm["symbol"])
            if price is None:
                continue

            triggered = False
            if alarm["direction"] == "above" and price >= alarm["target_price"]:
                triggered = True
            elif alarm["direction"] == "below" and price <= alarm["target_price"]:
                triggered = True

            if triggered:
                alarm["triggered"] = True
                changed = True
                direction_text = "⬆️ üstüne çıktı" if alarm["direction"] == "above" else "⬇️ altına indi"
                self._send_notification(
                    alarm["chat_id"],
                    f"🔔 <b>ALARM!</b>\n\n"
                    f"📊 {alarm['symbol']}\n"
                    f"💰 Fiyat {alarm['target_price']:.6g} {direction_text}\n"
                    f"📍 Anlık: {price:.6g}"
                )

        if changed:
            self._save()

    def start(self):
        """Alarm kontrolünü başlat."""
        if self.running:
            return
        self.running = True

        def _loop():
            while self.running:
                try:
                    self.check_alarms()
                except Exception as e:
                    logger.error(f"Alarm kontrol hatası: {e}")
                time.sleep(15)

        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        logger.info("Alarm sistemi başlatıldı.")

    def stop(self):
        self.running = False
