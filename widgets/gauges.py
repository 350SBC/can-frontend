# widgets/gauges.py
"""Custom gauge widgets for the CAN dashboard."""

import math
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient
from PyQt6.QtCore import QPointF, Qt

# Import performance settings
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import GAUGE_IMMEDIATE_THRESHOLD, GAUGE_SKIP_THRESHOLD
from config.settings import GAUGE_STYLE
try:
    from config.settings import GAUGE_SWEEP_DIRECTION
except ImportError:
    GAUGE_SWEEP_DIRECTION = 'ccw'

_SWEEP_DIR = (GAUGE_SWEEP_DIRECTION or 'ccw').lower()
_CW = _SWEEP_DIR == 'cw'


class RoundGauge(QWidget):
    """A round gauge widget for displaying numeric values."""
    
    def __init__(self, parent=None, min_value=0, max_value=8000, title="RPM", num_ticks=9):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.current_value = min_value
        self.previous_value = min_value  # Track previous value to avoid unnecessary updates
        self.title = title
        self.num_ticks = num_ticks
        self.update_threshold = 0.1  # Minimum change required to trigger update
        self._setup_widget()

    def _setup_widget(self):
        """Sets up the widget properties."""
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_value(self, value):
        """Update the gauge value with ultra-responsive settings."""
        new_value = max(self.min_value, min(self.max_value, value))
        
        # Calculate change percentage
        value_range = self.max_value - self.min_value
        if value_range > 0:
            change_percentage = abs(new_value - self.current_value) / value_range
            
            # Much more sensitive immediate updates for changes > 1%
            if change_percentage > GAUGE_IMMEDIATE_THRESHOLD:
                self.current_value = new_value
                self.repaint()  # Force immediate repaint
                return
            
            # Only skip extremely tiny changes (< 0.01%)
            if change_percentage < GAUGE_SKIP_THRESHOLD:
                return
        
        # Always update for any meaningful change
        self.current_value = new_value
        self.update()  # Normal update for all other changes

    def set_range(self, min_value, max_value):
        """Update the gauge range."""
        self.min_value = min_value
        self.max_value = max_value
        # Clamp current value to new range
        self.current_value = max(self.min_value, min(self.max_value, self.current_value))
        self.update()

    def set_title(self, title):
        """Update the gauge title."""
        self.title = title
        self.update()

    def paintEvent(self, event):
        """Custom paint event to draw the gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        dimensions = self._calculate_dimensions()
        self._draw_outer_circle(painter, dimensions)
        self._draw_title(painter, dimensions)
        self._draw_scale(painter, dimensions)
        self._draw_needle(painter, dimensions)
        self._draw_center_circle(painter, dimensions)
        self._draw_value_text(painter, dimensions)

    def _calculate_dimensions(self):
        """Calculate drawing dimensions."""
        width = self.width()
        height = self.height()
        size = min(width, height)
        center = QPointF(width / 2, height / 2)
        radius = size / 2 - 20
        return {'width': width, 'height': height, 'center': center, 'radius': radius}

    def _draw_outer_circle(self, painter, dimensions):
        """Draw the outer circle of the gauge."""
        painter.setPen(QPen(QColor(150, 150, 150), 3))  # Lighter gray for dark mode
        painter.drawEllipse(dimensions['center'], dimensions['radius'], dimensions['radius'])

    def _draw_title(self, painter, dimensions):
            """Draw the gauge title (bottom)."""
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 11, QFont.Weight.Medium))
            title_rect = painter.fontMetrics().boundingRect(self.title)
            y = int(dimensions['center'].y() + dimensions['radius'] - 14)
            painter.drawText(int(dimensions['center'].x() - title_rect.width() / 2), y, self.title)

    def _draw_scale(self, painter, dimensions):
        """Draw the scale marks and numbers."""
        painter.setFont(QFont("Arial", 8))
        for i in range(self.num_ticks):
            if _CW:
                angle = -45 - (i * 270 / (self.num_ticks - 1))
            else:
                angle = 45 + (i * 270 / (self.num_ticks - 1))
            angle_rad = math.radians(angle)
            
            self._draw_tick_mark(painter, dimensions, angle_rad)
            self._draw_scale_number(painter, dimensions, angle_rad, i)

    def _draw_tick_mark(self, painter, dimensions, angle_rad):
        """Draw a single tick mark."""
        inner_radius = dimensions['radius'] - 15
        outer_radius = dimensions['radius'] - 5
        center = dimensions['center']
        
        # Create QPointF objects for the line endpoints
        p1 = QPointF(
            center.x() + inner_radius * math.cos(angle_rad),
            center.y() + inner_radius * math.sin(angle_rad)
        )
        p2 = QPointF(
            center.x() + outer_radius * math.cos(angle_rad),
            center.y() + outer_radius * math.sin(angle_rad)
        )
        
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawLine(p1, p2)

    def _draw_scale_number(self, painter, dimensions, angle_rad, index):
        """Draw a scale number."""
        number_radius = dimensions['radius'] - 25
        center = dimensions['center']
        
        num_x = center.x() + number_radius * math.cos(angle_rad)
        num_y = center.y() + number_radius * math.sin(angle_rad)
        
        painter.setPen(QPen(QColor(220, 220, 220)))  # Light gray text
        
        # Calculate the actual value for this tick
        if self.num_ticks > 1:
            value = self.min_value + (index * (self.max_value - self.min_value) / (self.num_ticks - 1))
        else:
            value = self.min_value
            
        # Format the number based on the range
        if self.max_value - self.min_value >= 1000:
            text = f"{int(value)}"
        elif self.max_value - self.min_value >= 10:
            text = f"{value:.0f}"
        else:
            text = f"{value:.1f}"
            
        text_rect = painter.fontMetrics().boundingRect(text)
        painter.drawText(
            int(num_x - text_rect.width() / 2),
            int(num_y + text_rect.height() / 4),
            text
        )

    def _draw_needle(self, painter, dimensions):
        """Draw the needle."""
        if self.max_value == self.min_value:
            value_ratio = 0
        else:
            value_ratio = (self.current_value - self.min_value) / (self.max_value - self.min_value)
        if _CW:
            needle_angle = -45 - (value_ratio * 270)
        else:
            needle_angle = 45 + (value_ratio * 270)
        needle_angle_rad = math.radians(needle_angle)
        
        needle_length = dimensions['radius'] - 30
        center = dimensions['center']
        
        # Create QPointF for needle endpoint
        needle_end = QPointF(
            center.x() + needle_length * math.cos(needle_angle_rad),
            center.y() + needle_length * math.sin(needle_angle_rad)
        )
        
        painter.setPen(QPen(QColor(255, 0, 0), 3))
        painter.drawLine(center, needle_end)

    def _draw_center_circle(self, painter, dimensions):
        """Draw the center circle."""
        painter.setBrush(QColor(100, 100, 100))
        painter.setPen(QPen(QColor(150, 150, 150)))
        painter.drawEllipse(dimensions['center'], 8, 8)

    def _draw_value_text(self, painter, dimensions):
        """Draw the current value text."""
        painter.setPen(QPen(QColor(255, 255, 0)))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        
        # Format the value based on the range
        if self.max_value - self.min_value >= 100:
            value_text = f"{int(self.current_value)}"
        elif self.max_value - self.min_value >= 10:
            value_text = f"{self.current_value:.1f}"
        else:
            value_text = f"{self.current_value:.2f}"
            
        value_rect = painter.fontMetrics().boundingRect(value_text)
        painter.drawText(
            int(dimensions['center'].x() - value_rect.width() / 2),
            int(dimensions['center'].y() + dimensions['radius'] - 40),
            value_text
        )


class ModernGauge(QWidget):
    """A more modern, flat/neo style gauge with gradient arc, colored ranges, and smooth needle.

    Performance considerations:
    - Background (static layers) are rendered to an off-screen QPixmap and reused.
    - Only dynamic layers (needle & value text) are redrawn each update.
    - Minimal overdraw; no repeated layout calculations.
    """

    def __init__(self, parent=None, min_value=0, max_value=8000, title="RPM", warning_threshold=None,
                 critical_threshold=None, num_ticks=9):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.current_value = min_value
        self.title = title
        self.num_ticks = num_ticks
        self.warning_threshold = warning_threshold if warning_threshold is not None else min_value + 0.7 * (max_value - min_value)
        self.critical_threshold = critical_threshold if critical_threshold is not None else min_value + 0.9 * (max_value - min_value)
        self._bg_cache = None  # Cached pixmap for static drawing
        self._last_size = None
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_value(self, value: float):
        new_value = max(self.min_value, min(self.max_value, value))
        rng = self.max_value - self.min_value
        if rng > 0:
            change_pct = abs(new_value - self.current_value) / rng
            if change_pct < GAUGE_SKIP_THRESHOLD:
                return
        self.current_value = new_value
        if abs(new_value - self.current_value) / (self.max_value - self.min_value + 1e-9) > GAUGE_IMMEDIATE_THRESHOLD:
            self.repaint()
        else:
            self.update()

    def _rebuild_cache_if_needed(self):
        size = (self.width(), self.height())
        if self._bg_cache is not None and self._last_size == size:
            return
        self._last_size = size
        from PyQt6.QtGui import QPixmap
        self._bg_cache = QPixmap(self.width(), self.height())
        self._bg_cache.fill(QColor(0, 0, 0, 0))
        p = QPainter(self._bg_cache)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dims = self._dims()
        self._draw_background(p, dims)
        p.end()

    def _dims(self):
        w = self.width(); h = self.height(); s = min(w, h)
        center = QPointF(w/2, h/2)
        radius = s/2 - 12
        return {"w": w, "h": h, "center": center, "r": radius}

    def paintEvent(self, event):
        self._rebuild_cache_if_needed()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Draw cached static background
        painter.drawPixmap(0, 0, self._bg_cache)
        # Draw dynamic layers
        dims = self._dims()
        self._draw_needle(painter, dims)
        self._draw_value(painter, dims)
        painter.end()

    def _draw_background(self, p: QPainter, d):
        # Determine sweep orientation
        start_angle = 45 if not _CW else -45
        span = 270 if not _CW else -270

        # Outer ring
        grad_pen = QPen(QColor(60, 60, 70), 10)
        p.setPen(grad_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        outer_span = 270*16
        if _CW:
            outer_span = -outer_span
        p.drawArc(int(d['center'].x()-d['r']), int(d['center'].y()-d['r']), int(d['r']*2), int(d['r']*2), -135*16, outer_span)

        # Colored zones (normal / warning / critical)
        def draw_zone(start_ratio, end_ratio, color: QColor):
            a1 = start_angle + start_ratio*span
            a2 = (end_ratio - start_ratio)*span
            pen = QPen(color, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(int(d['center'].x()-d['r']+6), int(d['center'].y()-d['r']+6), int((d['r']-6)*2), int((d['r']-6)*2), int(-a1*16), int(-a2*16))

        total = self.max_value - self.min_value
        warn_ratio = (self.warning_threshold - self.min_value)/total
        crit_ratio = (self.critical_threshold - self.min_value)/total
        draw_zone(0.0, warn_ratio, QColor(80, 180, 255))
        draw_zone(warn_ratio, crit_ratio, QColor(255, 200, 0))
        draw_zone(crit_ratio, 1.0, QColor(255, 60, 60))

        # Tick marks
        p.setPen(QPen(QColor(140, 140, 155), 2))
        for i in range(self.num_ticks):
            angle = math.radians(start_angle + (i * span / (self.num_ticks - 1)))
            inner = d['r'] - 18
            outer = d['r'] - 6
            p1 = QPointF(d['center'].x() + inner * math.cos(angle), d['center'].y() + inner * math.sin(angle))
            p2 = QPointF(d['center'].x() + outer * math.cos(angle), d['center'].y() + outer * math.sin(angle))
            p.drawLine(p1, p2)
        # Title (moved to bottom)
        p.setPen(QColor(210, 210, 220))
        f = QFont("Arial", 10, QFont.Weight.DemiBold)
        p.setFont(f)
        rect = p.fontMetrics().boundingRect(self.title)
        bottom_y = int(d['center'].y() + d['r'] - 10)
        p.drawText(int(d['center'].x() - rect.width()/2), bottom_y, self.title)

    def _draw_needle(self, p: QPainter, d):
        rng = self.max_value - self.min_value or 1
        ratio = (self.current_value - self.min_value)/rng
        ratio = max(0.0, min(1.0, ratio))
        if _CW:
            angle = math.radians(-45 - ratio * 270)
        else:
            angle = math.radians(45 + ratio * 270)
        needle_len = d['r'] - 28
        center = d['center']
        end = QPointF(center.x() + needle_len*math.cos(angle), center.y() + needle_len*math.sin(angle))
        p.setPen(QPen(QColor(255, 90, 40), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(center, end)
        # hub
        p.setBrush(QColor(40, 40, 50))
        p.setPen(QPen(QColor(120, 120, 130), 2))
        p.drawEllipse(center, 7, 7)

    def _draw_value(self, p: QPainter, d):
        rng = self.max_value - self.min_value
        if rng >= 100:
            text = f"{int(self.current_value)}"
        elif rng >= 10:
            text = f"{self.current_value:.1f}"
        else:
            text = f"{self.current_value:.2f}"
        p.setPen(QColor(240, 240, 245))
        p.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        rect = p.fontMetrics().boundingRect(text)
        p.drawText(int(d['center'].x() - rect.width()/2), int(d['center'].y() + d['r'] - 32), text)


class NeonGauge(QWidget):
    """More contemporary gauge: minimal ticks, progress arc, soft glow, center value.

    Design goals:
    - Flat dark background with subtle ring shadow.
    - Track ring + gradient progress arc (dynamic).
    - Optional warning / critical color transition along gradient.
    - Smooth value animation (interpolated toward target).
    - Large centered value & small unit; compact title.
    - Cached static background for performance.
    """

    def __init__(self, parent=None, min_value=0, max_value=8000, title="RPM", unit="", num_ticks=0,
                 warn_ratio=0.7, crit_ratio=0.9, smooth_factor=0.2):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.title = title
        self.unit = unit
        self.num_ticks = num_ticks  # 0 => none
        self.warn_ratio = warn_ratio
        self.crit_ratio = crit_ratio
        self.smooth_factor = smooth_factor
        self._target_value = min_value
        self._display_value = float(min_value)
        self._bg_cache = None
        self._bg_size = None
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_value(self, value):
        # Clamp & store target; animation handled in paint
        self._target_value = max(self.min_value, min(self.max_value, value))
        self.update()

    def _dimensions(self):
        w = self.width(); h = self.height(); s = min(w, h)
        c = QPointF(w/2, h/2)
        r = s/2 - 10
        return {"w": w, "h": h, "c": c, "r": r}

    def _rebuild_background(self):
        if self._bg_size == (self.width(), self.height()) and self._bg_cache is not None:
            return
        from PyQt6.QtGui import QPixmap
        self._bg_size = (self.width(), self.height())
        self._bg_cache = QPixmap(self.width(), self.height())
        self._bg_cache.fill(QColor(0, 0, 0, 0))
        p = QPainter(self._bg_cache)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = self._dimensions()
        # Background disc
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(25, 25, 30))
        p.drawEllipse(d['c'], d['r'], d['r'])
        # Track ring
        track_pen = QPen(QColor(55, 55, 65), 16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        p.setPen(track_pen)
        arc_rect = self._arc_rect(d)
        arc_span = 270*16
        if _CW:
            arc_span = -arc_span
        p.drawArc(*arc_rect, -135*16, arc_span)
        # Minimal ticks (optional)
        if self.num_ticks > 0:
            p.setPen(QPen(QColor(90, 90, 105), 2))
            for i in range(self.num_ticks):
                if _CW:
                    ang = math.radians(-45 - (i * 270 / (self.num_ticks - 1)))
                else:
                    ang = math.radians(45 + (i * 270 / (self.num_ticks - 1)))
                inner = d['r'] - 24
                outer = d['r'] - 10
                p1 = QPointF(d['c'].x() + inner*math.cos(ang), d['c'].y() + inner*math.sin(ang))
                p2 = QPointF(d['c'].x() + outer*math.cos(ang), d['c'].y() + outer*math.sin(ang))
                p.drawLine(p1, p2)
        # Title text (moved to bottom)
        p.setPen(QColor(180, 180, 190))
        p.setFont(QFont("Arial", 10, QFont.Weight.DemiBold))
        trect = p.fontMetrics().boundingRect(self.title)
        bottom_y = int(d['c'].y() + d['r'] - 12)
        p.drawText(int(d['c'].x() - trect.width()/2), bottom_y, self.title)
        p.end()

    def _arc_rect(self, d):
        r = d['r'] - 8
        return [int(d['c'].x() - r), int(d['c'].y() - r), int(r*2), int(r*2)]

    def _draw_progress_arc(self, p: QPainter, d):
        rng = (self.max_value - self.min_value) or 1
        ratio = (self._display_value - self.min_value)/rng
        ratio = max(0.0, min(1.0, ratio))
        span = int(270 * ratio * 16)
        if _CW:
            span = -span

        # Determine current arc color (no reliance on gradient .colorAt which isn't available)
        base_color = QColor(0, 180, 255)
        warn_color = QColor(255, 200, 0)
        crit_color = QColor(255, 70, 40)
        if ratio >= self.crit_ratio:
            end_color = crit_color
        elif ratio >= self.warn_ratio:
            end_color = warn_color
        else:
            end_color = base_color

        # Draw base arc for current progress
        pen = QPen(end_color, 16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawArc(*self._arc_rect(d), -135*16, span)

        # Subtle outer glow (separate lighter pen) – optional
        glow = QColor(end_color.red(), end_color.green(), end_color.blue(), 60)
        glow_pen = QPen(glow, 20, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        p.setPen(glow_pen)
        p.drawArc(*self._arc_rect(d), -135*16, span)

    def _animate(self):
        # Simple exponential smoothing toward target
        if self._display_value == self._target_value:
            return False
        self._display_value += (self._target_value - self._display_value) * self.smooth_factor
        # Snap if very close
        if abs(self._target_value - self._display_value) < (self.max_value - self.min_value) * 0.0005:
            self._display_value = self._target_value
        return True

    def paintEvent(self, event):
        self._rebuild_background()
        changed = self._animate()
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Static background
            p.drawPixmap(0, 0, self._bg_cache)
            d = self._dimensions()
            # Dynamic progress arc
            self._draw_progress_arc(p, d)
            # Center value
            rng = self.max_value - self.min_value
            if rng >= 100:
                txt = f"{int(self._display_value)}"
            elif rng >= 10:
                txt = f"{self._display_value:.1f}"
            else:
                txt = f"{self._display_value:.2f}"
            p.setFont(QFont("Arial", 20, QFont.Weight.Bold))
            p.setPen(QColor(235, 235, 240))
            val_rect = p.fontMetrics().boundingRect(txt)
            p.drawText(int(d['c'].x() - val_rect.width()/2), int(d['c'].y() + val_rect.height()/3), txt)
            if self.unit:
                p.setFont(QFont("Arial", 10))
                unit_rect = p.fontMetrics().boundingRect(self.unit)
                p.setPen(QColor(160, 160, 170))
                p.drawText(int(d['c'].x() - unit_rect.width()/2), int(d['c'].y() + val_rect.height()/3 + unit_rect.height() + 4), self.unit)
        finally:
            p.end()
        if changed:
            self.update()


class GaugeConfig:
    """Configuration class for gauge settings."""
    
    def __init__(self, title, min_value, max_value, signal_names, num_ticks=9, unit=""):
        self.title = title
        self.min_value = min_value
        self.max_value = max_value
        self.signal_names = signal_names if isinstance(signal_names, list) else [signal_names]
        self.num_ticks = num_ticks
        self.unit = unit

    @property
    def display_title(self):
        """Get the display title with units if specified."""
        if self.unit:
            return f"{self.title} ({self.unit})"
        return self.title