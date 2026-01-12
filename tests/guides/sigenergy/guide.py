"""Sigenergy system setup guide.

This module defines the Sigenergy-specific configuration data and runs
the guide using the primitives package.

Run with:
    uv run python tests/guides/sigenergy/guide.py
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import sys
from typing import Any

from playwright.sync_api import sync_playwright

from tests.guides.ha_runner import LiveHomeAssistant, live_home_assistant
from tests.guides.primitives import (
    BatteryConfig,
    GridConfig,
    HAPage,
    InverterConfig,
    LoadConfig,
    SolarConfig,
    add_battery,
    add_grid,
    add_integration,
    add_inverter,
    add_load,
    add_solar,
    login,
    verify_setup,
)
from tests.guides.primitives.context import GuideContext

_LOGGER = logging.getLogger(__name__)

# Configuration paths
GUIDE_DIR = Path(__file__).parent
PROJECT_ROOT = GUIDE_DIR.parent.parent.parent
INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"
SCREENSHOTS_DIR = GUIDE_DIR / "screenshots"

# Network name
NETWORK_NAME = "Sigenergy System"

# Sigenergy-specific element configurations
# Entity tuples are (search_term, display_name)

INVERTER = InverterConfig(
    name="Inverter",
    connection="Switchboard",
    max_power_dc_to_ac=("max active power", "Sigen Plant Max Active Power"),
    max_power_ac_to_dc=("max active power", "Sigen Plant Max Active Power"),
)

BATTERY = BatteryConfig(
    name="Battery",
    connection="Inverter",
    capacity=("rated energy", "Rated Energy Capacity"),
    initial_soc=("state of charge", "Battery State of Charge"),
    max_charge_power=("rated charging", "Rated Charging Power"),
    max_discharge_power=("rated discharging", "Rated Discharging Power"),
    min_charge_level=10,
    max_charge_level=100,
)

SOLAR = SolarConfig(
    name="Solar",
    connection="Inverter",
    forecasts=[
        ("east solar today", "East solar production forecast"),
        ("north solar today", "North solar production forecast"),
        ("south solar today", "South solar prediction forecast"),
        ("west solar today", "West solar production forecast"),
    ],
)

GRID = GridConfig(
    name="Grid",
    connection="Switchboard",
    import_prices=[
        ("general price", "Home - General Price"),
        ("general forecast", "Home - General Forecast"),
    ],
    export_prices=[
        ("feed in price", "Home - Feed In Price"),
        ("feed in forecast", "Home - Feed In Forecast"),
    ],
    import_limit=55,
    export_limit=30,
)

LOAD = LoadConfig(
    name="Constant Load",
    connection="Switchboard",
    forecast=("configurable", "Configurable Entity"),
    constant_value=1,
)


def run_guide(
    hass: LiveHomeAssistant,
    output_dir: Path,
    *,
    headless: bool = True,
    dark_mode: bool = False,
    pause_mode: bool = False,
) -> list[dict[str, Any]]:
    """Run the Sigenergy setup guide."""
    if pause_mode:
        _LOGGER.info("PAUSE MODE ENABLED")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--remote-debugging-port=9222"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        hass.inject_auth(context, dark_mode=dark_mode)
        page = context.new_page()
        page.set_default_timeout(5000)

        try:
            ha_page = HAPage(page=page, url=hass.url, output_dir=output_dir)
            ctx = GuideContext(page=ha_page, output_dir=output_dir, config={})

            # Run guide steps
            login(ctx)
            add_integration(ctx, NETWORK_NAME)
            add_inverter(ctx, INVERTER)
            add_battery(ctx, BATTERY)
            add_solar(ctx, SOLAR)
            add_grid(ctx, GRID)
            add_load(ctx, LOAD)
            verify_setup(ctx)

            return ha_page.results

        except Exception:
            _LOGGER.exception("Error running guide")
            error_path = output_dir / "error_state.png"
            page.screenshot(path=str(error_path))
            raise

        finally:
            browser.close()


def main() -> None:
    """Run the guide as a standalone script."""
    pause_mode = "--pause" in sys.argv
    headless = not pause_mode

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    _LOGGER.info("Sigenergy System Setup Guide")
    _LOGGER.info("=" * 50)

    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(parents=True)

    with live_home_assistant(timeout=120) as hass:
        _LOGGER.info("Home Assistant running at %s", hass.url)
        hass.load_states_from_file(INPUTS_FILE)

        results = run_guide(hass, SCREENSHOTS_DIR, headless=headless, pause_mode=pause_mode)

        _LOGGER.info("=" * 50)
        _LOGGER.info("Guide complete! %d screenshots captured", len(results))


if __name__ == "__main__":
    main()
