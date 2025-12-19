"""Sigenergy system setup guide with screenshot capture.

This script walks through the complete Sigenergy system setup from the
user guide example, capturing PNG screenshots at each step.

Run with:
    uv run python tests/guides/sigenergy/run_guide.py

The script uses the in-process Home Assistant runner which:
    - Runs on an ephemeral port (no conflicts)
    - Uses a temporary config directory
    - Loads entity states from scenario1 inputs.json
    - Pre-authenticates to skip onboarding

Screenshots are saved to tests/guides/sigenergy/screenshots/
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import shutil
import sys
from typing import TYPE_CHECKING, Any

from playwright.sync_api import sync_playwright

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.guides.ha_runner import LiveHomeAssistant, live_home_assistant  # noqa: E402

_LOGGER = logging.getLogger(__name__)

# Configuration
GUIDE_DIR = Path(__file__).parent
# Use scenario1 inputs for entity states - it has all the sensors we need
INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"
SCREENSHOTS_DIR = GUIDE_DIR / "screenshots"
NETWORK_NAME = "Sigenergy System"

# Short timeouts for fast iteration (most UI actions complete in <1s)
DEFAULT_TIMEOUT = 3000  # 3 seconds max
SHORT_WAIT = 0.1  # 100ms for UI stabilization
MEDIUM_WAIT = 0.2  # 200ms for animations
LONG_WAIT = 0.5  # 500ms for search results to populate


@dataclass
class SigenergyGuide:
    """Sigenergy setup guide with screenshot capture."""

    page: Page
    hass: LiveHomeAssistant
    output_dir: Path
    step_number: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)

    @property
    def url(self) -> str:
        """Get the Home Assistant URL."""
        return self.hass.url

    def capture(self, name: str) -> None:
        """Capture PNG screenshot of current page state."""
        self.step_number += 1
        filename = f"{self.step_number:02d}_{name}"
        _LOGGER.info("Capturing: %s", filename)

        # Save PNG
        png_path = self.output_dir / f"{filename}.png"
        self.page.screenshot(path=str(png_path))

        self.results.append(
            {
                "step": self.step_number,
                "name": name,
                "png": str(png_path),
            }
        )

    def click_button(self, name: str, *, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Click a button by its accessible name."""
        self.page.get_by_role("button", name=name).click(timeout=timeout)
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

    def fill_textbox(self, name: str, value: str) -> None:
        """Fill a textbox by its accessible name."""
        self.page.get_by_role("textbox", name=name).fill(value)

    def fill_spinbutton(self, name: str, value: str) -> None:
        """Fill a spinbutton (numeric input) by its accessible name."""
        spinbutton = self.page.get_by_role("spinbutton", name=name)
        spinbutton.clear()
        spinbutton.fill(value)

    def select_combobox_option(self, combobox_name: str, option_text: str) -> None:
        """Select an option from a combobox dropdown.

        Comboboxes in HA need to be clicked to open, then an option selected.
        """
        # Click to open the dropdown
        self.page.get_by_role("combobox", name=combobox_name).click()
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

        # Click the option
        self.page.get_by_role("option", name=option_text).click()
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

    def select_entity(self, field_label: str, search_term: str, entity_name: str) -> None:
        """Select an entity from picker dialog.

        Entity pickers in Home Assistant use custom web components with Shadow DOM.
        The picker is a ha-combo-box-item component within an ha-selector.

        We identify the correct picker by the field label appearing before it,
        then use HA's component selectors.
        """
        # Home Assistant entity pickers use ha-selector components
        # Find the ha-selector that contains our field label
        # The structure is: ha-selector containing the label text, with ha-combo-box-item inside
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")

        # Click the ha-combo-box-item inside (which shows "Select an entity")
        picker = selector.locator("ha-combo-box-item").first
        picker.click()
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

        # Wait for a dialog to appear - HA uses either field-named dialogs or "Select option"
        # Try field-specific name first, fall back to generic "Select option"
        entity_dialog = self.page.get_by_role("dialog", name=field_label)
        try:
            entity_dialog.wait_for(timeout=500)
        except Exception:
            # Fall back to generic dialog name
            entity_dialog = self.page.get_by_role("dialog", name="Select option")
            entity_dialog.wait_for(timeout=DEFAULT_TIMEOUT)

        # Fill the search textbox within the dialog
        search_input = entity_dialog.get_by_role("textbox", name="Search")
        search_input.fill(search_term)
        self.page.wait_for_timeout(1000)  # Wait 1s for search results to populate

        # Click the matching item in the dialog's results
        # HA uses different selectors: listitem in some dialogs, ha-combo-box-item in others
        try:
            entity_dialog.get_by_role("listitem").filter(has_text=entity_name).first.click(timeout=1000)
        except Exception:
            # Fall back to ha-combo-box-item
            entity_dialog.locator("ha-combo-box-item").filter(has_text=entity_name).first.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

    def add_another_entity(self, field_label: str, search_term: str, entity_name: str) -> None:
        """Add another entity to a multi-select field.

        For fields that accept multiple entities, a button appears after first selection.
        Uses the same HA component selectors as select_entity.
        """
        # Find the ha-selector containing this field and click its add button
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")
        add_btn = selector.get_by_role("button").first
        add_btn.click()
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

        # Wait for a dialog to appear - HA uses either field-named dialogs or "Select option"
        dialog = self.page.get_by_role("dialog", name=field_label)
        try:
            dialog.wait_for(timeout=500)
        except Exception:
            # Fall back to generic dialog name
            dialog = self.page.get_by_role("dialog", name="Select option")
            dialog.wait_for(timeout=DEFAULT_TIMEOUT)

        # Fill the search textbox within the dialog
        search_input = dialog.get_by_role("textbox", name="Search")
        search_input.fill(search_term)
        self.page.wait_for_timeout(1000)  # Wait 1s for search results to populate

        # Click the matching item in the dialog's results
        # HA uses different selectors: listitem in some dialogs, ha-combo-box-item in others
        try:
            dialog.get_by_role("listitem").filter(has_text=entity_name).first.click(timeout=1000)
        except Exception:
            # Fall back to ha-combo-box-item
            dialog.locator("ha-combo-box-item").filter(has_text=entity_name).first.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

    def close_network_dialog(self) -> None:
        """Close the network creation dialog (has 'Skip and finish' button)."""
        self.page.get_by_role("button", name="Skip and finish").click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    def close_element_dialog(self) -> None:
        """Close the element creation dialog (has 'Finish' button)."""
        self.page.get_by_role("button", name="Finish").click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)


def add_haeo_integration(guide: SigenergyGuide) -> None:
    """Add HAEO integration and create network."""
    _LOGGER.info("Adding HAEO integration...")

    # Navigate to integrations
    guide.page.goto(f"{guide.url}/config/integrations")
    guide.page.wait_for_load_state("networkidle")
    guide.page.wait_for_selector("button:has-text('Add integration')", timeout=DEFAULT_TIMEOUT)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("integrations_page")

    # Click the first "Add integration" button (inside ha-button, not the FAB)
    guide.page.locator("ha-button").get_by_role("button", name="Add integration").click()
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    # Wait for the dialog search box to appear
    guide.page.wait_for_selector("text=Search for a brand name", timeout=DEFAULT_TIMEOUT)

    # Search for our integration by its full name
    search_box = guide.page.get_by_role("textbox", name="Search for a brand name")
    search_box.fill("Home Assistant Energy")
    guide.page.wait_for_timeout(LONG_WAIT * 1000)

    guide.capture("search_haeo")

    # Click on the HAEO integration result
    haeo_item = guide.page.locator("ha-integration-list-item", has_text="Home Assistant Energy Optimizer")
    haeo_item.click(timeout=DEFAULT_TIMEOUT)

    # Wait for the HAEO Network Setup dialog
    guide.page.wait_for_selector("text=HAEO Network Setup", timeout=DEFAULT_TIMEOUT)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("network_form")

    # Fill network name
    guide.fill_textbox("Network Name*", NETWORK_NAME)

    guide.capture("network_filled")

    guide.click_button("Submit")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("network_created")
    guide.close_network_dialog()

    _LOGGER.info("HAEO integration added")


def add_inverter(guide: SigenergyGuide) -> None:
    """Add Inverter element."""
    _LOGGER.info("Adding Inverter...")

    guide.capture("before_inverter")

    # Click the Inverter button in the toolbar
    guide.click_button("Inverter")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    # Wait for the dialog to appear
    guide.page.wait_for_selector("text=Add Inverter", timeout=DEFAULT_TIMEOUT)
    guide.capture("inverter_form")

    # Fill inverter name (already has default "Inverter")
    guide.fill_textbox("Inverter Name*", "Inverter")

    # Select AC Connection - must explicitly click to select even if default shows
    guide.select_combobox_option("AC Connection*", "Switchboard")

    # Select power sensors
    guide.select_entity("Max DC to AC power", "max active power", "Sigen Plant Max Active Power")
    guide.select_entity("Max AC to DC power", "max active power", "Sigen Plant Max Active Power")

    guide.capture("inverter_filled")

    guide.click_button("Submit")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("inverter_created")
    guide.close_element_dialog()

    _LOGGER.info("Inverter added")


def add_battery(guide: SigenergyGuide) -> None:
    """Add Battery element."""
    _LOGGER.info("Adding Battery...")

    guide.click_button("Battery")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    # Wait for the dialog to fully load
    guide.page.wait_for_selector("text=Add Battery", timeout=DEFAULT_TIMEOUT)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)  # Extra wait for form to render
    guide.capture("battery_form")

    guide.fill_textbox("Battery Name*", "Battery")
    guide.select_combobox_option("Connection*", "Inverter")

    # Entity selections
    guide.select_entity("Capacity", "rated energy", "Rated Energy Capacity")
    guide.select_entity("State of Charge Charge Sensor", "state of charge", "Battery State of Charge")
    guide.select_entity("Max Charging Power", "rated charging", "Rated Charging Power")
    guide.select_entity("Max Discharging Power", "rated discharging", "Rated Discharging Power")

    # Fill numeric fields
    guide.fill_spinbutton("Min Charge Level*", "10")
    guide.fill_spinbutton("Max Charge Level*", "100")
    guide.fill_spinbutton("Round-trip Efficiency*", "99")
    guide.fill_spinbutton("Early Charge Incentive", "0.001")

    guide.capture("battery_filled")

    guide.click_button("Submit")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("battery_created")
    guide.close_element_dialog()

    _LOGGER.info("Battery added")


def add_solar(guide: SigenergyGuide) -> None:
    """Add Solar element with multiple forecast sensors."""
    _LOGGER.info("Adding Solar...")

    guide.click_button("Solar")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.page.wait_for_selector("text=Add Solar", timeout=DEFAULT_TIMEOUT)
    guide.capture("solar_form")

    guide.fill_textbox("Solar Name*", "Solar")
    guide.select_combobox_option("Connection*", "Inverter")

    # First forecast sensor - search for "east solar" to find East solar production forecast
    guide.select_entity("Forecast Sensors", "east solar", "East solar production forecast")

    # Multi-entity picker for additional forecast sensors is not yet implemented
    # For now, just use a single forecast sensor

    guide.capture("solar_filled")

    guide.click_button("Submit")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("solar_created")
    guide.close_element_dialog()

    _LOGGER.info("Solar added")


def add_grid(guide: SigenergyGuide) -> None:
    """Add Grid element."""
    _LOGGER.info("Adding Grid...")

    guide.click_button("Grid")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.page.wait_for_selector("text=Add Grid", timeout=DEFAULT_TIMEOUT)
    guide.capture("grid_form")

    guide.fill_textbox("Grid Name*", "Grid")
    guide.select_combobox_option("Connection*", "Switchboard")

    # Entity selections - single sensor for now (multi-entity picker not yet implemented)
    guide.select_entity("Import Price Sensors", "general price", "Home - General Price")

    guide.select_entity("Export Price Sensors", "feed in price", "Home - Feed In Price")

    # Fill limits
    guide.fill_spinbutton("Import Limit (Optional)", "55")
    guide.fill_spinbutton("Export Limit (Optional)", "30")

    guide.capture("grid_filled")

    guide.click_button("Submit")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("grid_created")
    guide.close_element_dialog()

    _LOGGER.info("Grid added")


def add_load(guide: SigenergyGuide) -> None:
    """Add Load element."""
    _LOGGER.info("Adding Load...")

    guide.click_button("Load")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.page.wait_for_selector("text=Add Load", timeout=DEFAULT_TIMEOUT)
    guide.capture("load_form")

    guide.fill_textbox("Load Name*", "Constant Load")
    guide.select_combobox_option("Connection*", "Switchboard")

    guide.select_entity("Forecast Sensors", "constant load", "Constant Load Power")

    guide.capture("load_filled")

    guide.click_button("Submit")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("load_created")
    guide.close_element_dialog()

    _LOGGER.info("Load added")


def verify_setup(guide: SigenergyGuide) -> None:
    """Verify the complete setup."""
    _LOGGER.info("Verifying setup...")

    # Navigate to HAEO integration page
    guide.page.goto(f"{guide.url}/config/integrations/integration/haeo")
    guide.page.wait_for_load_state("networkidle")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("final_overview")

    _LOGGER.info("Setup verified")


def login_to_ha(guide: SigenergyGuide) -> None:
    """Log in to Home Assistant if not already authenticated."""
    _LOGGER.info("Logging in to Home Assistant...")

    # Navigate to home page first
    guide.page.goto(guide.url)
    guide.page.wait_for_load_state("networkidle")

    # Check if we're on the login page
    if "/auth/authorize" in guide.page.url:
        # Wait for login form
        guide.page.wait_for_selector("text=Username", timeout=DEFAULT_TIMEOUT)

        # Fill credentials (hardcoded for test environment)
        guide.page.get_by_role("textbox", name="Username").fill("testuser")
        guide.page.get_by_role("textbox", name="Password").fill("testpass")
        guide.page.get_by_role("button", name="Log in").click()

        # Wait for redirect to complete
        guide.page.wait_for_url("**/lovelace/**", timeout=DEFAULT_TIMEOUT * 2)
        guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

        _LOGGER.info("Logged in successfully")
    else:
        _LOGGER.info("Already authenticated")


def run_guide(hass: LiveHomeAssistant, output_dir: Path, *, headless: bool = True) -> list[dict[str, Any]]:
    """Run the complete Sigenergy guide.

    Args:
        hass: LiveHomeAssistant instance
        output_dir: Directory to save screenshots
        headless: Whether to run browser headlessly

    Returns:
        List of captured screenshot results

    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})

        # Note: inject_auth sets up localStorage but HA may still redirect to login
        # since the frontend validates tokens via websocket
        hass.inject_auth(context)

        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            guide = SigenergyGuide(
                page=page,
                hass=hass,
                output_dir=output_dir,
            )

            # Login first (handles redirect to login page)
            login_to_ha(guide)

            # Run guide steps
            add_haeo_integration(guide)
            add_inverter(guide)
            add_battery(guide)
            add_solar(guide)
            add_grid(guide)
            add_load(guide)
            verify_setup(guide)

            return guide.results

        except Exception:
            _LOGGER.exception("Error running guide")
            # Capture error state
            error_path = output_dir / "error_state.png"
            page.screenshot(path=str(error_path))
            _LOGGER.info("Error screenshot: %s", error_path)
            raise

        finally:
            page.close()
            context.close()
            browser.close()


def main() -> None:
    """Run the complete Sigenergy guide as a standalone script."""
    # Configure logging for CLI output
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    _LOGGER.info("Sigenergy System Setup Guide")
    _LOGGER.info("=" * 50)
    _LOGGER.info("Output directory: %s", SCREENSHOTS_DIR)

    # Clean and create output directory
    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(parents=True)

    with live_home_assistant(timeout=60) as hass:
        _LOGGER.info("Home Assistant running at %s", hass.url)

        # Load entity states from scenario1
        _LOGGER.info("Loading entity states...")
        hass.load_states_from_file(INPUTS_FILE)
        _LOGGER.info("Loaded states from %s", INPUTS_FILE.name)

        # Run guide
        results = run_guide(hass, SCREENSHOTS_DIR, headless=True)

        _LOGGER.info("=" * 50)
        _LOGGER.info("Guide complete! %d screenshots captured", len(results))
        _LOGGER.info("Screenshots saved to: %s", SCREENSHOTS_DIR)


if __name__ == "__main__":
    main()
