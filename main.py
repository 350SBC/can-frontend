# main.py
"""Main entry point for the CAN frontend application."""

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import CANDashboardMainWindow


def main():
    """Main function to start the application."""
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = CANDashboardMainWindow()
    window.show()
    
    # Start the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()