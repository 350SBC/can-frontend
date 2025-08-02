import sys
import os
import time
from datetime import datetime
import json
import zmq

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QComboBox, QMessageBox,
    QFormLayout, QGridLayout, QScrollArea
)
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer

# Import for plotting (install with: pip install pyqtgraph)
import pyqtgraph as pg

# ZeroMQ Ports and Backend IP
BACKEND_IP = "pi4" # !!! IMPORTANT: CHANGE THIS TO THE ACTUAL IP OF YOUR BACKEND MACHINE !!!
PUB_PORT = "5556"        # Port for receiving CAN messages (from backend's PUB socket)
REQ_REP_PORT = "5557"    # Port for sending commands and receiving responses (to backend's REP socket)

# --- Worker for ZeroMQ Communication (Frontend side) ---
class ZMQWorker(QObject):
    # Signals to send received data/status/errors to the main GUI thread
    decoded_message_received = pyqtSignal(dict) # Data dictionary for decoded message
    raw_message_received = pyqtSignal(dict)     # Data dictionary for raw message
    backend_status_message = pyqtSignal(str)    # General status updates from worker
    backend_error_message = pyqtSignal(str)     # Error messages from worker
    new_signal_value = pyqtSignal(str, float)   # signal_name, value (for plotting)

    def __init__(self, backend_ip, pub_port, req_rep_port):
        super().__init__()
        self.backend_ip = backend_ip
        self.pub_port = pub_port
        self.req_rep_port = req_rep_port

        self.context = zmq.Context()
        self.pub_socket = None # ZeroMQ SUB socket (subscriber to backend's PUB)
        self.req_socket = None # ZeroMQ REQ socket (requester to backend's REP)
        self._listening = False # Flag to control the message reception loop

    def connect_sockets(self):
        """Connects frontend ZeroMQ sockets to the backend."""
        try:
            # Subscriber socket for CAN messages
            if self.pub_socket:
                self.pub_socket.disconnect(f"tcp://{self.backend_ip}:{self.pub_port}")
                self.pub_socket.close()
            self.pub_socket = self.context.socket(zmq.SUB)
            # --- ZeroMQ SUB: Connect to backend's PUB ---
            self.pub_socket.connect(f"tcp://{self.backend_ip}:{self.pub_port}")
            self.pub_socket.setsockopt_string(zmq.SUBSCRIBE, "") # Subscribe to ALL messages
            self.backend_status_message.emit(f"Connected to Backend PUB on {self.backend_ip}:{self.pub_port}")

            # Requester socket for commands
            if self.req_socket:
                self.req_socket.disconnect(f"tcp://{self.backend_ip}:{self.req_rep_port}")
                self.req_socket.close()
            self.req_socket = self.context.socket(zmq.REQ)
            # --- ZeroMQ REQ: Connect to backend's REP ---
            self.req_socket.connect(f"tcp://{self.backend_ip}:{self.req_rep_port}")
            self.backend_status_message.emit(f"Connected to Backend REQ/REP on {self.backend_ip}:{self.req_rep_port}")

            self._listening = True
            # Start the message reception loop in this worker's thread
            QTimer.singleShot(0, self.start_listening_loop) # Schedule call once thread is fully running
            return True
        except zmq.ZMQError as e:
            self.backend_error_message.emit(f"Failed to connect to backend: {e}")
            self._listening = False
            return False

    def start_listening_loop(self):
        """Continuously receives messages from the backend's PUB socket."""
        # This loop runs in the ZMQWorker's separate QThread
        while self._listening:
            try:
                # Use poll to non-blockingly check for messages, allowing graceful shutdown
                if self.pub_socket.poll(100) & zmq.POLLIN: # 100ms timeout
                    message = self.pub_socket.recv_json() # Receive JSON message
                    #print(f"Frontend worker received: {message.get('id_hex', 'N/A')}") # <-- ADD THIS
                    msg_type = message.get("type")
                    if msg_type == "decoded":
                        self.decoded_message_received.emit(message) # Emit signal for decoded data
                        # Also emit individual signals for plotting
                        for signal_name, value in message['data'].items():
                            self.new_signal_value.emit(signal_name, float(value))
                    elif msg_type == "raw":
                        self.raw_message_received.emit(message) # Emit signal for raw data
                else:
                    pass # No message, continue loop (check self._listening flag)
            except zmq.ZMQError as e:
                self.backend_error_message.emit(f"ZeroMQ error during receive: {e}")
                self._listening = False # Stop listening on error
                break
            except json.JSONDecodeError as e:
                self.backend_error_message.emit(f"JSON decode error from backend: {e}")
            except Exception as e:
                self.backend_error_message.emit(f"Unexpected error in ZMQ listener: {e}")
                self._listening = False
                break
        self.backend_status_message.emit("ZMQ listener stopped.")


    def send_command(self, command, args=None):
        """Sends a command to the backend via ZeroMQ REQ socket and waits for a response."""
        if not self.req_socket:
            self.backend_error_message.emit("Not connected to backend command socket.")
            return {"status": "error", "message": "Not connected to backend."}

        try:
            message = {"command": command, "args": args if args is not None else {}}
            # --- ZeroMQ REQ: Send command ---
            self.req_socket.send_json(message)
            # --- ZeroMQ REQ: Receive synchronous response ---
            response = self.req_socket.recv_json()
            return response
        except zmq.ZMQError as e:
            self.backend_error_message.emit(f"ZeroMQ error sending command '{command}': {e}")
            return {"status": "error", "message": f"Network error: {e}"}
        except Exception as e:
            self.backend_error_message.emit(f"Error sending command '{command}': {e}")
            return {"status": "error", "message": f"Client error: {e}"}

    def stop_listening(self):
        """Stops the ZeroMQ message reception loop and closes sockets."""
        self._listening = False
        self.backend_status_message.emit("Stopping ZMQ listener...")
        # Close and disconnect sockets cleanly
        if self.pub_socket:
            self.pub_socket.disconnect(f"tcp://{self.backend_ip}:{self.pub_port}")
            self.pub_socket.close()
            self.pub_socket = None
        if self.req_socket:
            self.req_socket.disconnect(f"tcp://{self.backend_ip}:{self.req_rep_port}")
            self.req_socket.close()
            self.req_socket = None
        self.backend_status_message.emit("ZMQ sockets disconnected.")
        # Request the QThread containing this worker to quit
        # self.thread().quit() # This line caused issues, removed for safer shutdown via QThread.wait() in main window

# --- Main Application Window ---
class CANDashboardFrontend(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAN Dashboard Frontend")
        self.setGeometry(10, 10, 1400, 900) # Initial window size

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Initialize ZMQWorker and move to a QThread
        self.zmq_worker = ZMQWorker(BACKEND_IP, PUB_PORT, REQ_REP_PORT)
        self.zmq_thread = QThread()
        self.zmq_worker.moveToThread(self.zmq_thread)

        # Connect signals from the ZMQWorker to slots in the main GUI thread
        self.zmq_worker.decoded_message_received.connect(self.update_decoded_messages_table)
        self.zmq_worker.raw_message_received.connect(self.update_raw_messages_table)
        self.zmq_worker.backend_status_message.connect(self.update_status_bar)
        self.zmq_worker.backend_error_message.connect(self.display_error)
        self.zmq_worker.new_signal_value.connect(self.update_plot_data)

        # Start the worker thread (it will then wait for connect_sockets call)
        self.zmq_thread.start()
        
        # Initialize message buffering for table updates
        self.message_buffer = []
        self.max_buffer_size = 50 # Or whatever makes sense for your message rate
        self.table_update_timer = QTimer(self)
        self.table_update_timer.setInterval(50) # Update table every 50ms (adjust as needed)
        self.table_update_timer.timeout.connect(self._flush_message_buffer)
        self.table_update_timer.start()

        self._init_ui() # Setup the graphical user interface elements
        self._init_plotting() # Setup plotting area with PyQtGraph
        
        # Auto-connect and configure everything
        self.auto_connect_and_configure()

        self.plot_data = {} # Dictionary to store data for plots
        self.max_plot_points = 500 # Max data points to show in plots for performance

    def auto_connect_and_configure(self):
        """Automatically connects to the backend and configures DBC and CAN connection."""
        self.update_status_bar("Auto-connecting to backend...")
        # Use a single-shot timer to ensure this runs after the UI is fully initialized
        QTimer.singleShot(500, self._auto_setup_sequence)

    def _auto_setup_sequence(self):
        """Performs automatic setup sequence: connect to backend, load DBC, connect CAN."""
        # First connect to backend
        self.zmq_worker.backend_ip = BACKEND_IP
        QTimer.singleShot(0, self.zmq_worker.connect_sockets)
        self.update_status_bar("Connected to backend. Loading DBC...")
        # Wait a moment then load DBC
        QTimer.singleShot(1000, self._auto_load_dbc)

    def _auto_load_dbc(self):
        """Automatically loads the DBC file."""
        response = self.zmq_worker.send_command("load_dbc", {"file_path": "dbc/test.dbc"})
        if response.get("status") == "success":
            self.update_status_bar("DBC loaded. Connecting to CAN...")
            # Wait a moment then connect to CAN
            QTimer.singleShot(1000, self._auto_connect_can)
        else:
            self.update_status_bar(f"Failed to load DBC: {response.get('message', 'Unknown error')}")

    def _auto_connect_can(self):
        """Automatically connects to the CAN bus."""
        response = self.zmq_worker.send_command("connect_can", {
            "interface": "socketcan",
            "channel": "vcan0", 
            "bitrate": 500000
        })
        if response.get("status") == "success":
            self.update_status_bar("CAN connected. Ready to receive messages.")
        else:
            self.update_status_bar(f"Failed to connect to CAN: {response.get('message', 'Unknown error')}")

    def _init_ui(self):
        # --- Middle Section: Data Display (Table for messages) ---
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(4)
        self.message_table.setHorizontalHeaderLabels(["Timestamp", "ID", "Message Name", "Signals"])
        self.message_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.message_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.message_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.message_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.message_table.verticalHeader().setVisible(False)
        self.message_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.message_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.main_layout.addWidget(QLabel("Live CAN Messages:"))
        self.main_layout.addWidget(self.message_table)

        # --- Plotting Area ---
        self.plot_widget = pg.GraphicsLayoutWidget(parent=self)
        self.plot_widget.ci.layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget.setMinimumHeight(900)  # Larger minimum height
        self.main_layout.addWidget(self.plot_widget)
        self.main_layout.addWidget(QLabel("Live Signal Plots (Max 4 for now):"))

        # --- Send Message Section (Optional) ---
        send_message_group = QFormLayout()
        self.message_name_to_send_edit = QLineEdit()
        send_message_group.addRow("Message Name to Send:", self.message_name_to_send_edit)
        self.signal_data_to_send_edit = QLineEdit("{}") # JSON format for signal data
        send_message_group.addRow("Signal Data (JSON):", self.signal_data_to_send_edit)
        self.send_can_button = QPushButton("Send CAN Message")
        self.send_can_button.clicked.connect(self.send_can_message_command)
        send_message_group.addRow(self.send_can_button)
        self.main_layout.addLayout(send_message_group)

        # --- Status Bar ---
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("Ready")

    def _init_plotting(self):
        # Dictionary to hold PyQtGraph PlotItem objects
        self.plots = {} # {signal_name: PlotItem}
        # Keep track of where to add new plots in the grid layout
        self.current_plot_row = 0
        self.current_plot_col = 0
        self.max_plots_per_row = 3
        self.max_plot_rows = 3

    def send_can_message_command(self):
        """Sends command to backend to send a CAN message."""
        msg_name = self.message_name_to_send_edit.text()
        signal_data_str = self.signal_data_to_send_edit.text()
        try:
            signal_data = json.loads(signal_data_str)
            if not isinstance(signal_data, dict):
                raise ValueError("Signal data must be a JSON object (dictionary).")
        except json.JSONDecodeError:
            self.display_error("Invalid JSON format for Signal Data.")
            return
        except ValueError as e:
            self.display_error(str(e))
            return

        response = self.zmq_worker.send_command("send_can_message", {
            "message_name": msg_name,
            "signal_data": signal_data
        })
        self.handle_backend_response(response, "Send CAN Message")


    def handle_backend_response(self, response, command_name="Command"):
        """Processes responses received from the backend for commands."""
        status = response.get("status", "unknown")
        message = response.get("message", "No message provided.")
        if status == "success":
            self.update_status_bar(f"{command_name} successful: {message}")
        else:
            self.display_error(f"{command_name} failed: {message}")

    def _flush_message_buffer(self):
        """Flushes buffered messages to the table for better performance."""
        if not self.message_buffer:
            return
        
        for message_data in self.message_buffer:
            msg_type = message_data.get("type")
            if msg_type == "decoded":
                self._add_decoded_message_to_table(message_data)
            elif msg_type == "raw":
                self._add_raw_message_to_table(message_data)
        
        self.message_buffer.clear()
        self.message_table.scrollToBottom()

    def update_decoded_messages_table(self, message_data):
        """Slot to buffer decoded CAN messages for batch table updates."""
        self.message_buffer.append(message_data)
        if len(self.message_buffer) >= self.max_buffer_size:
            self._flush_message_buffer()

    def update_raw_messages_table(self, message_data):
        """Slot to buffer raw CAN messages for batch table updates."""
        self.message_buffer.append(message_data)
        if len(self.message_buffer) >= self.max_buffer_size:
            self._flush_message_buffer()

    def _add_decoded_message_to_table(self, message_data):
        """Adds a decoded message to the table."""
        row_position = self.message_table.rowCount()
        self.message_table.insertRow(row_position)

        timestamp = message_data.get("timestamp")
        id_hex = message_data.get("id_hex")
        message_name = message_data.get("name")
        decoded_data = message_data.get("data", {})

        ts_item = QTableWidgetItem(datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3])
        id_item = QTableWidgetItem(id_hex)
        name_item = QTableWidgetItem(message_name)

        signals_str = ", ".join([f"{name}: {value:.2f}" if isinstance(value, (int, float)) else f"{name}: {value}"
                                 for name, value in decoded_data.items()])
        signals_item = QTableWidgetItem(signals_str)

        self.message_table.setItem(row_position, 0, ts_item)
        self.message_table.setItem(row_position, 1, id_item)
        self.message_table.setItem(row_position, 2, name_item)
        self.message_table.setItem(row_position, 3, signals_item)

    def _add_raw_message_to_table(self, message_data):
        """Adds a raw message to the table."""
        row_position = self.message_table.rowCount()
        self.message_table.insertRow(row_position)

        timestamp = message_data.get("timestamp")
        id_hex = message_data.get("id_hex")
        data_hex = message_data.get("data_hex")

        ts_item = QTableWidgetItem(datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3])
        id_item = QTableWidgetItem(id_hex)
        name_item = QTableWidgetItem("UNKNOWN MESSAGE (RAW)")
        raw_data_item = QTableWidgetItem(f"Raw Data: {data_hex}")

        self.message_table.setItem(row_position, 0, ts_item)
        self.message_table.setItem(row_position, 1, id_item)
        self.message_table.setItem(row_position, 2, name_item)
        self.message_table.setItem(row_position, 3, raw_data_item)
        self.message_table.scrollToBottom()


    def update_status_bar(self, message):
        """Updates the application's status bar."""
        self.statusBar.showMessage(message)

    def display_error(self, message):
        """Displays an error message using a QMessageBox and updates status bar."""
        QMessageBox.warning(self, "Error", message)
        self.statusBar.showMessage(f"ERROR: {message}", 5000)

    def update_plot_data(self, signal_name, value):
        """Slot to update live signal plots with new data."""
        current_time = time.time()

        if signal_name not in self.plot_data:
            total_plots = len(self.plots)
            if total_plots >= self.max_plots_per_row * self.max_plot_rows:
                return # Max plots reached, don't create new ones

            # Create a new plot for this signal in the PyQtGraph layout
            plot_item = self.plot_widget.addPlot(row=self.current_plot_row, col=self.current_plot_col, title=signal_name)
            plot_item.setLabel('bottom', "Time", units='s')
            plot_item.setLabel('left', "Value")
            plot_item.showGrid(x=True, y=True)
            plot_curve = plot_item.plot(pen='y') # Get the PlotDataItem for updating

            # Store references to data and curve
            self.plot_data[signal_name] = {'time': [], 'value': [], 'curve': plot_curve, 'start_time': current_time}
            self.plots[signal_name] = plot_item # Store the plot item itself

            # Move to the next position in the plot grid
            self.current_plot_col += 1
            if self.current_plot_col >= self.max_plots_per_row:
                self.current_plot_col = 0
                self.current_plot_row += 1

        data_entry = self.plot_data[signal_name]
        data_entry['time'].append(current_time - data_entry['start_time']) # Time relative to plot start
        data_entry['value'].append(value)

        # Keep only the most recent 'max_plot_points' for performance
        if len(data_entry['time']) > self.max_plot_points:
            data_entry['time'] = data_entry['time'][-self.max_plot_points:]
            data_entry['value'] = data_entry['value'][-self.max_plot_points:]

        # Update the plot with new data
        data_entry['curve'].setData(data_entry['time'], data_entry['value'])

    def closeEvent(self, event):
        """Handles the application close event for graceful shutdown."""
        # Ensure the ZMQ worker thread and its sockets are properly stopped
        self.zmq_worker.stop_listening()
        self.zmq_thread.quit() # Request the QThread to stop its event loop
        self.zmq_thread.wait(2000) # Wait up to 2 seconds for the thread to finish cleanly
        super().closeEvent(event) # Call base class close event


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CANDashboardFrontend()
    window.show()
    sys.exit(app.exec())