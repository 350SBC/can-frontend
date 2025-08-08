# gui/main_window.py
"""Main window for the CAN dashboard application."""

import json
import time
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QLineEdit, QMessageBox, QFormLayout)
from PyQt6.QtCore import QThread, QTimer
import pyqtgraph as pg

from communication.zmq_worker import ZMQWorker
from widgets.gauges import RoundGauge, GaugeConfig
# from widgets.message_table import MessageTableWidget  # Uncomment when ready
from config.settings import *


class CANDashboardMainWindow(QMainWindow):
    """Main window for the CAN dashboard application."""
    
    def __init__(self):
        super().__init__()
        self.plot_data = {}
        self.plots = {}
        self.current_plot_row = 0
        self.current_plot_col = 0
        self.gauges = {}  # Store gauge references
        
        # Define gauge configurations
        self.gauge_configs = [
            GaugeConfig("Engine RPM", 0, 8000, ["rpm", "engine_rpm", "engine_speed"], 9, "RPM"),
            GaugeConfig("Speed", 0, 160, ["speed", "vehicle_speed", "mph"], 9, "MPH"),
            GaugeConfig("Temperature", 60, 120, ["coolant_temp", "engine_temp", "temperature"], 7, "°C"),
            GaugeConfig("Fuel Level", 0, 100, ["fuel_level", "fuel_percentage"], 6, "%"),
            GaugeConfig("Battery Voltage", 10, 16, ["battery_voltage", "voltage"], 7, "V"),
        ]
        
        self._setup_window()
        self._setup_zmq_worker()
        self._init_ui()
        self._connect_signals()
        self._init_plotting()
        self._auto_connect_and_configure()

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
        self.zmq_worker.new_signal_value.connect(self.update_plot_data)

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
        for config in self.gauge_configs[:3]:  # Show first 3 gauges
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
        """Set up the plot widget."""
        self.plot_widget = pg.GraphicsLayoutWidget(parent=self)
        self.plot_widget.ci.layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget.setMinimumHeight(PLOT_MINIMUM_HEIGHT)
        self.main_layout.addWidget(QLabel("Live Signal Plots:"))
        self.main_layout.addWidget(self.plot_widget)

    def _setup_send_message_section(self):
        """Set up the send message section."""
        send_message_group = QFormLayout()
        self.message_name_to_send_edit = QLineEdit()
        send_message_group.addRow("Message Name to Send:", self.message_name_to_send_edit)
        
        self.signal_data_to_send_edit = QLineEdit("{}")
        send_message_group.addRow("Signal Data (JSON):", self.signal_data_to_send_edit)
        
        self.send_can_button = QPushButton("Send CAN Message")
        self.send_can_button.clicked.connect(self.send_can_message_command)
        send_message_group.addRow(self.send_can_button)
        
        self.main_layout.addLayout(send_message_group)

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

    def send_can_message_command(self):
        """Send command to backend to send a CAN message."""
        msg_name = self.message_name_to_send_edit.text()
        signal_data_str = self.signal_data_to_send_edit.text()
        
        try:
            signal_data = json.loads(signal_data_str)
            if not isinstance(signal_data, dict):
                raise ValueError("Signal data must be a JSON object (dictionary).")
        except (json.JSONDecodeError, ValueError) as e:
            self.display_error(f"Invalid signal data: {e}")
            return

        response = self.zmq_worker.send_command("send_can_message", {
            "message_name": msg_name,
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

    def update_plot_data(self, signal_name, value):
        """Update live signal plots with new data and gauges."""
        current_time = time.time()

        # Update gauges if this signal matches any gauge
        signal_lower = signal_name.lower()
        if signal_lower in self.gauges:
            self.gauges[signal_lower].set_value(value)

        # Continue with existing plotting logic
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

        # Update the plot with new data
        data_entry['curve'].setData(data_entry['time'], data_entry['value'])

    def closeEvent(self, event):
        """Handle the application close event for graceful shutdown."""
        try:
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