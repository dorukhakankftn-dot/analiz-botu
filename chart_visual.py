"""Grafik görselleştirme - Mum + seviyeler + giriş/TP/SL."""

import io
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from models import Candle, DrawStructure

logger = logging.getLogger(__name__)


def generate_chart(candles: list[Candle], structures: list[DrawStructure],
                   entry: float = None, tp: float = None, sl: float = None,
                   tp_long: float = None, symbol: str = "", tf: str = "") -> io.BytesIO | None:
    """Mum grafiği + seviyeler + sinyal çizgileri oluştur."""
    if not candles or len(candles) < 5:
        return None

    try:
        fig, ax = plt.subplots(1, 1, figsize=(12, 6))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#16213e')

        # Mumları çiz
        width = 0.6
        for i, c in enumerate(candles[-50:]):  # Son 50 mum
            color = '#00ff88' if c.is_green else '#ff4444' if c.is_red else '#888888'
            # Gövde
            body_bottom = min(c.open, c.close)
            body_height = c.body_size if c.body_size > 0 else c.close * 0.0001
            ax.bar(i, body_height, width, bottom=body_bottom, color=color, edgecolor=color, linewidth=0.5)
            # Fitiller
            ax.plot([i, i], [c.low, body_bottom], color=color, linewidth=0.8)
            ax.plot([i, i], [c.high, body_bottom + body_height], color=color, linewidth=0.8)

        num_candles = min(len(candles), 50)
        current_price = candles[-1].close

        # Seviyeleri çiz (fiyata yakın olanlar, ±%3)
        import time
        now = time.time()
        level_colors = {
            'LA': '#ffaa00', 'L1': '#00aaff', 'L2': '#0066ff',
            'L3': '#ff66ff', 'L4': '#ffffff', 'L5': '#00ffaa',
            'LSU': '#ff0000', 'LSD': '#ff6600', 'LF': '#gold',
            'LG': '#ffd700', 'LN': '#ff00ff',
        }

        drawn_levels = set()
        for s in structures:
            projected = s.projected_price(now)
            if projected <= 0:
                continue
            distance_pct = abs(projected - current_price) / current_price * 100
            if distance_pct > 3:
                continue
            # Aynı fiyata çok yakın seviye çizme
            rounded = round(projected, 4)
            if rounded in drawn_levels:
                continue
            drawn_levels.add(rounded)

            color = level_colors.get(s.level_code, '#888888')
            ax.axhline(y=projected, color=color, linestyle='--', linewidth=0.7, alpha=0.6)

        # Giriş/TP/SL çizgileri
        if entry:
            ax.axhline(y=entry, color='#ffffff', linestyle='-', linewidth=1.5, label=f'Giriş: {entry:.6g}')
        if tp:
            ax.axhline(y=tp, color='#00ff00', linestyle='-', linewidth=1.5, label=f'TP1: {tp:.6g}')
        if tp_long:
            ax.axhline(y=tp_long, color='#00cc00', linestyle='-.', linewidth=1.2, label=f'TP2: {tp_long:.6g}')
        if sl:
            ax.axhline(y=sl, color='#ff0000', linestyle='-', linewidth=1.5, label=f'SL: {sl:.6g}')

        # Stil
        ax.set_title(f'{symbol} - {tf}', color='white', fontsize=14, fontweight='bold')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('#333')
        ax.spines['top'].set_color('#333')
        ax.spines['left'].set_color('#333')
        ax.spines['right'].set_color('#333')
        ax.yaxis.label.set_color('white')
        ax.grid(True, alpha=0.1, color='white')

        if entry or tp or sl:
            legend = ax.legend(loc='upper left', facecolor='#1a1a2e', edgecolor='#333',
                             labelcolor='white', fontsize=9)

        plt.tight_layout()

        # BytesIO'ya kaydet
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf

    except Exception as e:
        logger.error(f"Grafik oluşturma hatası: {e}")
        plt.close('all')
        return None
