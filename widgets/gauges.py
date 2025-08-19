# widgets/gauges.py
"""Custom gauge widgets for the CAN dashboard."""

import math
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import QPointF

# Import performance settings
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import GAUGE_IMMEDIATE_THRESHOLD, GAUGE_SKIP_THRESHOLD


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
        """Update gauge value with Pi4-optimized rendering."""
        new_value = max(self.min_value, min(self.max_value, value))
        
        # Calculate change percentage
        value_range = self.max_value - self.min_value
        if value_range > 0:
            change_percentage = abs(new_value - self.current_value) / value_range
            
            # Pi4-optimized thresholds: Less sensitive to reduce GPU load
            if change_percentage > GAUGE_IMMEDIATE_THRESHOLD:
                self.current_value = new_value
                # Use update() instead of repaint() on Pi4 for better performance
                self.update()  # Let Qt optimize the repaint timing
                return
            
            # More aggressive skipping on Pi4 to reduce GPU load
            if change_percentage < GAUGE_SKIP_THRESHOLD:
                return
        
        # Normal update for Pi4
        self.current_value = new_value
        self.update()

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
        """Draw the gauge title."""
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_rect = painter.fontMetrics().boundingRect(self.title)
        painter.drawText(
            int(dimensions['center'].x() - title_rect.width() / 2),
            int(dimensions['center'].y() - dimensions['radius'] + 30),
            self.title
        )

    def _draw_scale(self, painter, dimensions):
        """Draw the scale marks and numbers."""
        painter.setFont(QFont("Arial", 8))
        for i in range(self.num_ticks):
            angle = -135 + (i * 270 / (self.num_ticks - 1))
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
        
        needle_angle = -135 + (value_ratio * 270)
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