import os

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# === Mistral AI (4 key rotasyonlu) ===
MISTRAL_KEYS = [k for k in [
    os.environ.get("MISTRAL_KEY_1", ""),
    os.environ.get("MISTRAL_KEY_2", ""),
    os.environ.get("MISTRAL_KEY_3", ""),
    os.environ.get("MISTRAL_KEY_4", ""),
] if k]
MISTRAL_MODEL = "mistral-small-latest"  # Ücretsiz tier en iyi model
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# === MEXC Futures API ===
MEXC_BASE = "https://contract.mexc.com/api/v1/contract"

# === Supabase ===
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lasopnelllyvxmtywhtu.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_Ocpga-v9z4qDiOqLxKClzw_YE4TiE4M")

# === Strateji Ayarları ===
# SL artık sabit yüzde değil, en yakın seviyeye göre belirleniyor
# Fallback SL (seviye bulunamazsa)
SL_FALLBACK_PERCENT = 0.8  # Maksimum %0.8 stop
NEW_COIN_MAX_DAYS = 30  # Yeni coin süresi (gün)
NEW_COIN_DRAW_DAYS = 45  # Günlük çizim süresi (1.5 ay)

# === Risk/Reward minimum oranı ===
MIN_RR_RATIO = 2.0  # Minimum 1:2 risk/reward

# === Zaman Dilimleri ===
TF_LA_BASE = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
TF_RAY_LEVELS = ["5m", "15m", "30m", "1h", "4h", "1d", "1W"]
TF_SR = ["15m", "30m", "1h", "4h", "1d"]
TF_L3 = ["5m", "15m", "30m", "1h", "4h"]

TF_SCALP = ["1m", "5m", "15m", "30m", "1h", "4h"]
TF_SWING = ["30m", "1h", "4h", "1d", "1W"]
TF_ANALIZ = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1W", "1M"]

# === MEXC Interval Mapping ===
MEXC_INTERVALS = {
    "1m": "Min1",
    "5m": "Min5",
    "15m": "Min15",
    "30m": "Min30",
    "1h": "Min60",
    "4h": "Hour4",
    "8h": "Hour8",
    "1d": "Day1",
    "1W": "Week1",
    "1M": "Month1",
}

# === Mum Sayıları (her TF için kaç mum çekilecek) ===
CANDLE_LIMITS = {
    "1m": 100,
    "5m": 100,
    "15m": 80,
    "30m": 60,
    "1h": 50,
    "4h": 40,
    "1d": 30,
    "1W": 20,
    "1M": 12,
}
