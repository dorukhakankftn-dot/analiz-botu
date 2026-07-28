"""MEXC Futures API - Mum verisi çekme."""

import logging
import httpx
from config import MEXC_BASE, MEXC_INTERVALS, CANDLE_LIMITS
from models import Candle

logger = logging.getLogger(__name__)


def fetch_klines(symbol: str, tf: str, limit: int = None) -> list[Candle]:
    """MEXC Futures'dan mum verisi çeker.
    
    symbol: BTC_USDT formatında
    tf: 1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 1W, 1M
    """
    interval = MEXC_INTERVALS.get(tf)
    if not interval:
        logger.warning(f"Bilinmeyen timeframe: {tf}")
        return []

    if limit is None:
        limit = CANDLE_LIMITS.get(tf, 50)

    url = f"{MEXC_BASE}/kline/{symbol}"
    params = {"interval": interval, "limit": limit}

    try:
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()

        if not data.get("success"):
            logger.error(f"MEXC API hatası: {data}")
            return []

        kline_data = data["data"]
        candles = []

        times = kline_data.get("time", [])
        opens = kline_data.get("open", [])
        highs = kline_data.get("high", [])
        lows = kline_data.get("low", [])
        closes = kline_data.get("close", [])
        vols = kline_data.get("vol", [])

        for i in range(len(times)):
            candles.append(Candle(
                open=float(opens[i]),
                high=float(highs[i]),
                low=float(lows[i]),
                close=float(closes[i]),
                volume=float(vols[i]) if i < len(vols) else 0.0,
                close_time=float(times[i]),
            ))

        return candles

    except Exception as e:
        logger.error(f"MEXC kline çekme hatası ({symbol} {tf}): {e}")
        return []


def fetch_all_timeframes(symbol: str, timeframes: list[str]) -> dict[str, list[Candle]]:
    """Birden fazla timeframe için mum verisi çeker."""
    result = {}
    for tf in timeframes:
        candles = fetch_klines(symbol, tf)
        if candles:
            result[tf] = candles
    return result


def get_coin_age_days(symbol: str) -> float:
    """Coin'in yaklaşık yaşını gün olarak döndürür (1M mumlardan)."""
    candles = fetch_klines(symbol, "1M", limit=100)
    if not candles:
        return 9999  # Bilinmiyor, eski kabul et
    import time
    first_time = candles[0].close_time
    now = time.time()
    return (now - first_time) / 86400


def search_symbol(query: str) -> str | None:
    """Parite adını MEXC formatına çevirir. Örn: btcusdt -> BTC_USDT"""
    # Kullanıcı girişini normalize et
    q = query.upper().replace("/", "").replace("-", "").replace(" ", "")
    
    # USDT ile bitiyorsa ayır
    if q.endswith("USDT"):
        base = q[:-4]
        return f"{base}_USDT"
    
    # Yoksa USDT ekle
    return f"{q}_USDT"


def validate_symbol(symbol: str) -> bool:
    """Sembolün MEXC'de mevcut olup olmadığını kontrol eder."""
    try:
        resp = httpx.get(f"{MEXC_BASE}/kline/{symbol}", params={"interval": "Min60", "limit": 1}, timeout=5)
        data = resp.json()
        return data.get("success", False) and len(data.get("data", {}).get("time", [])) > 0
    except:
        return False
