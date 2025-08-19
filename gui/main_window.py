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
                            QFrame)
from PyQt6.QtCore import QThread, QTimer, QPropertyAnimation, QRect, pyqtSignal
import pyqtgraph as pg

from communication.zmq_worker import ZMQWorker
from widgets.gauges import RoundGauge, GaugeConfig, ModernGauge, NeonGauge
from widgets.send_message_widget import CollapsibleSendMessageWidget  # Import the new widget
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
        self.plot_data = {}
        self.plots = {}
        self.current_plot_row = 0
        self.current_plot_col = 0
        self.gauges = {}  # Store gauge references
        
        # Performance optimization: separate handling for gauges and plots
        self.pending_gauge_updates = {}  # Buffer for gauge updates (faster)
        self.pending_plot_updates = {}   # Buffer for plot updates (slower)
        self.last_gauge_update_time = {}  # Track last gauge update time
        self.last_plot_update_time = {}   # Track last plot update time
        self.gauge_update_interval = GAUGE_UPDATE_INTERVAL   # Ultra-fast for gauges
        self.plot_update_interval = PLOT_UPDATE_INTERVAL     # Slower for plots
        
        # Critical signals that get immediate updates (bypass buffering)
        self.critical_signals = {"rpm", "engine_rpm", "engine_speed", "speed", "vehicle_speed"}
        
        # Define gauge configurations
        self.gauge_configs = [
            GaugeConfig("Engine RPM", 0, 6500, ["rpm", "engine_rpm", "engine_speed"], 14, "RPM"),
            GaugeConfig("Speed", 0, 100, ["speed", "vehicle_speed", "mph"], 21, "MPH"),
            GaugeConfig("Temperature", 60, 220, ["cts", "engine_temp", "temperature"], 7, "°f"),
            GaugeConfig("AFR", 0, 20, ["afr", "air_fuel_ratio"], 6, ":1"),
            GaugeConfig("Battery Voltage", 10, 16, ["battery_voltage", "voltage"], 7, "V"),
        ]
        
        self._setup_window()
        self._setup_zmq_worker()
        self._init_ui()
        self._connect_signals()
        self._init_plotting()
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
        self._setup_gauges()
        # self._setup_message_table()  # Uncomment when ready
        self._setup_plot_widget()
        self._setup_send_message_section()
        self._setup_status_bar()

    def _setup_gauges(self):
        """Set up gauge widgets based on configurations."""
        # Create a scrollable area for gauges or use a grid
        gauge_layout = QHBoxLayout()
        
        # Create gauges from configurations (limit to first few for space)
        gauge_style = globals().get('GAUGE_STYLE', 'classic')
        for config in self.gauge_configs[:3]:  # Show first 3 gauges
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
            
            # Store gauge with signal name mapping
            for signal_name in config.signal_names:
                self.gauges[signal_name.lower()] = gauge
            
            gauge_layout.addWidget(gauge)
        
        gauge_layout.addStretch()
        self.main_layout.addLayout(gauge_layout)

    def _setup_plot_widget(self):
        """Set up the plot widget as a collapsible widget."""
        # Create collapsible container
        self.plot_container = CollapsibleWidget("▶ Live Signal Plots")
        
        # Create the plot widget
        self.plot_widget = pg.GraphicsLayoutWidget(parent=self)
        self.plot_widget.ci.layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget.setMinimumHeight(PLOT_MINIMUM_HEIGHT)
        
        # Add plot widget to the collapsible container
        self.plot_container.add_content_widget(self.plot_widget)
        
        # Add to main layout
        self.main_layout.addWidget(self.plot_container)

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

    def _init_plotting(self):
        """Initialize plotting parameters."""
        pass

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
        """Ultra-responsive signal updates with immediate processing for critical signals."""
        current_time = time.time()
        signal_lower = signal_name.lower()
        
        # Critical signals get immediate gauge updates (no buffering)
        if signal_lower in self.critical_signals and signal_lower in self.gauges:
            self.gauges[signal_lower].set_value(value)
            # Still add to plot buffer for plotting
            self.pending_plot_updates[signal_name] = {'value': value, 'time': current_time}
            return
        
        # Handle other gauge updates with minimal delay
        if signal_lower in self.gauges:
            self.pending_gauge_updates[signal_name] = {'value': value, 'time': current_time}
        
        # Handle plot updates with rate limiting (for performance)
        if signal_name in self.last_plot_update_time:
            time_diff = (current_time - self.last_plot_update_time[signal_name]) * 1000
            if time_diff < self.plot_update_interval:
                return
        
        self.last_plot_update_time[signal_name] = current_time
        self.pending_plot_updates[signal_name] = {'value': value, 'time': current_time}

    def _process_pending_updates(self):
        """Process pending gauge and plot updates separately for optimal performance."""
        # Process gauge updates (higher priority, more frequent)
        if self.pending_gauge_updates:
            gauge_updates = self.pending_gauge_updates.copy()
            self.pending_gauge_updates.clear()
            
            for signal_name, update_data in gauge_updates.items():
                value = update_data['value']
                signal_lower = signal_name.lower()
                if signal_lower in self.gauges:
                    self.gauges[signal_lower].set_value(value)
        
        # Process plot updates (lower priority, less frequent)
        if self.pending_plot_updates:
            plot_updates = self.pending_plot_updates.copy()
            self.pending_plot_updates.clear()
            
            for signal_name, update_data in plot_updates.items():
                value = update_data['value']
                current_time = update_data['time']
                self._update_plot_data(signal_name, value, current_time)

    def _update_plot_data(self, signal_name, value, current_time):
        """Optimized plot data update method."""
        if signal_name not in self.plot_data:
            total_plots = len(self.plots)
            if total_plots >= MAX_PLOTS_PER_ROW * MAX_PLOT_ROWS:
                return

            # Create a new plot for this signal
            plot_item = self.plot_widget.addPlot(
                row=self.current_plot_row,
                col=self.current_plot_col,
                title=signal_name
            )
            plot_item.setLabel('bottom', "Time", units='s')
            plot_item.setLabel('left', "Value")
            plot_item.showGrid(x=True, y=True)
            plot_curve = plot_item.plot(pen='y')

            # Store references to data and curve
            self.plot_data[signal_name] = {
                'time': [], 'value': [], 'curve': plot_curve, 'start_time': current_time
            }
            self.plots[signal_name] = plot_item

            # Move to the next position in the plot grid
            self.current_plot_col += 1
            if self.current_plot_col >= MAX_PLOTS_PER_ROW:
                self.current_plot_col = 0
                self.current_plot_row += 1

        data_entry = self.plot_data[signal_name]
        data_entry['time'].append(current_time - data_entry['start_time'])
        data_entry['value'].append(value)

        # Keep only the most recent points for performance
        if len(data_entry['time']) > MAX_PLOT_POINTS:
            data_entry['time'] = data_entry['time'][-MAX_PLOT_POINTS:]
            data_entry['value'] = data_entry['value'][-MAX_PLOT_POINTS:]

        # Update the plot with new data (this is still needed for real-time plotting)
        data_entry['curve'].setData(data_entry['time'], data_entry['value'])

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