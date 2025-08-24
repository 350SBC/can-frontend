# communication/zmq_worker.py
"""ZeroMQ communication worker for CAN frontend."""

import json
import zmq
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Import performance settings
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    ZMQ_POLL_INTERVAL,
    MAX_MESSAGES_PER_CYCLE,
    DISPLAY_SIGNAL_WHITELIST,
    DISPLAY_SIGNAL_BLACKLIST,
    SIGNAL_RATE_LIMITS,
    MAX_SIGNALS_PER_MESSAGE,
    FAST_FORWARD_SIGNAL_UPDATES,
    ZMQ_SUB_RCVHWM,
    ZMQ_SUB_CONFLATE,
    BACKLOG_STRATEGY,
    MAX_DRAIN_PER_POLL,
    MERGE_SIGNALS_DURING_COLLAPSE,
)


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
        # Track last emission times for rate limiting
        self._last_signal_emit = {}

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
        # Apply socket options to reduce backlog
        try:
            if ZMQ_SUB_RCVHWM is not None:
                self.pub_socket.setsockopt(zmq.RCVHWM, ZMQ_SUB_RCVHWM)
            if ZMQ_SUB_CONFLATE:
                self.pub_socket.setsockopt(zmq.CONFLATE, 1)
        except Exception:
            pass
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
        """Aggressively poll for messages to minimize latency."""
        if not self._listening or not self.pub_socket:
            return
        try:
            if BACKLOG_STRATEGY == "collapse_latest":
                # Drain as many messages as are immediately available (bounded) and keep only latest per signal
                drained = 0
                latest_messages = []
                while drained < MAX_DRAIN_PER_POLL and (self.pub_socket.poll(0) & zmq.POLLIN):
                    try:
                        msg = self.pub_socket.recv_json(zmq.NOBLOCK)
                        latest_messages.append(msg)
                        drained += 1
                    except zmq.Again:
                        break
                if latest_messages:
                    if MERGE_SIGNALS_DURING_COLLAPSE:
                        # Build one synthetic combined decoded message using last value per signal
                        combined = None
                        signal_map = {}
                        for m in latest_messages:
                            if m.get('type') != 'decoded':
                                continue
                            if combined is None:
                                combined = {k: v for k, v in m.items() if k != 'data'}
                                combined['type'] = 'decoded'
                                combined['data'] = {}
                            for s, val in m.get('data', {}).items():
                                signal_map[s] = val
                        if combined is not None:
                            combined['data'].update(signal_map)
                            self._process_message(combined)
                    else:
                        # Just process only the last decoded message encountered
                        for m in reversed(latest_messages):
                            if m.get('type') == 'decoded':
                                self._process_message(m)
                                break
            else:
                # Original bounded loop
                messages_processed = 0
                while messages_processed < MAX_MESSAGES_PER_CYCLE:
                    if self.pub_socket.poll(0) & zmq.POLLIN:
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
            data_items = list(message.get('data', {}).items())

            # Apply per-message cap if configured
            if MAX_SIGNALS_PER_MESSAGE > 0 and len(data_items) > MAX_SIGNALS_PER_MESSAGE:
                data_items = data_items[:MAX_SIGNALS_PER_MESSAGE]

            # Optional fast-forward: keep only most recent per signal (compress backlog)
            if FAST_FORWARD_SIGNAL_UPDATES:
                compressed = {}
                for k, v in data_items:
                    compressed[k] = v
                data_iterable = compressed.items()
            else:
                data_iterable = data_items

            for signal_name, value in data_iterable:
                sig_l = signal_name.lower()

                # Whitelist filtering
                if DISPLAY_SIGNAL_WHITELIST and sig_l not in DISPLAY_SIGNAL_WHITELIST:
                    continue
                # Blacklist filtering
                if sig_l in DISPLAY_SIGNAL_BLACKLIST:
                    continue
                # Rate limiting
                if sig_l in SIGNAL_RATE_LIMITS:
                    min_interval = SIGNAL_RATE_LIMITS[sig_l]
                    last_t = self._last_signal_emit.get(sig_l, 0)
                    # Use time.monotonic for stable intervals
                    import time as _t
                    now = _t.monotonic()
                    if now - last_t < min_interval:
                        continue
                    self._last_signal_emit[sig_l] = now

                # Emit filtered signal
                try:
                    self.new_signal_value.emit(signal_name, float(value))
                except Exception:
                    # Ignore malformed values
                    pass
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

    def flush_backlog(self):
        """Attempt to drain any immediately available messages without processing backlog slowly."""
        if not self.pub_socket:
            return
        try:
            drained = 0
            while self.pub_socket.poll(0) & zmq.POLLIN:
                _ = self.pub_socket.recv_json(zmq.NOBLOCK)
                drained += 1
                if drained > 1000:  # safety cap
                    break
            if drained:
                self.backend_status_message.emit(f"Flushed {drained} queued messages.")
        except Exception:
            pass