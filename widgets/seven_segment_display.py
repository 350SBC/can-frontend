# widgets/seven_segment_display.py
"""Seven-segment display widget for displaying numbers and letters."""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QBrush, QFont, QFontMetrics
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SevenSegmentConfig:
    """Configuration for seven-segment display widget."""
    title: str
    signals: List[str]
    unit: str = ""
    digits: int = 4
    decimal_places: int = 0
    color_on: str = "#00FF00"  # Green when segments are on
    color_off: str = "#003300"  # Dark green when segments are off
    background_color: str = "#000000"  # Black background
    show_title: bool = True
    show_unit: bool = True
    blink_on_update: bool = False


class SevenSegmentColors:
    """Predefined colors for seven-segment displays."""
    GREEN = "#00FF00"
    RED = "#FF0000"
    YELLOW = "#FFFF00"
    BLUE = "#0080FF"
    ORANGE = "#FF8000"
    WHITE = "#FFFFFF"
    
    # Background variants
    DARK_GREEN = "#003300"
    DARK_RED = "#330000"
    DARK_YELLOW = "#333300"
    DARK_BLUE = "#001133"
    DARK_ORANGE = "#331100"
    DARK_GRAY = "#333333"


class SevenSegmentDisplay(QWidget):
    """A seven-segment display widget that can show numbers and some letters."""
    
    # Segment patterns for digits 0-9 and letters A-F
    DIGIT_PATTERNS = {
        '0': [True, True, True, True, True, True, False],    # 0
        '1': [False, True, True, False, False, False, False], # 1
        '2': [True, True, False, True, True, False, True],   # 2
        '3': [True, True, True, True, False, False, True],   # 3
        '4': [False, True, True, False, False, True, True],  # 4
        '5': [True, False, True, True, False, True, True],   # 5
        '6': [True, False, True, True, True, True, True],    # 6
        '7': [True, True, True, False, False, False, False], # 7
        '8': [True, True, True, True, True, True, True],     # 8
        '9': [True, True, True, True, False, True, True],    # 9
        'A': [True, True, True, False, True, True, True],    # A
        'B': [False, False, True, True, True, True, True],   # b
        'C': [True, False, False, True, True, True, False],  # C
        'D': [False, True, True, True, True, False, True],   # d
        'E': [True, False, False, True, True, True, True],   # E
        'F': [True, False, False, False, True, True, True],  # F
        'H': [False, True, True, False, True, True, True],   # H
        'L': [False, False, False, True, True, True, False], # L
        'O': [True, True, True, True, True, True, False],    # O (same as 0)
        'P': [True, True, False, False, True, True, True],   # P
        'U': [False, True, True, True, True, True, False],   # U
        '-': [False, False, False, False, False, False, True], # dash
        ' ': [False, False, False, False, False, False, False], # space
        '.': [False, False, False, False, False, False, False], # decimal point handled separately
    }
    
    def __init__(self, config: SevenSegmentConfig):
        super().__init__()
        self.config = config
        self.current_value = 0.0
        self.display_text = "0"
        self.blink_state = True
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._toggle_blink)
        
        self.setMinimumSize(200, 100)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Seven-segment display area (will be custom painted)
        self.display_widget = QWidget()
        self.display_widget.setMinimumHeight(60)
        layout.addWidget(self.display_widget, 1)
        
        # Title label at bottom
        if self.config.show_title:
            self.title_label = QLabel(self.config.title)
            self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.title_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                    margin: 2px;
                }
            """)
            layout.addWidget(self.title_label)
        
        # Unit label at bottom (below title)
        if self.config.show_unit and self.config.unit:
            self.unit_label = QLabel(self.config.unit)
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.unit_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 10px;
                    margin: 2px;
                }
            """)
            layout.addWidget(self.unit_label)
        
        self.setLayout(layout)
        
        # Set background color
        self.setStyleSheet(f"background-color: {self.config.background_color};")
        
    def set_value(self, value):
        """Update the display value."""
        self.current_value = float(value)
        
        # Format the value based on decimal places
        if self.config.decimal_places > 0:
            format_str = f"{{:.{self.config.decimal_places}f}}"
            formatted_value = format_str.format(self.current_value)
        else:
            formatted_value = str(int(self.current_value))
        
        # Limit to available digits
        if len(formatted_value) > self.config.digits:
            # If number is too large, show dashes
            self.display_text = "-" * self.config.digits
        else:
            # Pad with spaces if needed
            self.display_text = formatted_value.rjust(self.config.digits)
        
        # Handle blinking
        if self.config.blink_on_update:
            self.blink_state = True
            self.blink_timer.start(500)  # Blink every 500ms
        
        self.update()  # Trigger repaint
        
    def set_text(self, text):
        """Set custom text to display."""
        text = str(text).upper()
        if len(text) > self.config.digits:
            text = text[:self.config.digits]
        else:
            text = text.rjust(self.config.digits)
        
        self.display_text = text
        self.update()
        
    def _toggle_blink(self):
        """Toggle blink state."""
        self.blink_state = not self.blink_state
        self.update()
        
        # Stop blinking after 3 seconds
        if not hasattr(self, '_blink_start_time'):
            import time
            self._blink_start_time = time.time()
        elif time.time() - self._blink_start_time > 3.0:
            self.blink_timer.stop()
            self.blink_state = True
            self.update()
            delattr(self, '_blink_start_time')
    
    def paintEvent(self, event):
        """Custom paint event to draw seven-segment display."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate display area
        widget_rect = self.display_widget.geometry()
        if widget_rect.isEmpty():
            return
            
        # Calculate character dimensions
        char_width = widget_rect.width() // self.config.digits
        char_height = widget_rect.height()
        segment_thickness = max(2, min(char_width // 15, char_height // 15))
        
        # Draw each character
        for i, char in enumerate(self.display_text):
            x_offset = widget_rect.x() + i * char_width + char_width // 8
            y_offset = widget_rect.y() + char_height // 8
            
            char_display_width = char_width - char_width // 4
            char_display_height = char_height - char_height // 4
            
            # Handle decimal point
            show_decimal = (self.config.decimal_places > 0 and 
                          i == len(self.display_text) - self.config.decimal_places - 1 and
                          '.' in str(self.current_value))
            
            self._draw_character(painter, char, x_offset, y_offset, 
                               char_display_width, char_display_height, 
                               segment_thickness, show_decimal)
    
    def _draw_character(self, painter, char, x, y, width, height, thickness, show_decimal=False):
        """Draw a single seven-segment character."""
        if char not in self.DIGIT_PATTERNS:
            char = ' '  # Default to blank for unknown characters
            
        pattern = self.DIGIT_PATTERNS[char]
        
        # Determine colors based on blink state
        if self.config.blink_on_update and not self.blink_state:
            on_color = self.config.color_off
        else:
            on_color = self.config.color_on
            
        off_color = self.config.color_off
        
        # Segment positions (as ratios of character dimensions)
        # Segments: a, b, c, d, e, f, g
        segments = [
            # a - top horizontal
            [(0.1, 0.0), (0.9, 0.0), (0.8, 0.1), (0.2, 0.1)],
            # b - top right vertical  
            [(0.9, 0.0), (1.0, 0.1), (1.0, 0.4), (0.9, 0.5), (0.8, 0.4), (0.8, 0.1)],
            # c - bottom right vertical
            [(0.9, 0.5), (1.0, 0.6), (1.0, 0.9), (0.9, 1.0), (0.8, 0.9), (0.8, 0.6)],
            # d - bottom horizontal
            [(0.1, 1.0), (0.9, 1.0), (0.8, 0.9), (0.2, 0.9)],
            # e - bottom left vertical
            [(0.0, 0.6), (0.1, 0.5), (0.2, 0.6), (0.2, 0.9), (0.1, 1.0), (0.0, 0.9)],
            # f - top left vertical
            [(0.0, 0.1), (0.1, 0.0), (0.2, 0.1), (0.2, 0.4), (0.1, 0.5), (0.0, 0.4)],
            # g - middle horizontal
            [(0.1, 0.5), (0.9, 0.5), (0.8, 0.4), (0.8, 0.6), (0.2, 0.6), (0.2, 0.4)]
        ]
        
        # Draw each segment
        for i, segment_coords in enumerate(segments):
            if pattern[i]:  # Segment should be on
                painter.setBrush(QBrush(Qt.GlobalColor.transparent))
                painter.setPen(QPen(Qt.GlobalColor.transparent))
                
                # Convert relative coordinates to absolute
                points = []
                for rel_x, rel_y in segment_coords:
                    abs_x = x + rel_x * width
                    abs_y = y + rel_y * height
                    points.append((int(abs_x), int(abs_y)))
                
                # Draw filled polygon for segment
                from PyQt6.QtGui import QPolygon, QColor
                from PyQt6.QtCore import QPoint
                color = QColor(on_color)
                painter.setBrush(QBrush(color))
                polygon = QPolygon([QPoint(x, y) for x, y in points])
                painter.drawPolygon(polygon)
            else:  # Segment should be off (draw faintly)
                painter.setBrush(QBrush(Qt.GlobalColor.transparent))
                painter.setPen(QPen(Qt.GlobalColor.transparent))
                
                # Convert relative coordinates to absolute
                points = []
                for rel_x, rel_y in segment_coords:
                    abs_x = x + rel_x * width
                    abs_y = y + rel_y * height
                    points.append((int(abs_x), int(abs_y)))
                
                # Draw faint polygon for off segment
                from PyQt6.QtGui import QPolygon, QColor
                from PyQt6.QtCore import QPoint
                color = QColor(off_color)
                painter.setBrush(QBrush(color))
                polygon = QPolygon([QPoint(x, y) for x, y in points])
                painter.drawPolygon(polygon)
        
        # Draw decimal point if needed
        if show_decimal:
            from PyQt6.QtGui import QColor
            color = QColor(on_color)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.GlobalColor.transparent))
            dot_size = max(3, thickness)
            dot_x = x + width - dot_size
            dot_y = y + height - dot_size
            painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)
