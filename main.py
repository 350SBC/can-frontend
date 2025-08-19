# main.py
"""Main entry point for the CAN frontend application."""

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import CANDashboardMainWindow
from themes.dark_theme import DARK_THEME


def main():
    """Main function to start the application."""
    app = QApplication(sys.argv)
    
    # Apply dark theme
    app.setStyleSheet(DARK_THEME)
    
    # Create and show the main window
    window = CANDashboardMainWindow()
    window.show()
    
    # Start the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()