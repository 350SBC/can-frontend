# gui/main_window.py
"""Main window for the CAN dashboard application."""

import json
import time
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QLineEdit, QMessageBox, QFormLayout,
                            QFrame, QGridLayout, QComboBox)
from PyQt6.QtCore import QThread, QTimer, QPropertyAnimation, QRect, pyqtSignal, Qt

from communication.zmq_worker import ZMQWorker
from widgets.gauges import RoundGauge, GaugeConfig, ModernGauge, NeonGauge
from widgets.indicator_light import IndicatorLight, IndicatorConfig, IndicatorColors
from widgets.seven_segment_display import SevenSegmentDisplay, SevenSegmentConfig, SevenSegmentColors
from widgets.send_message_widget import CollapsibleSendMessageWidget  # Import the new widget
from gui.layout_manager import LayoutManager
# from widgets.message_table import MessageTableWidget  # Uncomment when ready
from config.settings import *


class CollapsibleWidget(QWidget):
    """A widget that can be collapsed and expanded."""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.toggle)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)
        
        self.toggle()  # Start collapsed

    def toggle(self):
        """Toggle the visibility of the content area."""
        checked = self.toggle_button.isChecked()
        self.toggle_button.setText("▼ Live Signal Plots" if checked else "▶ Live Signal Plots")
        self.content_area.setVisible(checked)

    def add_content_widget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)


class CANDashboardMainWindow(QMainWindow):
    """Main window for the CAN dashboard application."""
    
    def __init__(self):
        super().__init__()
        self.gauges = {}  # Store gauge references
        self.indicators = {}  # Store indicator light references
        self.displays = {}  # Store seven-segment display references
        # Performance optimization: gauge-only (plots removed)
        self.pending_gauge_updates = {}
        self.last_gauge_update_time = {}
        self.gauge_update_interval = GAUGE_UPDATE_INTERVAL
        # Critical signals that get immediate updates (bypass buffering)
        self.critical_signals = {"rpm", "engine_rpm", "engine_speed", "speed", "vehicle_speed"}
        # Define gauge configurations
        self.gauge_configs = [
            GaugeConfig("Engine RPM", 0, 6500, ["rpm", "engine_rpm", "engine_speed"], 14, "RPM"),
            GaugeConfig("Speed", 0, 100, ["speed", "vehicle_speed", "mph"], 21, "MPH"),
            GaugeConfig("Temperature", 60, 220, ["cts", "engine_temp", "temperature"], 7, "°f"),
            GaugeConfig("AFR", 0, 20, ["average_afr", "air_fuel_ratio"], 6, ":1"),
            GaugeConfig("Battery Voltage", 10, 16, ["battery_voltage", "voltage"], 7, "V"),
            GaugeConfig("Oil Pressure", 0, 100, ["oil", "oil_psi"], 6, "PSI"),
            GaugeConfig("Timing", -10, 50, ["timing", "ignition_timing", "advance"], 8, "°"),
            GaugeConfig("Pedal Position", 0, 100, ["pedal", "throttle", "tps", "pedal_position"], 6, "%"),
            GaugeConfig("MAP", 0, 30, ["map", "manifold_pressure", "boost"], 7, "PSI"),
        ]
        
        # Define indicator configurations
        self.indicator_configs = [
            IndicatorConfig("Closed Loop", ["closed_loop_status"], 
                          on_color=IndicatorColors.GREEN, 
                          off_color=IndicatorColors.RED, 
                          size=50, 
                          threshold=0.5),
        ]
        
        # Define seven-segment display configurations
        self.display_configs = [
            SevenSegmentConfig("Gear", ["gear", "current_gear"], digits=1, 
                             color_on=SevenSegmentColors.GREEN, show_unit=False),
            SevenSegmentConfig("Lambda", ["lambda", "lambda_value"], digits=4, decimal_places=2,
                             color_on=SevenSegmentColors.BLUE, unit="λ"),
            SevenSegmentConfig("Boost", ["boost_psi", "turbo_pressure"], digits=3, decimal_places=1,
                             color_on=SevenSegmentColors.YELLOW, unit="PSI"),
        ]
        # Enable multitouch events
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)

        # Initialize layout manager
        self.layout_manager = LayoutManager()
        self.current_layout_name = DEFAULT_LAYOUT
        self.gauge_widgets = []  # Store gauge widgets for layout switching
        self.indicator_widgets = []  # Store indicator widgets for layout switching
        self.display_widgets = []  # Store seven-segment display widgets for layout switching

        self._setup_window()
        self._setup_zmq_worker()
        self._init_ui()
        self._connect_signals()
        self._setup_update_timer()
        self._auto_connect_and_configure()

    def _setup_update_timer(self):
        """Setup ultra-fast timer for maximum gauge responsiveness."""
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self._process_pending_updates)
        self.ui_update_timer.start(UI_UPDATE_RATE)  # Ultra-fast 120 FPS updates

    def _setup_window(self):
        """Set up the main window properties."""
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(*WINDOW_GEOMETRY)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

    def _setup_zmq_worker(self):
        """Set up the ZMQ worker and thread."""
        self.zmq_worker = ZMQWorker(BACKEND_IP, PUB_PORT, REQ_REP_PORT)
        self.zmq_thread = QThread()
        self.zmq_worker.moveToThread(self.zmq_thread)
        self.zmq_thread.start()

    def _connect_signals(self):
        """Connect ZMQ worker signals after UI is initialized."""
        # Uncomment when message table is implemented
        # self.zmq_worker.decoded_message_received.connect(self.message_table.add_message)
        # self.zmq_worker.raw_message_received.connect(self.message_table.add_message)
        
        self.zmq_worker.backend_status_message.connect(self.update_status_bar)
        self.zmq_worker.backend_error_message.connect(self.display_error)
        self.zmq_worker.new_signal_value.connect(self.update_display_data)
        
        # Connect the send message widget signal
        self.send_message_widget.send_message_requested.connect(self.send_can_message_command)

    def _init_ui(self):
        """Initialize the user interface."""
        self._setup_layout_controls()
        self._setup_gauges()
        # self._setup_message_table()  # Uncomment when ready
        self._setup_send_message_section()
        self._setup_status_bar()

    def _setup_layout_controls(self):
        """Set up layout switching controls."""
        # Hide the layout dropdown but keep it functional for safety
        layout_control_widget = QWidget()
        layout_control_layout = QHBoxLayout(layout_control_widget)
        
        # Layout selector
        layout_label = QLabel("Layout:")
        self.layout_combo = QComboBox()
        
        # Populate combo box with available layouts
        for layout_key, layout_config in LAYOUT_CONFIGS.items():
            self.layout_combo.addItem(layout_config["name"], layout_key)
        
        # Set current layout
        index = self.layout_combo.findData(self.current_layout_name)
        if index >= 0:
            self.layout_combo.setCurrentIndex(index)
        
        # Connect signal
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        
        layout_control_layout.addWidget(layout_label)
        layout_control_layout.addWidget(self.layout_combo)
        layout_control_layout.addStretch()  # Push everything to the left
        
        # Hide the layout control widget but keep it in the layout
        layout_control_widget.setVisible(False)
        
        # Add to main layout
        self.main_layout.addWidget(layout_control_widget)

    def _setup_gauges(self):
        """Set up gauge widgets based on configurations."""
        # Create gauge widgets (only once)
        if not self.gauge_widgets:  # Only create if not already created
            gauge_style = globals().get('GAUGE_STYLE', 'classic')
            for config in self.gauge_configs:
                if gauge_style == 'modern':
                    # Use NeonGauge as primary modern style
                    gauge = NeonGauge(
                        min_value=config.min_value,
                        max_value=config.max_value,
                        title=config.title,
                        unit=config.unit,
                        num_ticks=5 if config.title.lower() != 'afr' else 0
                    )
                elif gauge_style == 'modern_arc':
                    gauge = ModernGauge(
                        min_value=config.min_value,
                        max_value=config.max_value,
                        title=config.display_title,
                        num_ticks=config.num_ticks
                    )
                else:
                    gauge = RoundGauge(
                        min_value=config.min_value,
                        max_value=config.max_value,
                        title=config.display_title,
                        num_ticks=config.num_ticks
                    )
                
                # Store config reference for layout manager
                gauge.config = config
                self.gauge_widgets.append(gauge)
                
                # Store gauge with signal name mapping
                for signal_name in config.signal_names:
                    self.gauges[signal_name.lower()] = gauge
        
        # Create indicator widgets (only once)
        if not self.indicator_widgets:  # Only create if not already created
            for config in self.indicator_configs:
                indicator = IndicatorLight(
                    title=config.title,
                    on_color=config.on_color,
                    off_color=config.off_color,
                    size=config.size
                )
                
                # Store config reference for layout manager
                indicator.config = config
                self.indicator_widgets.append(indicator)
                
                # Store indicator with signal name mapping
                for signal_name in config.signal_names:
                    self.indicators[signal_name.lower()] = indicator
        
        # Create seven-segment display widgets (only once)
        if not self.display_widgets:  # Only create if not already created
            for config in self.display_configs:
                display = SevenSegmentDisplay(config)
                
                # Store config reference for layout manager
                display.config = config
                self.display_widgets.append(display)
                
                # Store display with signal name mapping
                for signal_name in config.signals:
                    self.displays[signal_name.lower()] = display
        
        # Apply current layout
        self._apply_layout(self.current_layout_name)

    def _apply_layout(self, layout_name):
        """Apply a specific layout to the gauges."""
        # Remove existing gauge layout if it exists
        if hasattr(self, 'gauge_layout') and self.gauge_layout:
            self._clear_layout(self.gauge_layout)
            self.main_layout.removeItem(self.gauge_layout)
        
                # Reset sizes for all widgets to ensure clean layout application
        self.layout_manager.reset_gauge_sizes(self.gauge_widgets + self.indicator_widgets + self.display_widgets)
        
        # Get current window size for relative calculations
        window_size = (self.width(), self.height())
        
        # Create new layout using layout manager
        try:
            all_widgets = self.gauge_widgets + self.indicator_widgets + self.display_widgets
            self.gauge_layout = self.layout_manager.create_layout(layout_name, all_widgets, window_size)
            self.current_layout_name = layout_name
            
            # Insert gauge layout after layout controls but before plots
            self.main_layout.insertLayout(1, self.gauge_layout)
            
        except Exception as e:
            print(f"Error applying layout {layout_name}: {e}")
            # Fallback to default grid layout
            self._apply_fallback_layout()

    def resizeEvent(self, event):
        """Handle window resize events to update gauge sizes."""
        super().resizeEvent(event)
        
        # Update layout manager with new window size
        if hasattr(self, 'layout_manager') and hasattr(self, 'current_layout_name'):
            self.layout_manager.set_window_size(self.width(), self.height())
            
            # Re-apply current layout with new window size if using relative sizing
            if (hasattr(self, 'current_layout_name') and 
                self.current_layout_name in LAYOUT_CONFIGS):
                config = LAYOUT_CONFIGS[self.current_layout_name]
                if (config.get("use_proportional_sizing") or 
                    any("scale_factor" in gauge_config for gauge_config in 
                        config.get("gauge_sizes", {}).values())):
                    # Only re-apply if layout uses relative sizing
                    self._apply_layout(self.current_layout_name)

    def _apply_fallback_layout(self):
        """Apply a fallback grid layout if the selected layout fails."""
        self.gauge_layout = QGridLayout()
        self.gauge_layout.setSpacing(20)
        
        # Simple 2x3 grid
        all_widgets = self.gauge_widgets + self.indicator_widgets + self.display_widgets
        for i, widget in enumerate(all_widgets):
            row = i // 3
            col = i % 3
            self.gauge_layout.addWidget(widget, row, col)
        
        self.main_layout.insertLayout(1, self.gauge_layout)

    def _clear_layout(self, layout):
        """Clear all widgets from a layout without deleting them."""
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
                elif child.layout():
                    self._clear_layout(child.layout())

    def _on_layout_changed(self):
        """Handle layout selection change."""
        layout_key = self.layout_combo.currentData()
        if layout_key and layout_key != self.current_layout_name:
            self._apply_layout(layout_key)
            self.update_status_bar(f"Layout changed to: {LAYOUT_CONFIGS[layout_key]['name']}")

    def _setup_send_message_section(self):
        """Set up the send message section using the new widget."""
        # Create the collapsible send message widget
        self.send_message_widget = CollapsibleSendMessageWidget("Send CAN Messages")
        
        # Add to main layout
        self.main_layout.addWidget(self.send_message_widget)

    def _setup_status_bar(self):
        """Set up the status bar."""
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("Ready")

    # Plot initialization removed

    def _auto_connect_and_configure(self):
        """Automatically connect and configure the backend."""
        self.update_status_bar("Auto-connecting to backend...")
        QTimer.singleShot(500, self._auto_setup_sequence)

    def _auto_setup_sequence(self):
        """Perform automatic setup sequence."""
        self.zmq_worker.backend_ip = BACKEND_IP
        QTimer.singleShot(0, self.zmq_worker.connect_sockets)
        self.update_status_bar("Connected to backend. Loading DBC...")
        QTimer.singleShot(1000, self._auto_load_dbc)

    def _auto_load_dbc(self):
        """Automatically load the DBC file."""
        response = self.zmq_worker.send_command("load_dbc", {"file_path": AUTO_DBC_PATH})
        if response.get("status") == "success":
            self.update_status_bar("DBC loaded. Connecting to CAN...")
            QTimer.singleShot(1000, self._auto_connect_can)
        else:
            self.update_status_bar(f"Failed to load DBC: {response.get('message', 'Unknown error')}")

    def _auto_connect_can(self):
        """Automatically connect to the CAN bus."""
        response = self.zmq_worker.send_command("connect_can", {
            "interface": AUTO_INTERFACE,
            "channel": AUTO_CHANNEL,
            "bitrate": AUTO_BITRATE
        })
        if response.get("status") == "success":
            self.update_status_bar("CAN connected. Ready to receive messages.")
        else:
            self.update_status_bar(f"Failed to connect to CAN: {response.get('message', 'Unknown error')}")

    def send_can_message_command(self, message_name, signal_data):
        """Send command to backend to send a CAN message."""
        response = self.zmq_worker.send_command("send_can_message", {
            "message_name": message_name,
            "signal_data": signal_data
        })
        self._handle_backend_response(response, "Send CAN Message")

    def _handle_backend_response(self, response, command_name="Command"):
        """Process responses received from the backend."""
        status = response.get("status", "unknown")
        message = response.get("message", "No message provided.")
        if status == "success":
            self.update_status_bar(f"{command_name} successful: {message}")
        else:
            self.display_error(f"{command_name} failed: {message}")

    def update_status_bar(self, message):
        """Update the application's status bar."""
        self.statusBar.showMessage(message)

    def display_error(self, message):
        """Display an error message."""
        QMessageBox.warning(self, "Error", message)
        self.statusBar.showMessage(f"ERROR: {message}", 5000)

    def update_display_data(self, signal_name, value):
        """Ultra-responsive signal updates (plots removed)."""
        signal_lower = signal_name.lower()
        # Optional whitelist filtering: if configured, ignore signals not explicitly listed
        if 'DISPLAY_SIGNAL_WHITELIST' in globals() and DISPLAY_SIGNAL_WHITELIST:
            if signal_lower not in DISPLAY_SIGNAL_WHITELIST:
                return
        # Decide immediate vs buffered based on config and criticality
        if signal_lower in self.gauges:
            if REALTIME_GAUGE_UPDATES or signal_lower in self.critical_signals:
                self.gauges[signal_lower].set_value(value)
            else:
                # Buffer latest value only
                self.pending_gauge_updates[signal_name] = {'value': value, 'time': time.time()}
        
        # Update indicators
        if signal_lower in self.indicators:
            indicator = self.indicators[signal_lower]
            threshold = getattr(indicator.config, 'threshold', 0.5)
            indicator.set_state(value > threshold)
        
        # Update seven-segment displays
        if signal_lower in self.displays:
            display = self.displays[signal_lower]
            # Check if this is a text signal (like gear) or numeric
            if signal_lower in ['gear', 'current_gear'] and isinstance(value, (int, float)):
                # Convert numeric gear to text (1,2,3,4,5,6,R,N,P)
                gear_map = {1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 
                           0: 'N', -1: 'R', 99: 'P'}
                display.set_text(gear_map.get(int(value), str(int(value))))
            else:
                # Numeric display
                display.set_value(value)

    def _process_pending_updates(self):
        """Process pending gauge updates (plots removed)."""
        if self.pending_gauge_updates:
            updates = self.pending_gauge_updates.copy()
            self.pending_gauge_updates.clear()
            for signal_name, update_data in updates.items():
                value = update_data['value']
                signal_lower = signal_name.lower()
                if signal_lower in self.gauges:
                    self.gauges[signal_lower].set_value(value)

    def flush_inflight(self):
        """Immediately clear any queued updates and drain ZMQ backlog to stop lingering movement."""
        # Clear GUI-side pending updates
        self.pending_gauge_updates.clear()
        # Ask worker to drain socket queue
        try:
            if hasattr(self, 'zmq_worker'):
                self.zmq_worker.flush_backlog()
        except Exception:
            pass

    # Plot update method removed

    def closeEvent(self, event):
        """Handle the application close event for graceful shutdown."""
        try:
            # Stop UI update timer
            if hasattr(self, 'ui_update_timer'):
                self.ui_update_timer.stop()
            
            # Stop the ZMQ worker
            if hasattr(self, 'zmq_worker'):
                self.zmq_worker.stop_listening()
            
            # Stop the ZMQ thread
            if hasattr(self, 'zmq_thread'):
                self.zmq_thread.quit()
                if not self.zmq_thread.wait(500):
                    print("Warning: ZMQ thread did not shut down cleanly, terminating...")
                    self.zmq_thread.terminate()
                    self.zmq_thread.wait(1000)
            
            event.accept()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            event.accept()

    def event(self, event):
        from PyQt6.QtGui import QMouseEvent, QAction
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtWidgets import QApplication, QMenu
        if event.type() in (event.Type.TouchBegin, event.Type.TouchUpdate):
            touch_points = event.points()  # PyQt6 uses points()
            if len(touch_points) == 1:
                pos = touch_points[0].position()
                widget = self.childAt(pos.toPoint())
                if widget:
                    mouse_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    QApplication.sendEvent(widget, mouse_event)
                    mouse_release = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    QApplication.sendEvent(widget, mouse_release)
                return True
            elif len(touch_points) == 2:
                pos1 = touch_points[0].position()
                pos2 = touch_points[1].position()
                avg_x = (pos1.x() + pos2.x()) / 2
                avg_y = (pos1.y() + pos2.y()) / 2
                avg_qpointf = QPointF(avg_x, avg_y)
                widget = self.childAt(QPointF(avg_x, avg_y).toPoint())
                if widget:
                    mouse_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, avg_qpointf, Qt.MouseButton.RightButton, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier)
                    QApplication.sendEvent(widget, mouse_event)
                    mouse_release = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, avg_qpointf, Qt.MouseButton.RightButton, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier)
                    QApplication.sendEvent(widget, mouse_release)
                return True
            elif len(touch_points) == 3:
                # Three finger tap: show layout selection menu at average position
                pos1 = touch_points[0].position()
                pos2 = touch_points[1].position()
                pos3 = touch_points[2].position()
                avg_x = (pos1.x() + pos2.x() + pos3.x()) / 3
                avg_y = (pos1.y() + pos2.y() + pos3.y()) / 3
                avg_qpointf = QPointF(avg_x, avg_y)
                menu = QMenu(self)
                current_layout = self.current_layout_name
                for layout_key, layout_config in LAYOUT_CONFIGS.items():
                    if layout_key != current_layout:
                        action = QAction(layout_config["name"], self)
                        action.triggered.connect(lambda checked, key=layout_key: self._apply_layout(key))
                        menu.addAction(action)
                menu.exec(self.mapToGlobal(avg_qpointf.toPoint()))
                return True
        return super().event(event)

    def mousePressEvent(self, event):
        from PyQt6.QtWidgets import QMenu, QAction
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.MiddleButton:
            # Center click: show layout selection menu at cursor position
            menu = QMenu(self)
            current_layout = self.current_layout_name
            for layout_key, layout_config in LAYOUT_CONFIGS.items():
                if layout_key != current_layout:
                    action = QAction(layout_config["name"], self)
                    action.triggered.connect(lambda checked, key=layout_key: self._apply_layout(key))
                    menu.addAction(action)
            menu.exec(event.globalPos())
            event.accept()
        else:
            super().mousePressEvent(event)