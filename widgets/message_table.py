# widgets/message_table.py
"""Message table widget for displaying CAN messages."""

from datetime import datetime
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import QTimer


class MessageTableWidget(QTableWidget):
    """Custom table widget for displaying CAN messages."""
    
    def __init__(self, parent=None, max_buffer_size=50, update_interval=50):
        super().__init__(parent)
        self.max_buffer_size = max_buffer_size
        self.message_buffer = []
        self._setup_table()
        self._setup_timer(update_interval)

    def _setup_table(self):
        """Configure the table properties."""
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Timestamp", "ID", "Message Name", "Signals"])
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def _setup_timer(self, interval):
        """Set up the buffer flush timer."""
        self.table_update_timer = QTimer(self)
        self.table_update_timer.setInterval(interval)
        self.table_update_timer.timeout.connect(self._flush_message_buffer)
        self.table_update_timer.start()

    def add_message(self, message_data):
        """Add a message to the buffer."""
        self.message_buffer.append(message_data)
        if len(self.message_buffer) >= self.max_buffer_size:
            self._flush_message_buffer()

    def _flush_message_buffer(self):
        """Flush buffered messages to the table."""
        if not self.message_buffer:
            return
        
        for message_data in self.message_buffer:
            msg_type = message_data.get("type")
            if msg_type == "decoded":
                self._add_decoded_message(message_data)
            elif msg_type == "raw":
                self._add_raw_message(message_data)
        
        self.message_buffer.clear()
        self.scrollToBottom()

    def _add_decoded_message(self, message_data):
        """Add a decoded message to the table."""
        row_position = self.rowCount()
        self.insertRow(row_position)

        timestamp = message_data.get("timestamp")
        id_hex = message_data.get("id_hex")
        message_name = message_data.get("name")
        decoded_data = message_data.get("data", {})

        ts_item = QTableWidgetItem(datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3])
        id_item = QTableWidgetItem(id_hex)
        name_item = QTableWidgetItem(message_name)

        signals_str = ", ".join([
            f"{name}: {value:.2f}" if isinstance(value, (int, float)) else f"{name}: {value}"
            for name, value in decoded_data.items()
        ])
        signals_item = QTableWidgetItem(signals_str)

        self.setItem(row_position, 0, ts_item)
        self.setItem(row_position, 1, id_item)
        self.setItem(row_position, 2, name_item)
        self.setItem(row_position, 3, signals_item)

    def _add_raw_message(self, message_data):
        """Add a raw message to the table."""
        row_position = self.rowCount()
        self.insertRow(row_position)

        timestamp = message_data.get("timestamp")
        id_hex = message_data.get("id_hex")
        data_hex = message_data.get("data_hex")

        ts_item = QTableWidgetItem(datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3])
        id_item = QTableWidgetItem(id_hex)
        name_item = QTableWidgetItem("UNKNOWN MESSAGE (RAW)")
        raw_data_item = QTableWidgetItem(f"Raw Data: {data_hex}")

        self.setItem(row_position, 0, ts_item)
        self.setItem(row_position, 1, id_item)
        self.setItem(row_position, 2, name_item)
        self.setItem(row_position, 3, raw_data_item)

    def stop_timer(self):
        """Stop the update timer."""
        if hasattr(self, 'table_update_timer'):
            self.table_update_timer.stop()