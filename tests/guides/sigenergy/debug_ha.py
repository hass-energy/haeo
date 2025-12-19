#!/usr/bin/env python3
"""Debug script to start Home Assistant and keep it running for browser inspection."""

from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.guides.ha_runner import live_home_assistant

INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"

print("Starting Home Assistant...")

with live_home_assistant(timeout=60) as hass:
    print(f"✅ Home Assistant running at {hass.url}")
    print(f"   Access token: {hass.access_token[:20]}...")

    # Load entity states
    hass.load_states_from_file(INPUTS_FILE)
    print(f"   Loaded states from {INPUTS_FILE.name}")

    print("\nPress Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
