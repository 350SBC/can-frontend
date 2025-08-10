# widgets/send_message_widget.py
"""Widget for sending CAN messages."""

import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                            QPushButton, QLabel, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class SendMessageWidget(QWidget):
    """Widget for sending CAN messages with a clean interface."""
    
    # Signal emitted when user wants to send a message
    send_message_requested = pyqtSignal(str, dict)  # message_name, signal_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Send CAN Message")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Form layout for inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        
        # Message name input
        self.message_name_edit = QLineEdit()
        self.message_name_edit.setPlaceholderText("e.g., EngineData")
        form_layout.addRow("Message Name:", self.message_name_edit)
        
        # Signal data input
        self.signal_data_edit = QLineEdit()
        self.signal_data_edit.setText('{"rpm": 2500, "throttle": 45.2}')
        self.signal_data_edit.setPlaceholderText('{"signal_name": value}')
        form_layout.addRow("Signal Data (JSON):", self.signal_data_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.send_button = QPushButton("Send CAN Message")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c41e3a;
            }
        """)
        
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Example/help text
        help_label = QLabel(
            "Example: Message='EngineData', Data='{\"rpm\": 2500, \"throttle\": 45.2}'"
        )
        help_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                font-size: 10px;
                padding: 5px;
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.send_button.clicked.connect(self._on_send_clicked)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        
        # Enable/disable send button based on input
        self.message_name_edit.textChanged.connect(self._validate_inputs)
        self.signal_data_edit.textChanged.connect(self._validate_inputs)
    
    def _validate_inputs(self):
        """Validate inputs and enable/disable send button."""
        message_name = self.message_name_edit.text().strip()
        signal_data = self.signal_data_edit.text().strip()
        
        # Basic validation
        has_message_name = len(message_name) > 0
        has_valid_json = self._is_valid_json(signal_data)
        
        self.send_button.setEnabled(has_message_name and has_valid_json)
    
    def _is_valid_json(self, text):
        """Check if text is valid JSON."""
        try:
            data = json.loads(text)
            return isinstance(data, dict)
        except (json.JSONDecodeError, ValueError):
            return False
    
    def _on_send_clicked(self):
        """Handle send button click."""
        message_name = self.message_name_edit.text().strip()
        signal_data_text = self.signal_data_edit.text().strip()
        
        try:
            signal_data = json.loads(signal_data_text)
            if not isinstance(signal_data, dict):
                raise ValueError("Signal data must be a JSON object (dictionary).")
            
            # Emit the signal for the main window to handle
            self.send_message_requested.emit(message_name, signal_data)
            
        except (json.JSONDecodeError, ValueError) as e:
            # Show error message
            QMessageBox.warning(
                self, 
                "Invalid Input", 
                f"Invalid signal data: {str(e)}\n\n"
                "Please enter valid JSON in the format: {\"signal_name\": value}"
            )
    
    def _on_clear_clicked(self):
        """Handle clear button click."""
        self.message_name_edit.clear()
        self.signal_data_edit.setText('{}')
    
    def set_message_name(self, name):
        """Set the message name programmatically."""
        self.message_name_edit.setText(name)
    
    def set_signal_data(self, data):
        """Set the signal data programmatically."""
        if isinstance(data, dict):
            self.signal_data_edit.setText(json.dumps(data, separators=(',', ': ')))
        else:
            self.signal_data_edit.setText(str(data))
    
    def get_message_name(self):
        """Get the current message name."""
        return self.message_name_edit.text().strip()
    
    def get_signal_data(self):
        """Get the current signal data as a dictionary."""
        try:
            return json.loads(self.signal_data_edit.text().strip())
        except (json.JSONDecodeError, ValueError):
            return {}


class CollapsibleSendMessageWidget(QWidget):
    """Collapsible version of the send message widget."""
    
    # Forward the signal from the inner widget
    send_message_requested = pyqtSignal(str, dict)
    
    def __init__(self, title="Send CAN Messages", parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.title = title
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)
        
        # Toggle button
        self.toggle_button = QPushButton(f"▶ {title}")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
                background-color: #4a4a4a;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle)
        
        # Content widget (the actual send message widget)
        self.send_widget = SendMessageWidget()
        self.send_widget.setStyleSheet("""
            SendMessageWidget {
                border: 1px solid #ccc;
                border-top: none;
                background-color: white;
            }
        """)
        
        # Forward the signal
        self.send_widget.send_message_requested.connect(self.send_message_requested.emit)
        
        # Add to layout
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.send_widget)
        
        # Start collapsed
        self.send_widget.hide()
    
    def toggle(self):
        """Toggle visibility."""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.send_widget.show()
            self.toggle_button.setText(f"▼ {self.title}")
        else:
            self.send_widget.hide()
            self.toggle_button.setText(f"▶ {self.title}")
    
    def set_expanded(self, expanded):
        """Set expanded state."""
        if self.is_expanded != expanded:
            self.toggle()