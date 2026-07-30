"""Strateji backtest modülü - Geçmiş veride test."""

import logging
import time
from models import Candle, DrawStructure
from strategy_engine import StructureEngine
from mexc_api import fetch_klines
from config import TF_SCALP, TF_SWING, TF_ANALIZ, MEXC_INTERVALS

logger = logging.getLogger(__name__)
engine = StructureEngine()


def run_backtest(symbol: str, mode: str = "scalp", lookback_candles: int = 200) -> dict:
    """Geçmiş veride stratejiyi test et.
    
    Returns: {
        "total_signals": int,
        "tp_count": int,
        "sl_count": int,
        "win_rate": float,
        "avg_profit": float,
        "avg_loss": float,
        "trades": list[dict],
        "summary": str,
    }
    """
    # Ana TF seç
    if mode == "scalp":
        signal_tf = "5m"
        timeframes = ["5m", "15m", "30m", "1h"]
    elif mode == "swing":
        signal_tf = "1h"
        timeframes = ["1h", "4h", "1d"]
    else:
        signal_tf = "15m"
        timeframes = ["15m", "30m", "1h", "4h"]

    # Veri çek
    candles = fetch_klines(symbol, signal_tf, limit=lookback_candles)
    if not candles or len(candles) < 50:
        return {"total_signals": 0, "summary": "Yeterli veri yok."}

    # Diğer TF'ler
    candles_by_tf = {signal_tf: candles}
    for tf in timeframes:
        if tf != signal_tf:
            tf_candles = fetch_klines(symbol, tf, limit=100)
            if tf_candles:
                candles_by_tf[tf] = tf_candles

    # Simülasyon
    trades = []
    window = 30  # Her seferinde 30 mumla analiz

    for i in range(window, len(candles) - 10):
        # Window mumlarıyla seviye hesapla
        window_candles = candles[i-window:i]
        temp_by_tf = {signal_tf: window_candles}
        for tf in timeframes:
            if tf != signal_tf and tf in candles_by_tf:
                temp_by_tf[tf] = candles_by_tf[tf]

        structures = engine.build_all(temp_by_tf, is_new_coin=False)
        if not structures:
            continue

        # Sinyal bul
        now_ts = candles[i].close_time
        candidate = engine.find_candidate(window_candles, structures, now_ts)
        if not candidate:
            continue

        # İleriye bak - TP veya SL'e ulaşıyor mu?
        entry = candidate["entry"]
        tp = candidate["tp"]
        sl = candidate["sl"]
        direction = candidate["direction"]

        result = None
        for j in range(i+1, min(i+50, len(candles))):
            future = candles[j]
            if direction == "BUY":
                if future.high >= tp:
                    result = "TP"
                    profit = (tp - entry) / entry * 100
                    break
                elif future.low <= sl:
                    result = "SL"
                    profit = -((entry - sl) / entry * 100)
                    break
            else:  # SELL
                if future.low <= tp:
                    result = "TP"
                    profit = (entry - tp) / entry * 100
                    break
                elif future.high >= sl:
                    result = "SL"
                    profit = -((sl - entry) / entry * 100)
                    break

        if result:
            trades.append({
                "direction": direction,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "result": result,
                "profit_pct": round(profit, 2),
                "level_code": candidate["level_code"],
            })

    # İstatistikler
    total = len(trades)
    if total == 0:
        return {"total_signals": 0, "summary": "Test döneminde sinyal oluşmadı."}

    tp_count = sum(1 for t in trades if t["result"] == "TP")
    sl_count = sum(1 for t in trades if t["result"] == "SL")
    win_rate = tp_count / total * 100

    profits = [t["profit_pct"] for t in trades if t["result"] == "TP"]
    losses = [abs(t["profit_pct"]) for t in trades if t["result"] == "SL"]
    avg_profit = sum(profits) / len(profits) if profits else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    net_pnl = sum(t["profit_pct"] for t in trades)

    summary = (
        f"📊 BACKTEST SONUÇLARI - {symbol} ({mode.upper()})\n"
        f"{'='*35}\n\n"
        f"📈 Toplam Sinyal: {total}\n"
        f"✅ TP: {tp_count} | 🛑 SL: {sl_count}\n"
        f"📊 Win Rate: %{win_rate:.1f}\n"
        f"💰 Ort. Kar: %{avg_profit:.2f}\n"
        f"💸 Ort. Zarar: %{avg_loss:.2f}\n"
        f"📈 Net P&L: %{net_pnl:.2f}\n\n"
        f"En çok sinyal veren seviye: {_most_common_level(trades)}\n"
        f"Test dönemi: Son {lookback_candles} mum ({signal_tf})"
    )

    return {
        "total_signals": total,
        "tp_count": tp_count,
        "sl_count": sl_count,
        "win_rate": round(win_rate, 1),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "net_pnl": round(net_pnl, 2),
        "trades": trades[-10:],  # Son 10 trade detayı
        "summary": summary,
    }


def _most_common_level(trades: list[dict]) -> str:
    """En çok sinyal veren seviye kodunu bul."""
    counts = {}
    for t in trades:
        lc = t.get("level_code", "?")
        counts[lc] = counts.get(lc, 0) + 1
    if not counts:
        return "?"
    return max(counts, key=counts.get)
