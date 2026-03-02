"""Sigenergy system setup guide.

This guide walks through setting up a complete Sigenergy home battery system.
All configuration is inline - you can follow along step by step.

Run with:
    uv run python tests/guides/sigenergy/guide.py

Screenshots are automatically captured and named hierarchically based on
the function call stack, e.g. "add_battery.entity_Capacity.search_results"
"""

from __future__ import annotations

from collections import OrderedDict
import logging
from pathlib import Path
import shutil
import sys

from playwright.sync_api import sync_playwright

from tests.guides.ha_runner import LiveHomeAssistant, live_home_assistant
from tests.guides.primitives import (
    ConstantInput,
    EntityInput,
    HAPage,
    add_battery,
    add_grid,
    add_integration,
    add_inverter,
    add_load,
    add_solar,
    login,
    screenshot_context,
    verify_setup,
)

_LOGGER = logging.getLogger(__name__)

# Paths
GUIDE_DIR = Path(__file__).parent
PROJECT_ROOT = GUIDE_DIR.parent.parent.parent
INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"
SCREENSHOTS_DIR = GUIDE_DIR / "screenshots"


def run_guide(
    hass: LiveHomeAssistant,
    output_dir: Path,
    *,
    headless: bool = True,
    dark_mode: bool = False,
) -> OrderedDict[str, Path]:
    """Run the Sigenergy setup guide.

    Returns an OrderedDict of screenshot names to paths.
    """
    with sync_playwright() as p:
        browser = p.firefox.launch(
            headless=headless,
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        hass.inject_auth(context, dark_mode=dark_mode)
        page_obj = context.new_page()
        page_obj.set_default_timeout(5000)

        try:
            page = HAPage(page=page_obj, url=hass.url)

            with screenshot_context(output_dir) as ctx:
                # Step 1: Login
                login(page)

                # Step 2: Add HAEO integration with network name
                add_integration(
                    page,
                    network_name="Sigenergy System",
                )

                # Step 3: Add Inverter
                # The inverter connects the DC side (battery, solar) to AC (switchboard)
                add_inverter(
                    page,
                    name="Inverter",
                    connection="Switchboard",
                    max_power_source_target=EntityInput("max active power", "Sigen Plant Max Active Power"),
                    max_power_target_source=EntityInput("max active power", "Sigen Plant Max Active Power"),
                )

                # Step 4: Add Battery
                # A Sigenergy SigenStor battery with typical home storage capacity
                add_battery(
                    page,
                    name="Battery",
                    connection="Inverter",
                    capacity=EntityInput("rated energy", "Rated Energy Capacity"),
                    initial_charge_percentage=EntityInput("state of charge", "Battery State of Charge"),
                    max_power_target_source=EntityInput("rated charging", "Rated Charging Power"),
                    max_power_source_target=EntityInput("rated discharging", "Rated Discharging Power"),
                    min_charge_percentage=ConstantInput(10),
                    max_charge_percentage=ConstantInput(100),
                )

                # Step 5: Add Solar
                # Multiple solar arrays facing different directions
                add_solar(
                    page,
                    name="Solar",
                    connection="Inverter",
                    forecast=[
                        EntityInput("east solar today", "East solar production forecast"),
                        EntityInput("north solar today", "North solar production forecast"),
                        EntityInput("south solar today", "South solar prediction forecast"),
                        EntityInput("west solar today", "West solar production forecast"),
                    ],
                )

                # Step 6: Add Grid
                # Grid connection with Amber Electric pricing
                add_grid(
                    page,
                    name="Grid",
                    connection="Switchboard",
                    price_source_target=[
                        EntityInput("general price", "Home - General Price"),
                        EntityInput("general forecast", "Home - General Forecast"),
                    ],
                    price_target_source=[
                        EntityInput("feed in price", "Home - Feed In Price"),
                        EntityInput("feed in forecast", "Home - Feed In Forecast"),
                    ],
                    max_power_source_target=ConstantInput(55),
                    max_power_target_source=ConstantInput(30),
                )

                # Step 7: Add Load
                # Constant base load (things that are always on)
                add_load(
                    page,
                    name="Constant Load",
                    connection="Switchboard",
                    forecast=ConstantInput(1),
                )

                # Step 8: Verify setup
                verify_setup(page)

                return ctx.screenshots

        except Exception:
            _LOGGER.exception("Error running guide")
            error_path = output_dir / "error_state.png"
            page_obj.screenshot(path=str(error_path))
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

        screenshots = run_guide(hass, SCREENSHOTS_DIR, headless=headless)

        _LOGGER.info("=" * 50)
        _LOGGER.info("Guide complete! %d screenshots captured:", len(screenshots))
        for name in screenshots:
            _LOGGER.info("  %s", name)


if __name__ == "__main__":
    main()
