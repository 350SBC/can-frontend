# widgets/indicator_light.py
"""Indicator light widget for status displays."""

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QTimer


class IndicatorLight(QWidget):
    """A circular indicator light widget for showing status/warning lights."""
    
    def __init__(self, parent=None, title="Status", on_color=None, off_color=None, size=60):
        super().__init__(parent)
        self.title = title
        self.is_on = False
        self.size = size
        
        # Default colors
        self.on_color = on_color or QColor(0, 255, 0)  # Green
        self.off_color = off_color or QColor(50, 50, 50)  # Dark gray
        
        # Blinking support
        self.is_blinking = False
        self.blink_state = True
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._toggle_blink_state)
        
        self._setup_widget()

    def _setup_widget(self):
        """Set up widget properties."""
        self.setMinimumSize(self.size, self.size + 20)  # Extra space for text
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_state(self, state):
        """Set the indicator state (True = on, False = off)."""
        self.is_on = bool(state)
        self.stop_blinking()  # Stop blinking when state is set directly
        self.update()

    def set_blinking(self, enabled, interval=500):
        """Enable or disable blinking mode."""
        self.is_blinking = enabled
        if enabled:
            self.blink_timer.start(interval)
        else:
            self.blink_timer.stop()
            self.blink_state = True
        self.update()

    def stop_blinking(self):
        """Stop blinking mode."""
        self.set_blinking(False)

    def _toggle_blink_state(self):
        """Toggle the blink state for blinking effect."""
        self.blink_state = not self.blink_state
        self.update()

    def set_colors(self, on_color, off_color):
        """Set custom colors for on and off states."""
        self.on_color = QColor(on_color) if isinstance(on_color, str) else on_color
        self.off_color = QColor(off_color) if isinstance(off_color, str) else off_color
        self.update()

    def set_title(self, title):
        """Set the indicator title."""
        self.title = title
        self.update()

    def paintEvent(self, event):
        """Paint the indicator light."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate circle position and size
        circle_size = self.size - 10
        circle_x = (self.width() - circle_size) // 2
        circle_y = 5
        
        # Determine current color
        if self.is_blinking:
            current_color = self.on_color if (self.is_on and self.blink_state) else self.off_color
        else:
            current_color = self.on_color if self.is_on else self.off_color
        
        # Draw circle
        painter.setBrush(QBrush(current_color))
        painter.setPen(QPen(QColor(255, 255, 255), 2))  # White border
        painter.drawEllipse(circle_x, circle_y, circle_size, circle_size)
        
        # Draw title
        painter.setPen(QPen(QColor(255, 255, 255)))
        text_rect = painter.fontMetrics().boundingRect(self.title)
        text_x = (self.width() - text_rect.width()) // 2
        text_y = circle_y + circle_size + 15
        painter.drawText(text_x, text_y, self.title)


class IndicatorConfig:
    """Configuration class for indicator light settings."""
    
    def __init__(self, title, signal_names, on_color=None, off_color=None, size=60, threshold=0.5):
        self.title = title
        self.signal_names = signal_names if isinstance(signal_names, list) else [signal_names]
        self.on_color = on_color or QColor(0, 255, 0)  # Green
        self.off_color = off_color or QColor(50, 50, 50)  # Dark gray
        self.size = size
        self.threshold = threshold  # Value above which indicator turns on
        self.name = title  # For compatibility with layout manager


# Predefined indicator colors
class IndicatorColors:
    """Common indicator light colors."""
    GREEN = QColor(0, 255, 0)
    RED = QColor(255, 0, 0)
    YELLOW = QColor(255, 255, 0)
    BLUE = QColor(0, 0, 255)
    ORANGE = QColor(255, 165, 0)
    WHITE = QColor(255, 255, 255)
    DARK_GRAY = QColor(50, 50, 50)
    LIGHT_GRAY = QColor(150, 150, 150)
