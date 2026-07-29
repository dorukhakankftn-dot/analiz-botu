"""Supabase entegrasyonu - İstatistik, AI notları, sinyal geçmişi."""

import logging
import time
import json
import httpx
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def _request(method: str, table: str, data: dict = None, params: dict = None) -> dict | list | None:
    """Supabase REST API çağrısı."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        if method == "POST":
            resp = httpx.post(url, headers=HEADERS, json=data, timeout=10)
        elif method == "GET":
            resp = httpx.get(url, headers=HEADERS, params=params, timeout=10)
        elif method == "PATCH":
            resp = httpx.patch(url, headers=HEADERS, json=data, params=params, timeout=10)
        else:
            return None

        if resp.status_code in (200, 201):
            return resp.json()
        else:
            logger.error(f"Supabase {method} {table} hatası: {resp.status_code} - {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Supabase bağlantı hatası: {e}")
        return None


# ============ SİNYAL GEÇMİŞİ ============

def save_signal(signal_data: dict) -> dict | None:
    """Sinyali veritabanına kaydet."""
    record = {
        "symbol": signal_data.get("symbol"),
        "direction": signal_data.get("direction"),
        "entry": signal_data.get("entry"),
        "tp": signal_data.get("tp"),
        "sl": signal_data.get("sl"),
        "tp_long": signal_data.get("tp_long", 0),
        "level_code": signal_data.get("level_code"),
        "signal_type": signal_data.get("signal_type"),
        "status": signal_data.get("status", "BEKLEMEDE"),
        "chat_id": str(signal_data.get("chat_id", "")),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "analysis": signal_data.get("analysis", ""),
    }
    return _request("POST", "signals", record)


def update_signal_status(signal_id: int, status: str, close_price: float = None, error_analysis: str = None):
    """Sinyal durumunu güncelle."""
    data = {
        "status": status,
        "closed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if close_price:
        data["close_price"] = close_price
    if error_analysis:
        data["error_analysis"] = error_analysis
    return _request("PATCH", "signals", data, params={"id": f"eq.{signal_id}"})


def get_signal_stats(chat_id: str = None) -> dict:
    """Sinyal istatistiklerini getir."""
    params = {"select": "*"}
    if chat_id:
        params["chat_id"] = f"eq.{chat_id}"

    signals = _request("GET", "signals", params=params)
    if not signals:
        return {"total": 0, "tp": 0, "sl": 0, "active": 0, "win_rate": 0}

    total = len(signals)
    tp_count = sum(1 for s in signals if s.get("status") == "TP")
    sl_count = sum(1 for s in signals if s.get("status") == "SL")
    active = sum(1 for s in signals if s.get("status") in ("BEKLEMEDE", "AKTIF"))
    closed = tp_count + sl_count
    win_rate = (tp_count / closed * 100) if closed > 0 else 0

    # Ortalama kar/zarar hesapla
    profits = []
    losses = []
    for s in signals:
        if s.get("status") == "TP" and s.get("entry") and s.get("close_price"):
            entry = float(s["entry"])
            close = float(s["close_price"])
            if s.get("direction") == "BUY":
                profits.append((close - entry) / entry * 100)
            else:
                profits.append((entry - close) / entry * 100)
        elif s.get("status") == "SL" and s.get("entry") and s.get("close_price"):
            entry = float(s["entry"])
            close = float(s["close_price"])
            if s.get("direction") == "BUY":
                losses.append((entry - close) / entry * 100)
            else:
                losses.append((close - entry) / entry * 100)

    avg_profit = sum(profits) / len(profits) if profits else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    return {
        "total": total,
        "tp": tp_count,
        "sl": sl_count,
        "active": active,
        "win_rate": round(win_rate, 1),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
    }


# ============ AI NOTLARI ============

def save_ai_note(note_type: str, content: str, symbol: str = None, metadata: dict = None):
    """AI'ın öğrendiği notu kaydet."""
    record = {
        "note_type": note_type,  # "error_lesson", "pattern", "strategy_update", "observation"
        "content": content,
        "symbol": symbol,
        "metadata": json.dumps(metadata) if metadata else None,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return _request("POST", "ai_notes", record)


def get_ai_notes(note_type: str = None, limit: int = 20) -> list:
    """AI notlarını getir."""
    params = {"select": "*", "order": "created_at.desc", "limit": str(limit)}
    if note_type:
        params["note_type"] = f"eq.{note_type}"
    result = _request("GET", "ai_notes", params=params)
    return result if result else []


def get_error_lessons(symbol: str = None, limit: int = 10) -> list:
    """Hata derslerini getir (AI'ın öğrendiği şeyler)."""
    params = {"select": "*", "note_type": "eq.error_lesson", "order": "created_at.desc", "limit": str(limit)}
    if symbol:
        params["symbol"] = f"eq.{symbol}"
    result = _request("GET", "ai_notes", params=params)
    return result if result else []


# ============ İSTATİSTİK KAYDI ============

def save_daily_stats(stats: dict):
    """Günlük istatistik kaydet."""
    record = {
        "date": time.strftime("%Y-%m-%d", time.gmtime()),
        "total_signals": stats.get("total", 0),
        "tp_count": stats.get("tp", 0),
        "sl_count": stats.get("sl", 0),
        "win_rate": stats.get("win_rate", 0),
        "avg_profit": stats.get("avg_profit", 0),
        "avg_loss": stats.get("avg_loss", 0),
    }
    return _request("POST", "daily_stats", record)


# ============ TABLO OLUŞTURMA SQL'LERİ ============

INIT_SQL = """
-- Supabase SQL Editor'da çalıştır:

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry NUMERIC,
    tp NUMERIC,
    sl NUMERIC,
    tp_long NUMERIC DEFAULT 0,
    close_price NUMERIC,
    level_code TEXT,
    signal_type TEXT,
    status TEXT DEFAULT 'BEKLEMEDE',
    chat_id TEXT,
    analysis TEXT,
    error_analysis TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ai_notes (
    id BIGSERIAL PRIMARY KEY,
    note_type TEXT NOT NULL,
    content TEXT NOT NULL,
    symbol TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_signals INT DEFAULT 0,
    tp_count INT DEFAULT 0,
    sl_count INT DEFAULT 0,
    win_rate NUMERIC DEFAULT 0,
    avg_profit NUMERIC DEFAULT 0,
    avg_loss NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS politikaları (anon key erişimi için)
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for anon" ON signals FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON ai_notes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON daily_stats FOR ALL USING (true) WITH CHECK (true);
"""
