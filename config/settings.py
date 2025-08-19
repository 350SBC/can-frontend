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
MAX_PLOT_POINTS = 200  # Reduced further for ultra-fast rendering
PLOT_MINIMUM_HEIGHT = 900

# Table Configuration
MAX_BUFFER_SIZE = 50
TABLE_UPDATE_INTERVAL = 50  # milliseconds

# Performance Configuration
UI_UPDATE_RATE = 8   # milliseconds (~120 FPS for ultra-responsive gauges)
GAUGE_UPDATE_INTERVAL = 8   # milliseconds (~120 FPS for gauges)
PLOT_UPDATE_INTERVAL = 50   # milliseconds (~20 FPS for plots)
SIGNAL_UPDATE_THRESHOLD = 50  # minimum ms between signal updates (for plots)
ZMQ_POLL_INTERVAL = 5   # milliseconds for more aggressive ZMQ polling
MAX_MESSAGES_PER_CYCLE = 20  # increased message processing per cycle

# Gauge Responsiveness Settings
GAUGE_IMMEDIATE_THRESHOLD = 0.01  # 1% change triggers immediate repaint (more sensitive)
GAUGE_SKIP_THRESHOLD = 0.0001     # 0.01% change threshold to skip updates (more responsive)

# Gauge Visual Style
GAUGE_STYLE = "modern"  # Options: "round", "modern", "neon"
GAUGE_SWEEP_DIRECTION = "cw"  # "cw" for clockwise, "ccw" for counter-clockwise

# Layout configurations
LAYOUT_CONFIGS = {
    "grid_2x3": {
        "name": "Grid 2x3",
        "type": "grid",
        "rows": 2,
        "cols": 3,
        "spacing": 20,
        "gauge_sizes": {
            "Temperature": {"scale_factor": 0.5},
            "AFR": {"scale_factor": 0.5},
            "Battery Voltage": {"scale_factor": 0.5},
            "Oil Pressure": {"scale_factor": 0.5}
        }
    },
    "grid_3x2": {
        "name": "Grid 3x2", 
        "type": "grid",
        "rows": 3,
        "cols": 2,
        "spacing": 20,
        "gauge_sizes": {
            "Temperature": {"scale_factor": 0.5},
            "AFR": {"scale_factor": 0.5},
            "Battery Voltage": {"scale_factor": 0.5},
            "Oil Pressure": {"scale_factor": 0.5}
        }
    },
    "single_row": {
        "name": "Single Row",
        "type": "grid",
        "rows": 1,
        "cols": 6,
        "spacing": 5,
        "gauge_sizes": {
            "Temperature": {"scale_factor": 0.5},
            "AFR": {"scale_factor": 0.5},
            "Battery Voltage": {"scale_factor": 0.5},
            "Oil Pressure": {"scale_factor": 0.5}
        }
    },
    "compact_2x3": {
        "name": "Compact 2x3",
        "type": "grid", 
        "rows": 2,
        "cols": 3,
        "spacing": 5,
        "gauge_sizes": {
            "Temperature": {"scale_factor": 0.5},
            "AFR": {"scale_factor": 0.5},
            "Battery Voltage": {"scale_factor": 0.5},
            "Oil Pressure": {"scale_factor": 0.5}
        }
    },
    "focus_primary": {
        "name": "Focus Primary",
        "type": "custom",
        "primary_gauges": ["RPM", "Speed"],
        "secondary_gauges": ["Temperature", "AFR", "Battery Voltage", "Oil Pressure"]
    },
    "large_rpm_speed": {
        "name": "Large RPM/Speed",
        "type": "grid",
        "rows": 2,
        "cols": 3,
        "spacing": 15,
        "gauge_sizes": {
            "RPM": {"scale_factor": 1.4},  # 40% larger than default
            "Speed": {"scale_factor": 1.4},
            "Temperature": {"scale_factor": 0.5},  # 1/2 size
            "AFR": {"scale_factor": 0.5},  # 1/2 size
            "Battery Voltage": {"scale_factor": 0.5},  # 1/2 size
            "Oil Pressure": {"scale_factor": 0.5}  # 1/2 size
        }
    },
    "small_secondary": {
        "name": "Small Secondary",
        "type": "grid", 
        "rows": 2,
        "cols": 3,
        "spacing": 10,
        "gauge_sizes": {
            "RPM": {"scale_factor": 1.2},  # 20% larger
            "Speed": {"scale_factor": 1.2},
            "Temperature": {"scale_factor": 0.5},  # 1/2 size
            "AFR": {"scale_factor": 0.5},  # 1/2 size
            "Battery Voltage": {"scale_factor": 0.5},  # 1/2 size
            "Oil Pressure": {"scale_factor": 0.5}  # 1/2 size
        }
    },
    "proportional_2x3": {
        "name": "Proportional 2x3",
        "type": "grid",
        "rows": 2,
        "cols": 3,
        "spacing": 20,
        "use_proportional_sizing": True,
        "gauge_proportions": {
            "RPM": {"width_percent": 30, "height_percent": 45},  # Takes 30% width, 45% height of available space
            "Speed": {"width_percent": 30, "height_percent": 45},
            "Temperature": {"width_percent": 20, "height_percent": 25},  # Half size proportionally
            "AFR": {"width_percent": 20, "height_percent": 25},  # Half size proportionally
            "Battery Voltage": {"width_percent": 20, "height_percent": 25},  # Half size proportionally
            "Oil Pressure": {"width_percent": 20, "height_percent": 25}  # Half size proportionally
        }
    }
}

# Default layout
DEFAULT_LAYOUT = "grid_2x3"

# Auto-connection Configuration
AUTO_DBC_PATH = "dbc/test.dbc"
AUTO_INTERFACE = "socketcan"
AUTO_CHANNEL = "vcan0"
AUTO_BITRATE = 500000

# Gauge Configuration
RPM_GAUGE_MIN = 0
RPM_GAUGE_MAX = 8000
RPM_SIGNAL_NAMES = ['rpm', 'engine_rpm', 'engine_speed', 'enginespeed']