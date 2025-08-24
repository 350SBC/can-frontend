    # ...existing imports and class definition...

class LayoutManager:
    """Manages different layout configurations for gauges."""
    # ...existing methods...

# gui/layout_manager.py
"""Layout manager for handling different gauge arrangements."""

from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt
from config.settings import LAYOUT_CONFIGS


class LayoutManager:
    """Manages different layout configurations for gauges."""
    
    def __init__(self):
        self.current_layout = None
        self.current_layout_name = None
        self.window_size = None
        
    def set_window_size(self, width, height):
        """Set the current window size for relative calculations."""
        self.window_size = (width, height)
        
    def create_layout(self, layout_name, gauges, window_size=None):
        """
        Create a layout based on the configuration.
        
        Args:
            layout_name (str): Name of the layout configuration
            gauges (list): List of gauge widgets
            window_size (tuple): Optional (width, height) of the window
            
        Returns:
            QLayout: The configured layout
        """
        if window_size:
            self.set_window_size(window_size[0], window_size[1])
            
        if layout_name not in LAYOUT_CONFIGS:
            raise ValueError(f"Unknown layout: {layout_name}")
            
        config = LAYOUT_CONFIGS[layout_name]
        
        if config["type"] == "grid":
            return self._create_grid_layout(config, gauges)
        elif config["type"] == "custom":
            return self._create_custom_layout(config, gauges)
        elif config["type"] == "custom_grid":
            return self._create_custom_grid_layout(config, gauges)
        elif config["type"] == "video_grid":
            return self._create_video_grid_layout(config)
        elif config["type"] == "gauges_video_center":
            return self._create_gauges_video_center_layout(config, gauges)
        else:
            raise ValueError(f"Unknown layout type: {config['type']}")
    def _create_gauges_video_center_layout(self, config, gauges):
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QSizePolicy
        from widgets.video_grid_widget import VideoGridWidget
        layout = QHBoxLayout()
        layout.setSpacing(config.get("spacing", 0))

        # Split gauges by name
        left_names = set(config.get("gauge_left", []))
        right_names = set(config.get("gauge_right", []))
        left_gauges = [g for g in gauges if getattr(g.config, "title", getattr(g.config, "name", "")) in left_names]
        right_gauges = [g for g in gauges if getattr(g.config, "title", getattr(g.config, "name", "")) in right_names]

        # Left gauges (vertical)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(0)
        base_size = 180  # or calculate from window size if needed
        for g in left_gauges:
            self._apply_gauge_sizing(g, config, base_size)
            left_layout.addWidget(g)
        layout.addLayout(left_layout)

        # Video grid center
        num_cameras = config.get("num_cameras", 2)
        camera_indices = config.get("camera_indices", list(range(num_cameras)))
        video_widget = VideoGridWidget(camera_indices=camera_indices)
        video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(video_widget)

        # Right gauges (vertical)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(0)
        for g in right_gauges:
            self._apply_gauge_sizing(g, config, base_size)
            right_layout.addWidget(g)
        layout.addLayout(right_layout)

        return layout
    def _create_video_grid_layout(self, config):
        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout()
        num_cameras = config.get("num_cameras", 4)
        camera_indices = config.get("camera_indices", list(range(num_cameras)))
        from widgets.video_grid_widget import VideoGridWidget
        video_widget = VideoGridWidget(camera_indices=camera_indices)
        scale_factor = config.get("scale_factor", 1.0)
        video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if scale_factor < 1.0:
            # Shrink widget by scale_factor relative to parent size
            def resize_event(event):
                parent = video_widget.parentWidget()
                if parent:
                    w = int(parent.width() * scale_factor)
                    h = int(parent.height() * scale_factor)
                    video_widget.resize(w, h)
            video_widget.resizeEvent = resize_event
        layout.addWidget(video_widget)
        return layout
    
    def _create_custom_grid_layout(self, config, widgets):
        """Create a custom grid layout with top large gauges, side small gauges, and bottom row."""
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(config.get("spacing", 15))
        
        # Get widget lists from config
        top_large_names = set(config.get("top_large", []))
        side_small_names = set(config.get("side_small", []))
        bottom_row_names = set(config.get("bottom_row", []))
        
        # Split widgets by name (match against config.title)
        top_large_widgets = [w for w in widgets if getattr(w.config, "title", "") in top_large_names]
        side_small_widgets = [w for w in widgets if getattr(w.config, "title", "") in side_small_names]
        bottom_row_widgets = [w for w in widgets if getattr(w.config, "title", "") in bottom_row_names]
        
        # Top section: side small | large widgets | side small
        top_layout = QHBoxLayout()
        top_layout.setSpacing(config.get("spacing", 15))
        
        # Left side small widget
        if len(side_small_widgets) > 0:
            left_small = side_small_widgets[0]
            self._apply_widget_sizing(left_small, config, 180)
            top_layout.addWidget(left_small)
        
        # Large widgets in center
        large_layout = QHBoxLayout()
        large_layout.setSpacing(config.get("spacing", 15))
        for widget in top_large_widgets:
            self._apply_widget_sizing(widget, config, 180)
            large_layout.addWidget(widget)
        top_layout.addLayout(large_layout)
        
        # Right side small widget
        if len(side_small_widgets) > 1:
            right_small = side_small_widgets[1]
            self._apply_widget_sizing(right_small, config, 180)
            top_layout.addWidget(right_small)
        
        main_layout.addLayout(top_layout)
        
        # Bottom row: grid of remaining widgets
        if bottom_row_widgets:
            bottom_layout = QHBoxLayout()
            bottom_layout.setSpacing(config.get("spacing", 15))
            for widget in bottom_row_widgets:
                self._apply_widget_sizing(widget, config, 180)
                bottom_layout.addWidget(widget)
            main_layout.addLayout(bottom_layout)
        
        return main_layout
    
    def _create_grid_layout(self, config, gauges):
        """Create a grid layout based on configuration."""
        layout = QGridLayout()
        layout.setSpacing(config["spacing"])
        
        rows = config["rows"]
        cols = config["cols"]
        
        # Calculate base gauge size for scaling
        if self.window_size:
            window_width, window_height = self.window_size
            # Reserve space for other UI elements (roughly 300px)
            available_width = window_width - 100
            available_height = window_height - 400
            
            base_width = available_width // cols
            base_height = available_height // rows
            base_size = min(base_width, base_height)
        else:
            base_size = 180  # Default fallback size
        
        # Add gauges to grid
        for i, gauge in enumerate(gauges):
            if i >= rows * cols:
                break  # Don't exceed grid capacity
                
            row = i // cols
            col = i % cols
            
            # Apply gauge-specific sizing if configured
            self._apply_gauge_sizing(gauge, config, base_size)
            
            layout.addWidget(gauge, row, col)
            
        return layout
    
    def _apply_gauge_sizing(self, gauge, config, base_size):
        """Apply gauge-specific sizing based on configuration."""
        self._apply_widget_sizing(gauge, config, base_size)
    
    def _apply_widget_sizing(self, widget, config, base_size):
        """Apply widget-specific sizing based on configuration (works for both gauges and indicators)."""
        # Reset any previous size constraints and set size policy
        widget.setMinimumSize(0, 0)
        widget.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        if not hasattr(widget, 'config'):
            return
            
        widget_name = widget.config.name if hasattr(widget.config, 'name') else widget.config.title
        
        # Apply proportional sizing if configured
        if config.get("use_proportional_sizing") and "gauge_proportions" in config:
            if widget_name in config["gauge_proportions"]:
                self._apply_proportional_sizing(widget, config["gauge_proportions"][widget_name])
                return
        
        # Apply scale factor sizing if configured
        if "gauge_sizes" in config and widget_name in config["gauge_sizes"]:
            size_config = config["gauge_sizes"][widget_name]
            
            if "scale_factor" in size_config:
                scale = size_config["scale_factor"]
                scaled_size = int(base_size * scale)
                
                # Set minimum size to maintain proportions, but allow expansion
                widget.setMinimumSize(scaled_size, scaled_size)
                
                # Adjust size policy based on scale factor
                if scale > 1.0:
                    # Larger widgets get more space preference
                    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                else:
                    # Smaller widgets are more constrained
                    widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
                    widget.setMaximumSize(int(scaled_size * 1.5), int(scaled_size * 1.5))
            
            # Legacy support for fixed min/max sizes
            elif "min_size" in size_config:
                min_width, min_height = size_config["min_size"]
                widget.setMinimumSize(min_width, min_height)
                
                if "max_size" in size_config:
                    max_width, max_height = size_config["max_size"]
                    widget.setMaximumSize(max_width, max_height)

    def _apply_proportional_sizing(self, widget, proportion_config):
        """Apply proportional sizing based on window size (works for both gauges and indicators)."""
        if not self.window_size:
            return
            
        window_width, window_height = self.window_size
        
        # Calculate available space (minus UI overhead)
        available_width = window_width - 100
        available_height = window_height - 400
        
        width_percent = proportion_config.get("width_percent", 20)
        height_percent = proportion_config.get("height_percent", 20)
        
        target_width = int(available_width * width_percent / 100)
        target_height = int(available_height * height_percent / 100)
        
        widget.setMinimumSize(target_width, target_height)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def _create_custom_layout(self, config, gauges):
        """Create a custom layout (e.g., focus on primary gauges)."""
        if config.get("primary_gauges") and config.get("secondary_gauges"):
            return self._create_focus_layout(config, gauges)
        else:
            # Fallback to 2x3 grid
            fallback_config = {
                "type": "grid",
                "rows": 2,
                "cols": 3,
                "spacing": 10
            }
            return self._create_grid_layout(fallback_config, gauges)
    
    def _create_focus_layout(self, config, gauges):
        """Create a layout that focuses on primary gauges."""
        main_layout = QVBoxLayout()
        
        # Create gauge mapping by name
        gauge_map = {}
        for gauge in gauges:
            if hasattr(gauge, 'config') and hasattr(gauge.config, 'name'):
                gauge_map[gauge.config.name] = gauge
            elif hasattr(gauge, 'config') and hasattr(gauge.config, 'title'):
                gauge_map[gauge.config.title] = gauge
        
        # Primary gauges (larger, top row)
        primary_layout = QHBoxLayout()
        primary_layout.setSpacing(15)
        
        for gauge_name in config["primary_gauges"]:
            if gauge_name in gauge_map:
                gauge = gauge_map[gauge_name]
                # Reset size constraints first
                gauge.setMinimumSize(0, 0)
                gauge.setMaximumSize(16777215, 16777215)
                # Set larger primary gauge size
                gauge.setMinimumSize(200, 200)
                primary_layout.addWidget(gauge)
        
        # Secondary gauges (smaller, bottom rows)
        secondary_layout = QGridLayout()
        secondary_layout.setSpacing(8)
        
        secondary_gauges = [gauge_map[name] for name in config["secondary_gauges"] 
                          if name in gauge_map]
        
        # Arrange secondary gauges in 2x2 grid
        for i, gauge in enumerate(secondary_gauges):
            # Reset size constraints first
            gauge.setMinimumSize(0, 0)
            gauge.setMaximumSize(16777215, 16777215)
            # Set smaller secondary gauge size
            gauge.setMaximumSize(150, 150)
            row = i // 2
            col = i % 2
            secondary_layout.addWidget(gauge, row, col)
        
        main_layout.addLayout(primary_layout)
        main_layout.addLayout(secondary_layout)
        
        return main_layout
    
    def reset_gauge_sizes(self, gauges):
        """Reset all gauge sizes to default."""
        for gauge in gauges:
            gauge.setMinimumSize(0, 0)
            gauge.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX
            gauge.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def get_available_layouts(self):
        """Get list of available layout names and their display names."""
        return [(name, config["name"]) for name, config in LAYOUT_CONFIGS.items()]
