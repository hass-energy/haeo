"""Sigenergy system setup guide using primitives.

This module defines the Sigenergy-specific configuration and runs the guide
using the primitives package.

Run with:
    uv run python tests/guides/sigenergy/guide.py

The script:
    - Runs an in-process Home Assistant instance
    - Loads entity states from scenario1 inputs.json
    - Walks through HAEO configuration for a Sigenergy system
    - Captures screenshots at each step
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import sys
from typing import Any

from playwright.sync_api import sync_playwright

from tests.guides.ha_runner import LiveHomeAssistant, live_home_assistant
from tests.guides.primitives import HAPage

_LOGGER = logging.getLogger(__name__)

# Configuration paths
GUIDE_DIR = Path(__file__).parent
PROJECT_ROOT = GUIDE_DIR.parent.parent.parent
INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"
SCREENSHOTS_DIR = GUIDE_DIR / "screenshots"

# Network name for the HAEO integration
NETWORK_NAME = "Sigenergy System"

# UI timeout
DEFAULT_TIMEOUT = 5000


def run_guide(
    hass: LiveHomeAssistant,
    output_dir: Path,
    *,
    headless: bool = True,
    dark_mode: bool = False,
    pause_mode: bool = False,
) -> list[dict[str, Any]]:
    """Run the complete Sigenergy guide.

    This uses HAPage primitives for HA UI interactions while keeping
    Sigenergy-specific knowledge (entity names, search terms) in this module.

    Args:
        hass: LiveHomeAssistant instance
        output_dir: Directory to save screenshots
        headless: Whether to run browser headlessly
        dark_mode: Whether to use dark theme
        pause_mode: Whether to pause after each step

    Returns:
        List of captured screenshot results

    """
    if pause_mode:
        _LOGGER.info("PAUSE MODE ENABLED - will pause after each step")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--remote-debugging-port=9222"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        hass.inject_auth(context, dark_mode=dark_mode)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            ha = HAPage(
                page=page,
                url=hass.url,
                output_dir=output_dir,
            )

            # Login
            _login(ha)

            # Add HAEO integration
            _add_haeo_integration(ha)

            # Add elements
            _add_inverter(ha)
            _add_battery(ha)
            _add_solar(ha)
            _add_grid(ha)
            _add_load(ha)

            # Final verification
            _verify_setup(ha)

            return ha.results

        except Exception:
            _LOGGER.exception("Error running guide")
            error_path = output_dir / "error_state.png"
            page.screenshot(path=str(error_path))
            _LOGGER.info("Error screenshot: %s", error_path)
            raise

        finally:
            page.close()
            context.close()
            browser.close()


def _login(ha: HAPage) -> None:
    """Log in to Home Assistant."""
    _LOGGER.info("Logging in...")
    ha.goto("/")

    if "/auth/authorize" in ha.page.url:
        ha.fill_textbox("Username", "testuser")
        ha.fill_textbox("Password", "testpass")
        ha.click_button("Log in")
        ha.page.wait_for_url("**/lovelace/**", timeout=DEFAULT_TIMEOUT * 2)

    _LOGGER.info("Logged in")


def _add_haeo_integration(ha: HAPage) -> None:
    """Add HAEO integration."""
    _LOGGER.info("Adding HAEO integration...")

    ha.goto("/config/integrations")
    ha.click_add_integration(capture=True)
    ha.search_integration("HAEO", capture=True)

    ha.wait_for_dialog("HAEO Setup")
    ha.capture("network_form")

    ha.fill_textbox("System Name", NETWORK_NAME, capture=True)
    ha.submit(capture=True)
    ha.wait_for_load()

    ha.goto("/config/integrations/integration/haeo")
    ha.capture("haeo_integration_page")

    _LOGGER.info("HAEO integration added")


def _add_inverter(ha: HAPage) -> None:
    """Add Inverter element."""
    _LOGGER.info("Adding Inverter...")

    ha.click_button("Inverter", capture=True)
    ha.wait_for_dialog("Inverter Configuration")

    ha.fill_textbox("Inverter Name", "Inverter", capture=True)
    ha.select_combobox("AC Connection", "Switchboard", capture=True)

    # Entity selections with Sigenergy-specific names
    ha.select_entity(
        "Max DC to AC Power",
        "max active power",
        "Sigen Plant Max Active Power",
        capture=True,
    )
    ha.select_entity(
        "Max AC to DC Power",
        "max active power",
        "Sigen Plant Max Active Power",
        capture=True,
    )

    ha.submit(capture=True)
    ha.close_element_dialog(capture=True)

    _LOGGER.info("Inverter added")


def _add_battery(ha: HAPage) -> None:
    """Add Battery element."""
    _LOGGER.info("Adding Battery...")

    ha.click_button("Battery", capture=True)
    ha.wait_for_dialog("Battery Configuration")

    ha.fill_textbox("Battery Name", "Battery", capture=True)
    ha.select_combobox("Connection", "Inverter", capture=True)

    ha.select_entity("Capacity", "rated energy", "Rated Energy Capacity", capture=True)
    ha.select_entity("State of Charge", "state of charge", "Battery State of Charge", capture=True)
    ha.select_entity("Max Charging Power", "rated charging", "Rated Charging Power", capture=True)
    ha.select_entity(
        "Max Discharging Power",
        "rated discharging",
        "Rated Discharging Power",
        capture=True,
    )

    ha.submit(capture=True)

    # Check for step 2 (min/max charge levels)
    submit = ha.page.get_by_role("button", name="Submit")
    if submit.count() > 0 and submit.is_visible(timeout=1000):
        _try_fill_spinbutton(ha, "Min Charge Level", "10")
        _try_fill_spinbutton(ha, "Max Charge Level", "100")
        ha.submit(capture=True)

    ha.close_element_dialog(capture=True)

    _LOGGER.info("Battery added")


def _add_solar(ha: HAPage) -> None:
    """Add Solar element with multiple forecast sensors."""
    _LOGGER.info("Adding Solar...")

    ha.click_button("Solar", capture=True)
    ha.wait_for_dialog("Solar Configuration")

    ha.fill_textbox("Solar Name", "Solar", capture=True)
    ha.select_combobox("Connection", "Inverter", capture=True)

    # Multiple forecast sensors for different solar arrays
    ha.select_entity(
        "Forecast",
        "east solar today",
        "East solar production forecast",
        capture=True,
    )
    ha.add_another_entity(
        "Forecast",
        "north solar today",
        "North solar production forecast",
        capture=True,
    )
    ha.add_another_entity(
        "Forecast",
        "south solar today",
        "South solar prediction forecast",
        capture=True,
    )
    ha.add_another_entity(
        "Forecast",
        "west solar today",
        "West solar production forecast",
        capture=True,
    )

    ha.submit(capture=True)
    ha.close_element_dialog(capture=True)

    _LOGGER.info("Solar added")


def _add_grid(ha: HAPage) -> None:
    """Add Grid element."""
    _LOGGER.info("Adding Grid...")

    ha.click_button("Grid", capture=True)
    ha.wait_for_dialog("Grid Configuration")

    ha.fill_textbox("Grid Name", "Grid", capture=True)
    ha.select_combobox("Connection", "Switchboard", capture=True)

    # Import/export price sensors
    ha.select_entity("Import Price", "general price", "Home - General Price", capture=True)
    ha.add_another_entity("Import Price", "general forecast", "Home - General Forecast", capture=True)

    ha.select_entity("Export Price", "feed in price", "Home - Feed In Price", capture=True)
    ha.add_another_entity("Export Price", "feed in forecast", "Home - Feed In Forecast", capture=True)

    ha.submit(capture=True)

    # Step 2: Grid limits
    ha.page.get_by_role("spinbutton", name="Import Limit").wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
    ha.fill_spinbutton("Import Limit", "55", capture=True)
    ha.fill_spinbutton("Export Limit", "30", capture=True)

    ha.submit(capture=True)
    ha.close_element_dialog(capture=True)

    _LOGGER.info("Grid added")


def _add_load(ha: HAPage) -> None:
    """Add Load element (constant load using configurable entity)."""
    _LOGGER.info("Adding Load...")

    ha.click_button("Load", capture=True)
    ha.wait_for_dialog("Load Configuration")

    ha.fill_textbox("Load Name", "Constant Load", capture=True)
    ha.select_combobox("Connection", "Switchboard", capture=True)

    # Use HAEO Configurable entity for constant load
    ha.select_entity("Forecast", "configurable", "Configurable Entity", capture=True)

    ha.submit(capture=True)

    # Step 2: Enter constant load value
    ha.page.get_by_role("spinbutton", name="Forecast").wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
    ha.fill_spinbutton("Forecast", "1", capture=True)

    ha.submit(capture=True)
    ha.close_element_dialog(capture=True)

    _LOGGER.info("Load added")


def _verify_setup(ha: HAPage) -> None:
    """Verify the complete setup."""
    _LOGGER.info("Verifying setup...")

    ha.goto("/config/integrations/integration/haeo")
    ha.page.get_by_role("button", name="Inverter").first.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
    ha.capture("final_overview")

    _LOGGER.info("Setup verified")


def _try_fill_spinbutton(ha: HAPage, name: str, value: str) -> None:
    """Try to fill a spinbutton if it exists and is visible."""
    spinbutton = ha.page.get_by_role("spinbutton", name=name)
    if spinbutton.count() > 0:
        try:
            if spinbutton.is_visible(timeout=1000):
                ha.fill_spinbutton(name, value, capture=True)
        except Exception:
            pass


def main() -> None:
    """Run the complete Sigenergy guide as a standalone script."""
    pause_mode = "--pause" in sys.argv
    headless = not pause_mode

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    _LOGGER.info("Sigenergy System Setup Guide")
    _LOGGER.info("=" * 50)
    _LOGGER.info("Output directory: %s", SCREENSHOTS_DIR)
    if pause_mode:
        _LOGGER.info("PAUSE MODE: Browser will be visible, pauses enabled")

    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(parents=True)

    with live_home_assistant(timeout=120) as hass:
        _LOGGER.info("Home Assistant running at %s", hass.url)

        _LOGGER.info("Loading entity states...")
        hass.load_states_from_file(INPUTS_FILE)
        _LOGGER.info("Loaded states from %s", INPUTS_FILE.name)

        results = run_guide(hass, SCREENSHOTS_DIR, headless=headless, pause_mode=pause_mode)

        _LOGGER.info("=" * 50)
        _LOGGER.info("Guide complete! %d screenshots captured", len(results))
        _LOGGER.info("Screenshots saved to: %s", SCREENSHOTS_DIR)


if __name__ == "__main__":
    main()
