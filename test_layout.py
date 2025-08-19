#!/usr/bin/env python3
"""Test script to verify gauge layout configuration without GUI."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our gauge configuration
from gui.main_window import MainWindow

def test_gauge_layout():
    """Test the gauge configuration and layout setup."""
    print("Testing gauge layout configuration...")
    
    # Create a dummy main window to access gauge configs
    window = MainWindow()
    
    print(f"Total configured gauges: {len(window.gauge_configs)}")
    print("\nGauge Layout (2x3 grid):")
    print("┌─────────────┬─────────────┬─────────────┐")
    
    for i, config in enumerate(window.gauge_configs):
        row = i // 3
        col = i % 3
        
        if col == 0:
            print(f"│ {config.title:11s} ", end="")
        elif col == 1:
            print(f"│ {config.title:11s} ", end="")
        else:
            print(f"│ {config.title:11s} │")
            if row == 0:
                print("├─────────────┼─────────────┼─────────────┤")
    
    print("└─────────────┴─────────────┴─────────────┘")
    
    print("\nGauge Details:")
    for i, config in enumerate(window.gauge_configs):
        row = i // 3
        col = i % 3
        print(f"  Position ({row},{col}): {config.title} ({config.min_value}-{config.max_value} {config.unit})")
        print(f"    Signals: {', '.join(config.signal_names)}")
    
    print("\nLayout test completed successfully!")

if __name__ == "__main__":
    test_gauge_layout()
