# communication/zmq_worker.py
"""ZeroMQ communication worker for CAN frontend."""

import json
import zmq
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Import performance settings
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import ZMQ_POLL_INTERVAL, MAX_MESSAGES_PER_CYCLE


class ZMQWorker(QObject):
    """Worker class for ZeroMQ communication with the backend."""
    
    # Signals
    decoded_message_received = pyqtSignal(dict)
    raw_message_received = pyqtSignal(dict)
    backend_status_message = pyqtSignal(str)
    backend_error_message = pyqtSignal(str)
    new_signal_value = pyqtSignal(str, float)

    def __init__(self, backend_ip, pub_port, req_rep_port):
        super().__init__()
        self.backend_ip = backend_ip
        self.pub_port = pub_port
        self.req_rep_port = req_rep_port
        self.context = zmq.Context()
        self.pub_socket = None
        self.req_socket = None
        self._listening = False

    def connect_sockets(self):
        """Connects frontend ZeroMQ sockets to the backend."""
        try:
            self._setup_pub_socket()
            self._setup_req_socket()
            self._listening = True
            QTimer.singleShot(0, self.start_listening_loop)
            return True
        except zmq.ZMQError as e:
            self.backend_error_message.emit(f"Failed to connect to backend: {e}")
            self._listening = False
            return False

    def _setup_pub_socket(self):
        """Sets up the PUB socket for receiving messages."""
        if self.pub_socket:
            self.pub_socket.disconnect(f"tcp://{self.backend_ip}:{self.pub_port}")
            self.pub_socket.close()
        self.pub_socket = self.context.socket(zmq.SUB)
        self.pub_socket.connect(f"tcp://{self.backend_ip}:{self.pub_port}")
        self.pub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.backend_status_message.emit(f"Connected to Backend PUB on {self.backend_ip}:{self.pub_port}")

    def _setup_req_socket(self):
        """Sets up the REQ socket for sending commands."""
        if self.req_socket:
            self.req_socket.disconnect(f"tcp://{self.backend_ip}:{self.req_rep_port}")
            self.req_socket.close()
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{self.backend_ip}:{self.req_rep_port}")
        self.backend_status_message.emit(f"Connected to Backend REQ/REP on {self.backend_ip}:{self.req_rep_port}")

    def start_listening_loop(self):
        """Use QTimer for non-blocking message reception."""
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self._poll_messages)
        self.message_timer.start(ZMQ_POLL_INTERVAL)  # Use config setting

    def _poll_messages(self):
        """Poll for messages without blocking."""
        if not self._listening or not self.pub_socket:
            return
            
        try:
            # Process multiple messages per timer cycle to handle bursts
            messages_processed = 0
            while messages_processed < MAX_MESSAGES_PER_CYCLE:  # Use config setting
                if self.pub_socket.poll(0) & zmq.POLLIN:  # Non-blocking poll
                    message = self.pub_socket.recv_json(zmq.NOBLOCK)
                    self._process_message(message)
                    messages_processed += 1
                else:
                    break
        except zmq.Again:
            # No messages available, normal condition
            pass
        except zmq.ZMQError as e:
            if self._listening:
                self.backend_error_message.emit(f"ZeroMQ error during receive: {e}")
            self._listening = False
            if hasattr(self, 'message_timer'):
                self.message_timer.stop()
        except Exception as e:
            if self._listening:
                self.backend_error_message.emit(f"Unexpected error in ZMQ listener: {e}")
            self._listening = False
            if hasattr(self, 'message_timer'):
                self.message_timer.stop()

    def _process_message(self, message):
        """Processes received messages and emits appropriate signals."""
        msg_type = message.get("type")
        if msg_type == "decoded":
            self.decoded_message_received.emit(message)
            for signal_name, value in message['data'].items():
                self.new_signal_value.emit(signal_name, float(value))
        elif msg_type == "raw":
            self.raw_message_received.emit(message)

    def send_command(self, command, args=None):
        """Sends a command to the backend via ZeroMQ REQ socket."""
        if not self.req_socket:
            self.backend_error_message.emit("Not connected to backend command socket.")
            return {"status": "error", "message": "Not connected to backend."}

        try:
            message = {"command": command, "args": args if args is not None else {}}
            self.req_socket.send_json(message)
            response = self.req_socket.recv_json()
            return response
        except Exception as e:
            self.backend_error_message.emit(f"Error sending command '{command}': {e}")
            return {"status": "error", "message": f"Client error: {e}"}

    def stop_listening(self):
        """Stops the ZeroMQ message reception loop and closes sockets."""
        self._listening = False
        self.backend_status_message.emit("Stopping ZMQ listener...")
        
        # Stop the timer
        if hasattr(self, 'message_timer'):
            self.message_timer.stop()
        
        try:
            if self.pub_socket:
                self.pub_socket.setsockopt(zmq.LINGER, 0)
                self.pub_socket.close()
                self.pub_socket = None
                
            if self.req_socket:
                self.req_socket.setsockopt(zmq.LINGER, 0)
                self.req_socket.close()
                self.req_socket = None
                
            if self.context:
                self.context.term()
                
            self.backend_status_message.emit("ZMQ sockets disconnected.")
        except Exception as e:
            self.backend_error_message.emit(f"Error during ZMQ shutdown: {e}")