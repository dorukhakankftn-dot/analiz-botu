"""Veri modelleri - Candle ve DrawStructure."""

from dataclasses import dataclass, field


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: float  # Unix timestamp

    @property
    def is_green(self) -> bool:
        return self.close > self.open

    @property
    def is_red(self) -> bool:
        return self.close < self.open

    @property
    def is_neutral(self) -> bool:
        return self.close == self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def total_range(self) -> float:
        return self.high - self.low

    @property
    def color(self) -> str:
        if self.is_green:
            return "yeşil"
        elif self.is_red:
            return "kırmızı"
        return "nötr"


@dataclass
class DrawStructure:
    level_code: str  # L1, L2, L3, L4, L5, LA, LF, LG, LSU, LSD, LN
    draw_type: str  # "horizontal" veya "ray"
    timeframe: str
    price: float
    slope_per_sec: float = 0.0
    anchor_time: float = 0.0
    magnet: bool = False

    def projected_price(self, now_ts: float) -> float:
        """Ray için şu anki fiyat projeksiyonu."""
        if self.draw_type == "horizontal" or self.slope_per_sec == 0.0:
            return self.price
        dt = now_ts - self.anchor_time
        return self.price + self.slope_per_sec * dt


@dataclass
class Signal:
    symbol: str
    direction: str  # "BUY" veya "SELL"
    entry: float
    tp: float
    sl: float
    level_code: str
    level_price: float
    signal_type: str  # "scalp", "swing", "analiz"
    status: str = "BEKLEMEDE"  # BEKLEMEDE, AKTIF, TP, SL, IPTAL
    tp_long: float = 0.0  # Uzun vadeli hedef (analiz için)
    analysis: str = ""  # AI analiz notu
