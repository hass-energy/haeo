"""Pytest test for Sigenergy guide.

This test runs the Sigenergy setup guide through Playwright browser automation,
validating that all configuration steps complete successfully and capturing
screenshots for documentation.

Run with:
    uv run pytest tests/guides/sigenergy/test_sigenergy_guide.py -m guide -v
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
import shutil
import sys
from collections.abc import Generator

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.guides.ha_runner import live_home_assistant
from tests.guides.sigenergy.run_guide import INPUTS_FILE, SCREENSHOTS_DIR, run_guide

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _restore_timezone() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    """Restore dt_util.DEFAULT_TIME_ZONE after test.

    The live HA instance sets the timezone to ZoneInfo('UTC') via
    async_set_time_zone(), but pytest-homeassistant-custom-component
    expects datetime.timezone.utc at teardown.
    """
    yield
    # Reset to datetime.UTC which is what the pytest plugin expects
    dt_util.set_default_time_zone(datetime.UTC)


@pytest.mark.guide
@pytest.mark.enable_socket
@pytest.mark.timeout(300)  # 5 minutes for full guide run
@pytest.mark.parametrize("dark_mode", [False, True], ids=["light", "dark"])
def test_sigenergy_guide(dark_mode: bool) -> None:
    """Test the complete Sigenergy setup guide.

    This test:
    1. Starts a fresh Home Assistant instance with pre-authenticated user
    2. Loads entity states from scenario1 inputs.json
    3. Runs through all guide steps using Playwright
    4. Captures screenshots at each step
    5. Validates that all elements were created successfully
    """
    # Use separate directories for light and dark mode screenshots
    mode_suffix = "dark" if dark_mode else "light"
    output_dir = SCREENSHOTS_DIR.parent / f"screenshots_{mode_suffix}"

    # Clean and create output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    with live_home_assistant(timeout=120) as hass:
        # Load entity states from scenario1
        hass.load_states_from_file(INPUTS_FILE)

        # Run the guide
        results = run_guide(hass, output_dir, headless=True, dark_mode=dark_mode)

        # Validate results
        assert len(results) > 0, "No screenshots captured"

        # Verify expected elements were created by checking config entries
        # Note: async_entries is synchronous despite its name (HA convention for callback methods)

        async def get_entries() -> list[ConfigEntry]:
            return hass.hass.config_entries.async_entries("haeo")

        config_entries = hass.run_coro(get_entries())
        assert len(config_entries) > 0, "No HAEO config entries created"

        # Check that we have the hub entry
        hub_entry = config_entries[0]
        assert hub_entry.title == "Sigenergy System"

        # Check subentries for elements
        subentries = list(hub_entry.subentries.values())
        element_names = {se.title for se in subentries}

        expected_elements = {
            "Switchboard",
            "Inverter",
            "Battery",
            "Solar",
            "Grid",
            "Constant Load",
        }
        assert expected_elements <= element_names, (
            f"Missing elements: {expected_elements - element_names}"
        )

        _LOGGER.info(
            "Guide test passed (%s mode): %d screenshots saved to %s",
            mode_suffix,
            len(results),
            output_dir,
        )
