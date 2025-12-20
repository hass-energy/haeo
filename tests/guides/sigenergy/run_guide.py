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
from tests.guides.singlefile_capture import capture_html  # noqa: E402

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
    debug_indicators: bool = True  # Enable full-screen crosshairs for debugging

    @property
    def url(self) -> str:
        """Get the Home Assistant URL."""
        return self.hass.url

    def _ensure_click_indicator_styles(self) -> None:
        """Inject the click indicator stylesheet if not already present.

        Uses a class-based approach so the indicator styling can be toggled
        off later by removing or disabling the stylesheet.
        """
        self.page.evaluate("""
            if (!document.getElementById('click-indicator-styles')) {
                const style = document.createElement('style');
                style.id = 'click-indicator-styles';
                style.textContent = `
                    /* Click target indicator - applied via data-click-target attribute */
                    [data-click-target] {
                        box-shadow:
                            0 0 0 3px rgba(255, 0, 0, 0.9),
                            0 0 0 5px white,
                            0 0 0 7px rgba(255, 0, 0, 0.9),
                            0 0 15px 5px rgba(255, 0, 0, 0.4) !important;
                        outline: none !important;
                    }
                `;
                document.head.appendChild(style);
            }
        """)

    def _show_click_indicator(self, locator: Any) -> None:
        """Mark the target element as a click target using a data attribute.

        The indicator styling is applied via CSS using [data-click-target].
        This approach doesn't modify ancestor elements and works regardless
        of overflow settings since box-shadow is drawn outside the element.

        When debug_indicators is True, also draws full-screen crosshairs in a
        separate top-layer dialog.
        """
        # Remove any existing indicators first
        self._remove_click_indicator()

        # Ensure stylesheet is present
        self._ensure_click_indicator_styles()

        # Get the element handle and add the data attribute
        element = locator.element_handle(timeout=1000)
        if not element:
            return

        # Mark the element as a click target
        element.evaluate("(el) => el.setAttribute('data-click-target', 'true')")

        # Add crosshairs in debug mode using a separate top-layer dialog
        if self.debug_indicators:
            pos = self._get_element_center(locator)
            if pos:
                x, y = pos
                self.page.evaluate(
                    """([x, y]) => {
                    const dialog = document.createElement('dialog');
                    dialog.id = 'click-indicator-crosshairs';
                    dialog.style.cssText = `
                        position: fixed;
                        inset: 0;
                        width: 100vw;
                        height: 100vh;
                        max-width: 100vw;
                        max-height: 100vh;
                        margin: 0;
                        padding: 0;
                        border: none;
                        background: transparent;
                        pointer-events: none;
                        overflow: visible;
                    `;

                    // Remove the default ::backdrop styling
                    const style = document.createElement('style');
                    style.textContent = '#click-indicator-crosshairs::backdrop { background: transparent; }';
                    dialog.appendChild(style);

                    const hLine = document.createElement('div');
                    hLine.style.cssText = `
                        position: fixed;
                        left: 0;
                        top: ${y}px;
                        width: 100vw;
                        height: 2px;
                        background: rgba(255, 0, 0, 0.7);
                        pointer-events: none;
                    `;
                    dialog.appendChild(hLine);

                    const vLine = document.createElement('div');
                    vLine.style.cssText = `
                        position: fixed;
                        left: ${x}px;
                        top: 0;
                        width: 2px;
                        height: 100vh;
                        background: rgba(255, 0, 0, 0.7);
                        pointer-events: none;
                    `;
                    dialog.appendChild(vLine);

                    document.body.appendChild(dialog);
                    dialog.showModal();
                }""",
                    [x, y],
                )

    def _remove_click_indicator(self) -> None:
        """Remove click indicator from any marked elements."""
        self.page.evaluate("""
            // Remove the data attribute from any marked elements
            const marked = document.querySelectorAll('[data-click-target]');
            for (const el of marked) {
                el.removeAttribute('data-click-target');
            }

            // Remove crosshairs dialog
            const crosshairs = document.getElementById('click-indicator-crosshairs');
            if (crosshairs) {
                crosshairs.close();
                crosshairs.remove();
            }
        """)

    def _get_element_center(self, locator: Any) -> tuple[float, float] | None:
        """Get the center position of an element."""
        try:
            box = locator.bounding_box(timeout=1000)
            if box:
                return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        except Exception:
            pass
        return None

    def _scroll_into_view(self, locator: Any) -> None:
        """Scroll element into view, centered in viewport."""
        try:
            locator.scroll_into_view_if_needed(timeout=1000)
            self.page.wait_for_timeout(100)  # Brief pause after scroll
        except Exception:
            pass

    def _capture_with_indicator(self, name: str, locator: Any) -> None:
        """Capture screenshot with click indicator attached to the target element."""
        self.step_number += 1
        filename = f"{self.step_number:02d}_{name}"
        _LOGGER.info("Capturing: %s", filename)

        self._show_click_indicator(locator)
        png_path = self.output_dir / f"{filename}.png"
        self.page.screenshot(path=str(png_path))

        # Also capture HTML snapshot
        html_path = self.output_dir / f"{filename}.html"
        self._capture_html(html_path)

        self._remove_click_indicator()

        self.results.append(
            {
                "step": self.step_number,
                "name": name,
                "png": str(png_path),
                "html": str(html_path),
            }
        )

    def capture(self, name: str) -> None:
        """Capture PNG screenshot and HTML snapshot of current page state."""
        self.step_number += 1
        filename = f"{self.step_number:02d}_{name}"
        _LOGGER.info("Capturing: %s", filename)

        png_path = self.output_dir / f"{filename}.png"
        self.page.screenshot(path=str(png_path))

        # Also capture HTML snapshot
        html_path = self.output_dir / f"{filename}.html"
        self._capture_html(html_path)

        self.results.append(
            {
                "step": self.step_number,
                "name": name,
                "png": str(png_path),
                "html": str(html_path),
            }
        )

    def _capture_html(self, path: Path) -> None:
        """Capture static HTML snapshot using SingleFile JavaScript injection.

        SingleFile creates a self-contained HTML file with all resources
        (styles, images, fonts) embedded inline. We inject the SingleFile
        JavaScript directly into the current page context to capture the
        authenticated state (unlike CLI which opens a new unauthenticated tab).

        The HTML captures the current DOM state including any open dialogs
        or form inputs. The PNG screenshot captures exact visual state.
        """
        capture_html(self.page, path)

    def click_button(self, name: str, *, timeout: int = DEFAULT_TIMEOUT, capture_name: str | None = None) -> None:
        """Click a button by its accessible name.

        If capture_name is provided, captures before (with indicator) and after (result).
        """
        button = self.page.get_by_role("button", name=name)

        if capture_name:
            self._scroll_into_view(button)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_click", button)

        button.click(timeout=timeout)
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

        if capture_name:
            self.page.wait_for_timeout(MEDIUM_WAIT * 1000)
            self.capture(f"{capture_name}_result")

    def fill_textbox(self, name: str, value: str, *, capture_name: str | None = None) -> None:
        """Fill a textbox by its accessible name.

        If capture_name is provided, captures before (with indicator) and after (filled).
        """
        textbox = self.page.get_by_role("textbox", name=name)

        if capture_name:
            self._scroll_into_view(textbox)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_field", textbox)

        textbox.fill(value)

        if capture_name:
            self.capture(f"{capture_name}_filled")

    def fill_spinbutton(self, name: str, value: str, *, capture_name: str | None = None) -> None:
        """Fill a spinbutton (numeric input) by its accessible name.

        If capture_name is provided, captures before (with indicator) and after (filled).
        """
        spinbutton = self.page.get_by_role("spinbutton", name=name)

        if capture_name:
            self._scroll_into_view(spinbutton)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_field", spinbutton)

        spinbutton.clear()
        spinbutton.fill(value)

        if capture_name:
            self.capture(f"{capture_name}_filled")

    def select_combobox_option(self, combobox_name: str, option_text: str, *, capture_name: str | None = None) -> None:
        """Select an option from a combobox dropdown.

        Comboboxes in HA need to be clicked to open, then an option selected.
        If capture_name is provided, captures the selection flow.
        """
        # Click to open the dropdown
        combobox = self.page.get_by_role("combobox", name=combobox_name)

        if capture_name:
            self._scroll_into_view(combobox)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_dropdown", combobox)

        combobox.click()
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

        # Click the option
        option = self.page.get_by_role("option", name=option_text)

        if capture_name:
            self._scroll_into_view(option)
            self._capture_with_indicator(f"{capture_name}_option", option)

        option.click()
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

        if capture_name:
            self.capture(f"{capture_name}_selected")

    def select_entity(
        self, field_label: str, search_term: str, entity_name: str, *, capture_name: str | None = None
    ) -> None:
        """Select an entity from picker dialog.

        Entity pickers in Home Assistant use custom web components with Shadow DOM.
        The picker is a ha-combo-box-item component within an ha-selector.

        We identify the correct picker by the field label appearing before it,
        then use HA's component selectors.
        If capture_name is provided, captures the selection flow.
        """
        # Home Assistant entity pickers use ha-selector components
        # Find the ha-selector that contains our field label
        # The structure is: ha-selector containing the label text, with ha-combo-box-item inside
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")

        # Click the ha-combo-box-item inside (which shows "Select an entity")
        picker = selector.locator("ha-combo-box-item").first

        if capture_name:
            self._scroll_into_view(picker)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_picker", picker)

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

        if capture_name:
            self.capture(f"{capture_name}_search")

        # Click the matching item in the dialog's results
        # HA uses different selectors: listitem in some dialogs, ha-combo-box-item in others
        try:
            result_item = entity_dialog.get_by_role("listitem").filter(has_text=entity_name).first
            if capture_name:
                self._scroll_into_view(result_item)
                self.capture(f"{capture_name}_select_before")
                self._capture_with_indicator(f"{capture_name}_select", result_item)
            result_item.click(timeout=1000)
        except Exception:
            # Fall back to ha-combo-box-item
            result_item = entity_dialog.locator("ha-combo-box-item").filter(has_text=entity_name).first
            if capture_name:
                self._scroll_into_view(result_item)
                self.capture(f"{capture_name}_select_before")
                self._capture_with_indicator(f"{capture_name}_select", result_item)
            result_item.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

        if capture_name:
            self.capture(f"{capture_name}_result")

    def add_another_entity(self, field_label: str, search_term: str, entity_name: str) -> None:
        """Add another entity to a multi-select field.

        For fields that accept multiple entities, an "Add entity" button appears after first selection.
        Uses the same HA dialog pattern as select_entity.
        """
        # Find the ha-selector containing this field
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")

        # Click the "Add entity" button within the selector
        add_btn = selector.get_by_role("button", name="Add entity")
        add_btn.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

        # Wait for a dialog to appear - HA uses "Select option" as the dialog name
        dialog = self.page.get_by_role("dialog", name="Select option")
        dialog.wait_for(timeout=DEFAULT_TIMEOUT)

        # Fill the search textbox within the dialog
        search_input = dialog.get_by_role("textbox", name="Search")
        search_input.fill(search_term)
        self.page.wait_for_timeout(1000)  # Wait 1s for search results to populate

        # Click the matching item in the dialog's results
        # HA uses different selectors: listitem in some dialogs, ha-combo-box-item in others
        try:
            result_item = dialog.get_by_role("listitem").filter(has_text=entity_name).first
            result_item.click(timeout=1000)
        except Exception:
            # Fall back to ha-combo-box-item
            result_item = dialog.locator("ha-combo-box-item").filter(has_text=entity_name).first
            result_item.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

    def close_network_dialog(self, *, capture_name: str | None = None) -> None:
        """Close the network creation dialog (has 'Skip and finish' button)."""
        button = self.page.get_by_role("button", name="Skip and finish")

        if capture_name:
            self._scroll_into_view(button)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_click", button)

        button.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    def close_element_dialog(self, *, capture_name: str | None = None) -> None:
        """Close the element creation dialog (has 'Finish' button)."""
        button = self.page.get_by_role("button", name="Finish")

        if capture_name:
            self._scroll_into_view(button)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_click", button)

        button.click(timeout=DEFAULT_TIMEOUT)
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
    add_btn = guide.page.locator("ha-button").get_by_role("button", name="Add integration")
    guide._capture_with_indicator("add_integration_click", add_btn)
    add_btn.click()
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
    guide._capture_with_indicator("select_haeo_click", haeo_item)
    haeo_item.click(timeout=DEFAULT_TIMEOUT)

    # Wait for the HAEO Network Setup dialog
    guide.page.wait_for_selector("text=HAEO Network Setup", timeout=DEFAULT_TIMEOUT)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("network_form")

    # Fill network name with capture
    guide.fill_textbox("Network Name*", NETWORK_NAME, capture_name="network_name")

    # Submit with capture
    guide.click_button("Submit", capture_name="network_submit")

    guide.close_network_dialog(capture_name="network_close")

    _LOGGER.info("HAEO integration added")


def add_inverter(guide: SigenergyGuide) -> None:
    """Add Inverter element."""
    _LOGGER.info("Adding Inverter...")

    # Click the Inverter button in the toolbar with capture
    guide.click_button("Inverter", capture_name="inverter_add")

    # Wait for the dialog to appear
    guide.page.wait_for_selector("text=Add Inverter", timeout=DEFAULT_TIMEOUT)

    # Fill inverter name
    guide.fill_textbox("Inverter Name*", "Inverter", capture_name="inverter_name")

    # Select AC Connection with capture
    guide.select_combobox_option("AC Connection*", "Switchboard", capture_name="inverter_connection")

    # Select power sensors with capture
    guide.select_entity(
        "Max DC to AC power", "max active power", "Sigen Plant Max Active Power", capture_name="inverter_dc_ac"
    )
    guide.select_entity(
        "Max AC to DC power", "max active power", "Sigen Plant Max Active Power", capture_name="inverter_ac_dc"
    )

    # Submit with capture
    guide.click_button("Submit", capture_name="inverter_submit")
    guide.close_element_dialog(capture_name="inverter_close")

    _LOGGER.info("Inverter added")


def add_battery(guide: SigenergyGuide) -> None:
    """Add Battery element."""
    _LOGGER.info("Adding Battery...")

    guide.click_button("Battery", capture_name="battery_add")

    # Wait for the dialog to fully load
    guide.page.wait_for_selector("text=Add Battery", timeout=DEFAULT_TIMEOUT)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    # Fill name with capture
    guide.fill_textbox("Battery Name*", "Battery", capture_name="battery_name")

    # Select connection
    guide.select_combobox_option("Connection*", "Inverter", capture_name="battery_connection")

    # Entity selections with captures
    guide.select_entity("Capacity", "rated energy", "Rated Energy Capacity", capture_name="battery_capacity")
    guide.select_entity(
        "State of Charge Charge Sensor", "state of charge", "Battery State of Charge", capture_name="battery_soc"
    )
    guide.select_entity("Max Charging Power", "rated charging", "Rated Charging Power", capture_name="battery_charge")
    guide.select_entity(
        "Max Discharging Power", "rated discharging", "Rated Discharging Power", capture_name="battery_discharge"
    )

    # Fill numeric fields with capture
    guide.fill_spinbutton("Min Charge Level*", "10", capture_name="battery_min_soc")
    guide.fill_spinbutton("Max Charge Level*", "100", capture_name="battery_max_soc")
    guide.fill_spinbutton("Round-trip Efficiency*", "99", capture_name="battery_efficiency")
    guide.fill_spinbutton("Early Charge Incentive", "0.001", capture_name="battery_incentive")

    # Submit
    guide.click_button("Submit", capture_name="battery_submit")
    guide.close_element_dialog(capture_name="battery_close")

    _LOGGER.info("Battery added")


def add_solar(guide: SigenergyGuide) -> None:
    """Add Solar element with multiple forecast sensors."""
    _LOGGER.info("Adding Solar...")

    guide.click_button("Solar", capture_name="solar_add")

    guide.page.wait_for_selector("text=Add Solar", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Solar Name*", "Solar", capture_name="solar_name")
    guide.select_combobox_option("Connection*", "Inverter", capture_name="solar_connection")

    # First forecast sensor
    guide.select_entity(
        "Forecast Sensors", "east solar today", "East solar production forecast", capture_name="solar_forecast"
    )

    # Add the other three array forecasts (no extra captures - too many screenshots)
    guide.add_another_entity("Forecast Sensors", "north solar today", "North solar production forecast")
    guide.add_another_entity("Forecast Sensors", "south solar today", "South solar prediction forecast")
    guide.add_another_entity("Forecast Sensors", "west solar today", "West solar production forecast")

    guide.click_button("Submit", capture_name="solar_submit")
    guide.close_element_dialog(capture_name="solar_close")

    _LOGGER.info("Solar added")


def add_grid(guide: SigenergyGuide) -> None:
    """Add Grid element."""
    _LOGGER.info("Adding Grid...")

    guide.click_button("Grid", capture_name="grid_add")

    guide.page.wait_for_selector("text=Add Grid", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Grid Name*", "Grid", capture_name="grid_name")
    guide.select_combobox_option("Connection*", "Switchboard", capture_name="grid_connection")

    # Import price with capture
    guide.select_entity(
        "Import Price Sensors", "general price", "Home - General Price", capture_name="grid_import_price"
    )
    guide.add_another_entity("Import Price Sensors", "general forecast", "Home - General Forecast")

    # Export price
    guide.select_entity(
        "Export Price Sensors", "feed in price", "Home - Feed In Price", capture_name="grid_export_price"
    )
    guide.add_another_entity("Export Price Sensors", "feed in forecast", "Home - Feed In Forecast")

    # Fill limits
    guide.fill_spinbutton("Import Limit (Optional)", "55", capture_name="grid_import_limit")
    guide.fill_spinbutton("Export Limit (Optional)", "30", capture_name="grid_export_limit")

    guide.click_button("Submit", capture_name="grid_submit")
    guide.close_element_dialog(capture_name="grid_close")

    _LOGGER.info("Grid added")


def add_load(guide: SigenergyGuide) -> None:
    """Add Load element."""
    _LOGGER.info("Adding Load...")

    guide.click_button("Load", capture_name="load_add")

    guide.page.wait_for_selector("text=Add Load", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Load Name*", "Constant Load", capture_name="load_name")
    guide.select_combobox_option("Connection*", "Switchboard", capture_name="load_connection")

    guide.select_entity("Forecast Sensors", "constant load", "Constant Load Power", capture_name="load_forecast")

    guide.click_button("Submit", capture_name="load_submit")
    guide.close_element_dialog(capture_name="load_close")

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

    _LOGGER.info("Current URL after navigation: %s", guide.page.url)

    # Check if we're in onboarding - handle onboarding redirect first
    if "/onboarding" in guide.page.url:
        msg = (
            f"Home Assistant is in onboarding mode (URL: {guide.page.url}). Onboarding should be bypassed by ha_runner."
        )
        raise RuntimeError(msg)

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
        # Use remote debugging port so SingleFile CLI can capture HTML snapshots
        browser = p.chromium.launch(
            headless=headless,
            args=["--remote-debugging-port=9222"],
        )
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
