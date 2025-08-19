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
    }
    QLineEdit:focus {
        border: 2px solid #007acc;
    }
    QPushButton {
        background-color: #0e639c;
        color: #ffffff;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #1177bb;
    }
    QPushButton:pressed {
        background-color: #005a9e;
    }
    QStatusBar {
        background-color: #007acc;
        color: #ffffff;
        border: none;
    }
"""