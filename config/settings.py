# config/settings.py
"""Configuration settings for the CAN frontend application."""

# ZeroMQ Configuration
BACKEND_IP = "pi4"
PUB_PORT = "5556"
REQ_REP_PORT = "5557"

# UI Configuration
WINDOW_GEOMETRY = (0, 5, 1024, 768)
WINDOW_TITLE = "CAN Dashboard Frontend"

# (Legacy table configuration removed: MAX_BUFFER_SIZE, TABLE_UPDATE_INTERVAL were unused)

# Performance Configuration
UI_UPDATE_RATE = 10   # milliseconds (~120 FPS for ultra-responsive gauges)
GAUGE_UPDATE_INTERVAL = 10   # milliseconds (~120 FPS for gauges)
ZMQ_POLL_INTERVAL = 10   # milliseconds for more aggressive ZMQ polling
MAX_MESSAGES_PER_CYCLE = 200  # increased message processing per cycle
REALTIME_GAUGE_UPDATES = False  # If True, apply gauge updates immediately on signal arrival (no buffering)
FAST_FORWARD_SIGNAL_UPDATES = True  # If True, compress backlog: keep only latest value per signal each poll
ZMQ_SUB_RCVHWM = 50  # High-water mark (queue size) for SUB socket; lowers backlog size
ZMQ_SUB_CONFLATE = False  # If True, keep only last message (may drop intermediate data)
BACKLOG_STRATEGY = "collapse_latest"  # Options: "normal", "collapse_latest" (drain queue each poll and keep only latest per signal)
MAX_DRAIN_PER_POLL = 1000  # Safety cap when collapsing backlog
MERGE_SIGNALS_DURING_COLLAPSE = True  # Merge values from all drained messages so last value per signal is kept

# Gauge Responsiveness Settings
GAUGE_IMMEDIATE_THRESHOLD = 0.50  # 1% change triggers immediate repaint (more sensitive)
GAUGE_SKIP_THRESHOLD = 0.0001     # 0.01% change threshold to skip updates (more responsive)

# Gauge Visual Style
GAUGE_STYLE = "modern"  # Options: "round", "modern", "neon"
GAUGE_SWEEP_DIRECTION = "cw"  # "cw" for clockwise, "ccw" for counter-clockwise

# Signal Filtering (optional)
# If DISPLAY_SIGNAL_WHITELIST is non-empty, only signals whose lowercase name appears here
# will be allowed to update gauges. Example:
# DISPLAY_SIGNAL_WHITELIST = ['rpm', 'speed', 'temperature']
DISPLAY_SIGNAL_WHITELIST = []  # Leave empty to allow all signals mapped to gauges
DISPLAY_SIGNAL_BLACKLIST = []  # Any lowercase signal names here will always be ignored

# Per-signal rate limits (seconds between accepted updates). Example: {'rpm': 0.05} for max 20 Hz
SIGNAL_RATE_LIMITS = {}

# Hard cap: process at most this many signal updates from a single decoded message (0 = no cap)
MAX_SIGNALS_PER_MESSAGE = 0

# Layout configurations
LAYOUT_CONFIGS = {
    "gauges_video_center": {
        "name": "Gauges Left/Right, Video Center",
        "type": "gauges_video_center",
        "num_cameras": 2,
        "camera_indices": [0, 3],
    "gauge_left": ["RPM", "Speed", "Temperature"],
    "gauge_right": ["AFR", "Battery Voltage", "Oil Pressure"],
        "spacing": 0,
        "gauge_sizes": {
            "RPM": {"scale_factor": 0.5},
            "Speed": {"scale_factor": 0.5},
            "Temperature": {"scale_factor": 0.5},
            "AFR": {"scale_factor": 0.5},
            "Battery Voltage": {"scale_factor": 0.5},
            "Oil Pressure": {"scale_factor": 0.5}
        }
    
    },
    "video_grid": {
        "name": "Video Grid",
        "type": "video_grid",
        "num_cameras": 2,  # Default, can be changed dynamically
        "camera_indices": [0, 2],
        "spacing": 10
    },
    "grid_2x3": {
        "name": "Grid 2x3",
        "type": "grid",
        "rows": 2,
        "cols": 3,
        "spacing": 20,
        "gauge_sizes": {
           # "Temperature": {"scale_factor": 0.5},
            # "AFR": {"scale_factor": 0.5},
            # "Battery Voltage": {"scale_factor": 0.5},
            # "Oil Pressure": {"scale_factor": 0.5}
        }
    },
    "grid_3x2": {
        "name": "Grid 3x2", 
        "type": "grid",
        "rows": 3,
        "cols": 2,
        "spacing": 20,
        "gauge_sizes": {
            # "Temperature": {"scale_factor": 0.5},
            # "AFR": {"scale_factor": 0.5},
            # "Battery Voltage": {"scale_factor": 0.5},
            # "Oil Pressure": {"scale_factor": 0.5}
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
    },
    "rpm_speed_focus": {
        "name": "RPM/Speed Focus",
        "type": "custom_grid",
        "spacing": 15,
        "top_large": ["Engine RPM", "Speed"],  # Two large gauges on top row, centered
        "side_small": ["Temperature", "AFR"],  # Small gauges on left and right of large ones
        "bottom_row": ["Battery Voltage", "Oil Pressure", "Timing", "Pedal Position", "MAP", "Closed Loop" ],  # Rest below including indicator and displays
        "gauge_sizes": {
            "Engine RPM": {"scale_factor": 1.6},  # Large top gauges
            "Speed": {"scale_factor": 1.6},
            "Temperature": {"scale_factor": 0.6},  # Small side gauges
            "AFR": {"scale_factor": 0.6},
            "Battery Voltage": {"scale_factor": 0.8},  # Medium bottom row
            "Oil Pressure": {"scale_factor": 0.8},
            "Timing": {"scale_factor": 0.8},
            "Pedal Position": {"scale_factor": 0.8},
            "MAP": {"scale_factor": 0.8},
            "Closed Loop": {"scale_factor": 0.6},  # Indicator light - smaller than gauges
          
        }
    }
}

# Default layout
DEFAULT_LAYOUT = "rpm_speed_focus"

# Auto-connection Configuration
AUTO_DBC_PATH = "dbc/test.dbc"
AUTO_INTERFACE = "socketcan"
AUTO_CHANNEL = "can0"
AUTO_BITRATE = 500000

# (Legacy RPM gauge range & signal aliases removed: RPM_GAUGE_MIN, RPM_GAUGE_MAX, RPM_SIGNAL_NAMES were unusede
