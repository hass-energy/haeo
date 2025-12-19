"""Pytest test for Sigenergy guide.

This test runs the Sigenergy setup guide through Playwright browser automation,
validating that all configuration steps complete successfully and capturing
screenshots for documentation.

Run with:
    uv run pytest tests/guides/sigenergy/test_sigenergy_guide.py -m guide -v
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

# Add project root to path for imports
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.guides.ha_runner import live_home_assistant
from tests.guides.sigenergy.run_guide import (
    INPUTS_FILE,
    SCREENSHOTS_DIR,
    run_guide,
)


@pytest.mark.guide
def test_sigenergy_guide() -> None:
    """Test the complete Sigenergy setup guide.

    This test:
    1. Starts a fresh Home Assistant instance with pre-authenticated user
    2. Loads entity states from scenario1 inputs.json
    3. Runs through all guide steps using Playwright
    4. Captures screenshots at each step
    5. Validates that all elements were created successfully
    """
    # Clean and create output directory
    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(parents=True)

    with live_home_assistant(timeout=60) as hass:
        # Load entity states from scenario1
        hass.load_states_from_file(INPUTS_FILE)

        # Run the guide
        results = run_guide(hass, SCREENSHOTS_DIR, headless=True)

        # Validate results
        assert len(results) > 0, "No screenshots captured"

        # Verify expected elements were created by checking config entries
        config_entries = hass.run_coro(hass.hass.config_entries.async_entries("haeo"))
        assert len(config_entries) > 0, "No HAEO config entries created"

        # Check that we have the hub entry
        hub_entry = config_entries[0]
        assert hub_entry.title == "Sigenergy System"

        # Check subentries for elements
        subentries = list(hub_entry.subentries.values())
        element_names = {se.title for se in subentries}

        expected_elements = {"Switchboard", "Inverter", "Battery", "Solar", "Grid", "Constant Load"}
        assert expected_elements <= element_names, f"Missing elements: {expected_elements - element_names}"

        print(f"\n✅ Guide test passed! {len(results)} screenshots captured")
        print(f"📁 Screenshots saved to: {SCREENSHOTS_DIR}")
