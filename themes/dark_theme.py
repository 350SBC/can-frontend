# themes/dark_theme.py
"""Dark theme stylesheet for the CAN dashboard."""

DARK_THEME = """
    QMainWindow {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QWidget {
        background-color: #1e1e1e;
        color: #ffffff;
        selection-background-color: #3399ff;
    }
    QLabel {
        color: #ffffff;
        background-color: transparent;
    }
    QLineEdit {
        background-color: #2d2d30;
        border: 1px solid #3f3f46;
        color: #ffffff;
        padding: 6px;
        border-radius: 4px;
        font-size: 11px;
    }
    QLineEdit:focus {
        border: 2px solid #007acc;
        background-color: #1e1e1e;
    }
    QPushButton {
        background-color: #0e639c;
        color: #ffffff;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: #1177bb;
    }
    QPushButton:pressed {
        background-color: #005a9e;
    }
    QPushButton:disabled {
        background-color: #3c3c3c;
        color: #888888;
    }
    QStatusBar {
        background-color: #007acc;
        color: #ffffff;
        border: none;
        font-weight: bold;
    }
    QFormLayout QLabel {
        color: #cccccc;
        font-weight: normal;
    }
    QMessageBox {
        background-color: #2d2d30;
        color: #ffffff;
    }
    QMessageBox QPushButton {
        min-width: 80px;
        background-color: #0e639c;
    }
    QMessageBox QPushButton:hover {
        background-color: #1177bb;
    }
    /* Scrollbars */
    QScrollBar:vertical {
        background-color: #2b2b2b;
        width: 12px;
        border: none;
    }
    QScrollBar::handle:vertical {
        background-color: #555555;
        border-radius: 6px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #666666;
    }
    QScrollBar:horizontal {
        background-color: #2b2b2b;
        height: 12px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background-color: #555555;
        border-radius: 6px;
        min-width: 20px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #666666;
    }
    /* Gauge styling for dark theme */
    RoundGauge {
        background-color: transparent;
    }
    /* Collapsible widget styling */
    QPushButton[checkable="true"] {
        text-align: left;
        padding: 10px;
        background-color: #4a4a4a;
        color: white;
        border: none;
        font-weight: bold;
        font-size: 12px;
    }
    QPushButton[checkable="true"]:hover {
        background-color: #5a5a5a;
    }
    QPushButton[checkable="true"]:pressed {
        background-color: #3a3a3a;
    }
"""