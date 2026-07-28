"""Coklu seviyeli grafik yapisi motoru.

NOT: Strateji seviyeleri jenerik kodlarla anilir (L1, L2, L3, L4, L5,
LA, LF, LG, LSU, LSD, LN). Bu isimlendirme bilinctir, degistirilmemelidir.
"""

from config import TF_LA_BASE, TF_RAY_LEVELS, TF_SR, TF_L3, SL_PERCENT
from models import Candle, DrawStructure


class StructureEngine:
    def __init__(self, tick_tolerance_l4: float = 0.0005, tick_tolerance_l5: float = 0.001):
        self.tol_l4 = tick_tolerance_l4
        self.tol_l5 = tick_tolerance_l5

    @staticmethod
    def _slope(c1: Candle, v1: float, c2: Candle, v2: float) -> float:
        dt = c2.close_time - c1.close_time
        if dt == 0:
            return 0.0
        return (v2 - v1) / dt

    def build_la(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        for c in candles:
            if c.is_red:
                out.append(DrawStructure("LA", "horizontal", tf, c.low))
        return out

    def build_l1(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        for i in range(1, len(candles)):
            c1, c2 = candles[i - 1], candles[i]
            if c1.is_green and c2.is_green:
                out.append(DrawStructure(
                    "L1", "ray", tf, c2.high,
                    slope_per_sec=self._slope(c1, c1.high, c2, c2.high),
                    anchor_time=c2.close_time,
                ))
                out.append(DrawStructure(
                    "L1", "ray", tf, c2.low,
                    slope_per_sec=self._slope(c1, c1.low, c2, c2.low),
                    anchor_time=c2.close_time,
                ))
        return out

    def build_l2(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        for i in range(1, len(candles)):
            c1, c2 = candles[i - 1], candles[i]
            if not (c1.is_green and c2.is_green):
                continue
            combos = [
                (c1.open, c2.low), (c1.open, c2.open), (c1.open, c2.close), (c1.open, c2.high),
                (c1.low, c2.open), (c1.low, c2.close), (c1.low, c2.high), (c1.low, c2.low),
            ]
            for v1, v2 in combos:
                out.append(DrawStructure(
                    "L2", "ray", tf, v2,
                    slope_per_sec=self._slope(c1, v1, c2, v2),
                    anchor_time=c2.close_time,
                ))
        return out

    def build_l3(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        for i in range(1, len(candles)):
            c1, c2 = candles[i - 1], candles[i]
            if c1.is_green and c2.is_green:
                out.append(DrawStructure("L3", "horizontal", tf, c1.low))
                out.append(DrawStructure("L3", "horizontal", tf, c2.high))
        return out

    def build_l4(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        for i in range(1, len(candles)):
            c1, c2 = candles[i - 1], candles[i]
            if c1.is_green and c2.is_green:
                if abs(c2.open - c1.close) <= c1.close * self.tol_l4:
                    out.append(DrawStructure(
                        "L4", "ray", tf, c1.close,
                        slope_per_sec=0.0, anchor_time=c2.close_time,
                    ))
        return out

    def build_l5(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        for i in range(1, len(candles)):
            c1, c2 = candles[i - 1], candles[i]
            if c1.is_red and c2.is_green:
                if abs(c2.close - c1.close) <= c1.close * self.tol_l5:
                    out.append(DrawStructure("L5", "ray", tf, c2.close, 0.0, c2.close_time))
                    out.append(DrawStructure("L5", "ray", tf, c2.open, 0.0, c2.close_time))
        return out

    def build_sr(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        for i in range(1, len(candles)):
            c1, c2 = candles[i - 1], candles[i]
            if c1.is_green and c2.is_green:
                highs_falling = c2.high < c1.high
                lows_falling = c2.low < c1.low
                if highs_falling or lows_falling:
                    out.append(DrawStructure(
                        "LSU", "ray", tf, c2.high,
                        slope_per_sec=self._slope(c1, c1.high, c2, c2.high),
                        anchor_time=c2.close_time, magnet=True,
                    ))
                    out.append(DrawStructure(
                        "LSD", "ray", tf, c2.low,
                        slope_per_sec=self._slope(c1, c1.low, c2, c2.low),
                        anchor_time=c2.close_time, magnet=False,
                    ))
        return out

    def build_fib_golden(self, atl: float, tf: str, steps: int = 5) -> list[DrawStructure]:
        out = []
        if atl is None or atl <= 0:
            return out
        for n in range(1, steps + 1):
            out.append(DrawStructure("LF", "horizontal", tf, atl * (1.618 ** n)))
            out.append(DrawStructure("LG", "horizontal", tf, atl * (2 ** n)))
        return out

    def build_new_coin(self, candles: list[Candle], tf: str) -> list[DrawStructure]:
        out = []
        if len(candles) < 2:
            return out
        c1, c2 = candles[0], candles[1]
        if not (c1.is_green and c2.is_green):
            return out
        ref = c1.low
        points = [c2.open, c2.high, c2.low, c2.close]
        for p in points:
            out.append(DrawStructure("LN", "horizontal", tf, round(ref + p, 8)))
            out.append(DrawStructure("LN", "horizontal", tf, round(abs(p - ref), 8)))
        return out

    def build_all(self, candles_by_tf: dict[str, list[Candle]], is_new_coin: bool) -> list[DrawStructure]:
        structures: list[DrawStructure] = []

        for tf in TF_LA_BASE + (["1d"] if is_new_coin else []):
            candles = candles_by_tf.get(tf, [])
            if candles:
                structures += self.build_la(candles, tf)

        for tf in TF_RAY_LEVELS:
            candles = candles_by_tf.get(tf, [])
            if len(candles) >= 2:
                structures += self.build_l1(candles, tf)
                structures += self.build_l2(candles, tf)
                structures += self.build_l4(candles, tf)
                structures += self.build_l5(candles, tf)

        for tf in TF_L3:
            candles = candles_by_tf.get(tf, [])
            if len(candles) >= 2:
                structures += self.build_l3(candles, tf)

        for tf in TF_SR:
            candles = candles_by_tf.get(tf, [])
            if len(candles) >= 2:
                structures += self.build_sr(candles, tf)

        monthly = candles_by_tf.get("1M", [])
        if monthly:
            atl = min(c.low for c in monthly)
            structures += self.build_fib_golden(atl, "1M")

        if is_new_coin:
            newest = candles_by_tf.get("1d", [])
            structures += self.build_new_coin(newest, "1d")

        return structures

    @staticmethod
    def find_candidate(candles_signal_tf: list[Candle], structures: list[DrawStructure], now_ts: float):
        if len(candles_signal_tf) < 2:
            return None
        last = candles_signal_tf[-1]
        levels = [(s, s.projected_price(now_ts)) for s in structures]

        buy_candidates = [(s, p) for s, p in levels if last.low <= p <= last.close]
        sell_candidates = [(s, p) for s, p in levels if last.close <= p <= last.high]

        def nearest(cands):
            return min(cands, key=lambda sp: abs(sp[1] - last.close))

        def next_above(price):
            above = [p for _, p in levels if p > price]
            return min(above) if above else price * 1.05

        def next_below(price):
            below = [p for _, p in levels if p < price]
            return max(below) if below else price * 0.95

        if buy_candidates:
            s, lvl = nearest(buy_candidates)
            tp = next_above(last.close)
            sl = lvl * (1 - SL_PERCENT / 100)
            return {"direction": "BUY", "level_code": s.level_code, "entry": last.close, "tp": tp, "sl": sl, "level": lvl}

        if sell_candidates:
            s, lvl = nearest(sell_candidates)
            tp = next_below(last.close)
            sl = lvl * (1 + SL_PERCENT / 100)
            return {"direction": "SELL", "level_code": s.level_code, "entry": last.close, "tp": tp, "sl": sl, "level": lvl}

        return None
