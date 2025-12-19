#!/usr/bin/env python3
"""Test script for in-process Home Assistant runner.

Run with: uv run python tests/guides/test_ha_runner.py
"""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.guides.ha_runner import live_home_assistant


def test_basic_startup() -> None:
    """Test that HA starts and is reachable."""
    print("🚀 Testing in-process Home Assistant startup...")

    with live_home_assistant(timeout=60) as hass:
        print(f"✅ Home Assistant started at {hass.url}")
        print(f"   Port: {hass.port}")

        # Try to reach the server
        import urllib.request
        from urllib.error import URLError

        try:
            with urllib.request.urlopen(hass.url, timeout=5) as response:
                print(f"   HTTP response: {response.status}")
        except URLError as e:
            print(f"   HTTP error (expected without auth): {e}")

        # Set some test states
        print("\n📝 Setting entity states...")
        hass.set_states(
            [
                {
                    "entity_id": "sensor.test_power",
                    "state": "1500",
                    "attributes": {
                        "unit_of_measurement": "W",
                        "friendly_name": "Test Power",
                        "device_class": "power",
                    },
                },
                {
                    "entity_id": "sensor.test_energy",
                    "state": "42.5",
                    "attributes": {
                        "unit_of_measurement": "kWh",
                        "friendly_name": "Test Energy",
                        "device_class": "energy",
                    },
                },
            ]
        )

        # Verify states were set
        async def check_states():
            state1 = hass.hass.states.get("sensor.test_power")
            state2 = hass.hass.states.get("sensor.test_energy")
            return state1, state2

        state1, state2 = hass.run_coro(check_states())
        print(f"   sensor.test_power: {state1.state if state1 else 'NOT FOUND'}")
        print(f"   sensor.test_energy: {state2.state if state2 else 'NOT FOUND'}")

        if state1 and state1.state == "1500" and state2 and state2.state == "42.5":
            print("\n✅ States verified correctly!")
        else:
            print("\n❌ State verification failed!")
            return False

    print("\n🛑 Home Assistant stopped cleanly")
    return True


def test_with_playwright() -> None:
    """Test browser automation with Playwright."""
    print("\n🎭 Testing Playwright integration...")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("   ⚠️ Playwright not installed, skipping browser test")
        return True

    with live_home_assistant(timeout=60) as hass:
        print(f"   HA running at {hass.url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(hass.url, timeout=10000)
                title = page.title()
                print(f"   Page title: {title}")

                if "Home Assistant" in title:
                    print("   ✅ Playwright can connect to HA!")
                else:
                    print(f"   ⚠️ Unexpected title: {title}")

            finally:
                page.close()
                browser.close()

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Home Assistant In-Process Runner Tests")
    print("=" * 60)

    success = True

    try:
        if not test_basic_startup():
            success = False
    except Exception as e:
        print(f"\n❌ Basic startup test failed: {e}")
        import traceback

        traceback.print_exc()
        success = False

    try:
        if not test_with_playwright():
            success = False
    except Exception as e:
        print(f"\n❌ Playwright test failed: {e}")
        import traceback

        traceback.print_exc()
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
