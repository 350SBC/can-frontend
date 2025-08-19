# config/settings.py
"""Configuration settings for the CAN frontend application."""

# ZeroMQ Configuration
BACKEND_IP = "pi4"
PUB_PORT = "5556"
REQ_REP_PORT = "5557"

# UI Configuration
WINDOW_GEOMETRY = (0, 10, 1024, 768)
WINDOW_TITLE = "CAN Dashboard Frontend"

# Plotting Configuration
MAX_PLOTS_PER_ROW = 3
MAX_PLOT_ROWS = 3
MAX_PLOT_POINTS = 500
PLOT_MINIMUM_HEIGHT = 900

# Table Configuration
MAX_BUFFER_SIZE = 50
TABLE_UPDATE_INTERVAL = 50  # milliseconds

# Auto-connection Configuration
AUTO_DBC_PATH = "dbc/test.dbc"
AUTO_INTERFACE = "socketcan"
AUTO_CHANNEL = "vcan0"
AUTO_BITRATE = 500000

# Gauge Configuration
RPM_GAUGE_MIN = 0
RPM_GAUGE_MAX = 8000
RPM_SIGNAL_NAMES = ['rpm', 'engine_rpm', 'engine_speed', 'enginespeed']