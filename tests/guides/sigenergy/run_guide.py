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
import os
from pathlib import Path
import shutil
import sys
from typing import TYPE_CHECKING, Any

from playwright.sync_api import sync_playwright

from tests.guides.ha_runner import LiveHomeAssistant, live_home_assistant

if TYPE_CHECKING:
    from playwright.sync_api import Page

_LOGGER = logging.getLogger(__name__)

# Configuration
GUIDE_DIR = Path(__file__).parent
PROJECT_ROOT = GUIDE_DIR.parent.parent.parent
# Use scenario1 inputs for entity states - it has all the sensors we need
INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"
SCREENSHOTS_DIR = GUIDE_DIR / "screenshots"

# JavaScript for click indicator overlay
CLICK_INDICATOR_JS_FILE = GUIDE_DIR.parent / "js" / "click_indicator.js"
NETWORK_NAME = "Sigenergy System"

# Short timeouts for fast iteration (most UI actions complete in <1s)
DEFAULT_TIMEOUT = 5000  # 5 seconds max
SEARCH_TIMEOUT = 10000  # 10 seconds for search results to populate


@dataclass
class SigenergyGuide:
    """Sigenergy setup guide with screenshot capture."""

    page: Page
    hass: LiveHomeAssistant
    output_dir: Path
    step_number: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    debug_indicators: bool = False  # Full-screen crosshairs for debugging
    dark_mode: bool = False  # Use dark theme for screenshots
    pause_mode: bool = False  # Pause after each step for debugging

    @property
    def url(self) -> str:
        """Get the Home Assistant URL."""
        return self.hass.url

    @property
    def port(self) -> int:
        """Get the Home Assistant port."""
        return self.hass.port

    def pause(self, message: str = "Paused") -> None:
        """Pause execution and wait for user input.

        Useful for debugging - allows inspection of the browser state.
        The HA server continues running so you can connect via Playwright MCP.
        """
        _LOGGER.info("\n%s", "=" * 60)
        _LOGGER.info("PAUSED: %s", message)
        _LOGGER.info("Home Assistant URL: %s", self.url)
        _LOGGER.info("Port: %s", self.port)
        _LOGGER.info("You can connect via Playwright MCP to inspect the page.")
        _LOGGER.info("Press Enter to continue...")
        _LOGGER.info("=" * 60)
        input()

    def apply_dark_theme(self) -> None:
        """Apply dark theme to Home Assistant.

        Uses JavaScript to set the theme mode via localStorage.
        Home Assistant stores user theme preferences in localStorage.
        """
        _LOGGER.info("Applying dark theme...")

        # Set the theme preference via localStorage
        # HA frontend uses 'selectedTheme' to store the user's theme choice
        self.page.evaluate("""
            // Set dark mode preference in localStorage
            // This matches how HA frontend stores theme preferences
            const themeData = {
                theme: 'default',
                dark: true  // Force dark mode
            };
            localStorage.setItem('selectedTheme', JSON.stringify(themeData));

            // Also try to trigger theme reload by dispatching event
            window.dispatchEvent(new CustomEvent('settheme', { detail: themeData }));
        """)

        # Reload the page to apply the theme
        self.page.reload()
        self.page.wait_for_load_state("networkidle")

    def _show_click_indicator(self, locator: Any) -> None:
        """Show click indicator as an overlay positioned at the target element.

        Creates a separate overlay element on the popover layer that matches
        the target element's bounding box and border-radius. This approach
        avoids clipping issues from parent overflow:hidden.

        When debug_indicators is True, also draws full-screen crosshairs.
        """
        # Remove any existing indicators first
        self._remove_click_indicator()

        # Get the element handle
        element = locator.element_handle(timeout=1000)
        if not element:
            return

        # Build selector for finding the best visual target element
        clickable_selector = (
            "button, [role='button'], [role='option'], [role='listitem'], a, "
            "ha-list-item, ha-combo-box-item, mwc-list-item, md-item, "
            "ha-button, ha-icon-button, .mdc-text-field, ha-textfield, "
            "input, select, ha-select, ha-integration-list-item"
        )

        # Load and execute click indicator JavaScript from external file
        js_code = CLICK_INDICATOR_JS_FILE.read_text()
        element.evaluate(js_code, clickable_selector)

        # Add crosshairs in debug mode
        # Use absolute positioning within the document body which has min-width 1280px
        # This ensures crosshairs stay aligned even when viewport is smaller
        if self.debug_indicators:
            pos = self._get_element_center(locator)
            if pos:
                x, y = pos
                self.page.evaluate(
                    """([x, y]) => {
                    // Create crosshairs container as a regular div (not dialog)
                    // This allows it to be positioned relative to the document body
                    const container = document.createElement('div');
                    container.id = 'click-indicator-crosshairs';
                    container.style.cssText = `
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        pointer-events: none;
                        z-index: 99999;
                        overflow: visible;
                    `;

                    const hLine = document.createElement('div');
                    hLine.style.cssText = `
                        position: absolute;
                        left: 0;
                        top: ${y}px;
                        width: 100%;
                        height: 2px;
                        background: rgba(255, 0, 0, 0.7);
                        pointer-events: none;
                    `;
                    container.appendChild(hLine);

                    const vLine = document.createElement('div');
                    vLine.style.cssText = `
                        position: absolute;
                        left: ${x}px;
                        top: 0;
                        width: 2px;
                        height: 100%;
                        background: rgba(255, 0, 0, 0.7);
                        pointer-events: none;
                    `;
                    container.appendChild(vLine);

                    document.body.appendChild(container);
                }""",
                    [x, y],
                )

    def _remove_click_indicator(self) -> None:
        """Remove click indicator overlay and crosshairs."""
        self.page.evaluate("""
            // Remove overlay
            const overlay = document.getElementById('click-indicator-overlay');
            if (overlay) {
                try {
                    overlay.hidePopover();
                } catch (e) {
                    // Ignore if popover API not supported
                }
                overlay.remove();
            }

            // Remove crosshairs container
            const crosshairs = document.getElementById('click-indicator-crosshairs');
            if (crosshairs) {
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
        locator.scroll_into_view_if_needed(timeout=DEFAULT_TIMEOUT)

    def _capture_with_indicator(self, name: str, locator: Any) -> None:
        """Capture screenshot with click indicator attached to the target element."""
        self.step_number += 1
        filename = f"{self.step_number:02d}_{name}"
        _LOGGER.info("Capturing: %s", filename)

        self._show_click_indicator(locator)
        png_path = self.output_dir / f"{filename}.png"
        self.page.screenshot(path=str(png_path), animations="disabled")
        self._remove_click_indicator()

        self.results.append(
            {
                "step": self.step_number,
                "name": name,
                "png": str(png_path),
            }
        )

    def capture(self, name: str) -> None:
        """Capture PNG screenshot of current page state."""
        self.step_number += 1
        filename = f"{self.step_number:02d}_{name}"

        # Log visible text for debugging
        visible_text = self.page.locator("body").inner_text(timeout=1000)
        # Truncate and clean up for logging
        text_preview = " ".join(visible_text.split())[:200]
        _LOGGER.info("Capturing: %s | Text: %s...", filename, text_preview)

        png_path = self.output_dir / f"{filename}.png"
        self.page.screenshot(path=str(png_path), animations="disabled")

        self.results.append(
            {
                "step": self.step_number,
                "name": name,
                "png": str(png_path),
            }
        )

    def click_button(
        self,
        name: str,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        capture_name: str | None = None,
    ) -> None:
        """Click a button by its accessible name.

        If capture_name is provided, captures before (with indicator) and after (result).
        """
        button = self.page.get_by_role("button", name=name)
        button.wait_for(state="visible", timeout=timeout)

        if capture_name:
            self._scroll_into_view(button)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_click", button)

        button.click(timeout=timeout)

        if capture_name:
            # Wait for any navigation or UI update to complete
            self.page.wait_for_load_state("domcontentloaded")
            self.capture(f"{capture_name}_result")

    def fill_textbox(self, name: str, value: str, *, capture_name: str | None = None) -> None:
        """Fill a textbox by its accessible name.

        If the textbox already contains the target value, skips filling.
        If capture_name is provided, captures before (with indicator) and after (filled).
        """
        textbox = self.page.get_by_role("textbox", name=name)

        # Check if field is already filled with the target value
        current_value = textbox.input_value(timeout=DEFAULT_TIMEOUT)
        if current_value == value:
            # Field is already correctly filled, skip
            return

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
        combobox.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self._scroll_into_view(combobox)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_dropdown", combobox)

        combobox.click()

        # Wait for the option to appear in the dropdown
        option = self.page.get_by_role("option", name=option_text)
        option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self._scroll_into_view(option)
            self._capture_with_indicator(f"{capture_name}_option", option)

        option.click()

        # Wait for dropdown to close by checking option is no longer visible
        option.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self.capture(f"{capture_name}_selected")

    def select_entity(
        self,
        field_label: str,
        search_term: str,
        entity_name: str,
        *,
        capture_name: str | None = None,
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
        picker.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self._scroll_into_view(picker)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_picker", picker)

        picker.click()

        # Wait for the "Select option" dialog to appear
        entity_dialog = self.page.get_by_role("dialog", name="Select option")
        entity_dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        # Fill the search textbox within the dialog
        search_input = entity_dialog.get_by_role("textbox", name="Search")
        search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self._capture_with_indicator(f"{capture_name}_search_box", search_input)

        search_input.fill(search_term)

        # Wait for the matching result item to appear
        # Use text content matching - the item should be visible after search completes
        result_item = entity_dialog.locator(f":text('{entity_name}')").first
        result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        if capture_name:
            self.capture(f"{capture_name}_search")
            self._scroll_into_view(result_item)
            self.capture(f"{capture_name}_select_before")
            self._capture_with_indicator(f"{capture_name}_select", result_item)

        result_item.click(timeout=DEFAULT_TIMEOUT)

        # Wait for dialog to close
        entity_dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self.capture(f"{capture_name}_result")

    def add_another_entity(
        self,
        field_label: str,
        search_term: str,
        entity_name: str,
        *,
        capture_name: str | None = None,
    ) -> None:
        """Add another entity to a multi-select field.

        For fields that accept multiple entities, an "Add entity" button appears after first selection.
        Uses the same HA dialog pattern as select_entity.
        """
        # Find the ha-selector containing this field
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")

        # Click the "Add entity" button within the selector
        add_btn = selector.get_by_role("button", name="Add entity")
        add_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self._scroll_into_view(add_btn)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_add_btn", add_btn)

        add_btn.click(timeout=DEFAULT_TIMEOUT)

        # Wait for the "Select option" dialog to appear
        dialog = self.page.get_by_role("dialog", name="Select option")
        dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self.capture(f"{capture_name}_dialog")

        # Fill the search textbox within the dialog
        search_input = dialog.get_by_role("textbox", name="Search")
        search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self._capture_with_indicator(f"{capture_name}_search_box", search_input)

        search_input.fill(search_term)

        # Wait for the matching result item to appear
        # Use text content matching - the item should be visible after search completes
        result_item = dialog.locator(f":text('{entity_name}')").first
        result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        if capture_name:
            self.capture(f"{capture_name}_search")
            self._scroll_into_view(result_item)
            self.capture(f"{capture_name}_select_before")
            self._capture_with_indicator(f"{capture_name}_select", result_item)

        result_item.click(timeout=DEFAULT_TIMEOUT)

        # Wait for dialog to close
        dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self.capture(f"{capture_name}_result")

    def close_network_dialog(self, *, capture_name: str | None = None) -> None:
        """Close the network creation dialog (has 'Skip and finish' button)."""
        button = self.page.get_by_role("button", name="Skip and finish")
        button.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self._scroll_into_view(button)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_click", button)

        button.click(timeout=DEFAULT_TIMEOUT)

        # Wait for dialog to close
        button.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

    def close_element_dialog(self, *, capture_name: str | None = None) -> None:
        """Close the element creation dialog.

        Home Assistant subentry flows show a success dialog after creation with a Finish button.
        """
        # Wait for the Finish button to appear (success dialog)
        # This may take longer as the backend processes the creation
        button = self.page.get_by_role("button", name="Finish")
        button.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        if capture_name:
            self._scroll_into_view(button)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_click", button)

        button.click(timeout=DEFAULT_TIMEOUT)

        # Wait for dialog to close
        button.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

        _LOGGER.info("Dialog closed successfully")


def add_haeo_integration(guide: SigenergyGuide) -> None:
    """Add HAEO integration and create network."""
    _LOGGER.info("Adding HAEO integration...")

    # Navigate to integrations
    guide.page.goto(f"{guide.url}/config/integrations")
    guide.page.wait_for_load_state("networkidle")

    # Wait for the Add integration button to be visible
    add_btn = guide.page.locator("ha-button").get_by_role("button", name="Add integration")
    add_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.capture("integrations_page")

    # Click the "Add integration" button
    guide._capture_with_indicator("add_integration_click", add_btn)
    add_btn.click()

    # Wait for the dialog search box to appear
    search_box = guide.page.get_by_role("textbox", name="Search for a brand name")
    search_box.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.capture("add_integration_dialog")

    # Click and capture the search box
    guide._capture_with_indicator("search_box_click", search_box)
    search_box.click()

    # Type the search term with capture
    search_box.fill("HAEO")

    # Wait for search results to appear - HAEO item should be visible
    haeo_item = guide.page.locator("ha-integration-list-item", has_text="HAEO")
    haeo_item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.capture("search_haeo")

    # Click on the HAEO integration result
    guide._capture_with_indicator("select_haeo_click", haeo_item)
    haeo_item.click(timeout=DEFAULT_TIMEOUT)

    # Wait for the HAEO Setup dialog - use the dialog title which is more specific
    setup_heading = guide.page.get_by_title("HAEO Setup")
    setup_heading.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.capture("network_form")

    # Fill system name with capture
    guide.fill_textbox("System Name", NETWORK_NAME, capture_name="network_name")

    # Submit with capture
    guide.click_button("Submit", capture_name="network_submit")

    # Wait for the integration to be set up - wait for network idle and page load
    guide.page.wait_for_load_state("networkidle")

    # Navigate to the HAEO integration page to add elements
    guide.page.goto(f"{guide.url}/config/integrations/integration/haeo")
    guide.page.wait_for_load_state("networkidle")

    # Wait for the integration page to be ready - look for an element button
    guide.page.get_by_role("button", name="Inverter").wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.capture("haeo_integration_page")

    _LOGGER.info("HAEO integration added")


def add_inverter(guide: SigenergyGuide) -> None:
    """Add Inverter element."""
    _LOGGER.info("Adding Inverter...")

    # Click the Inverter button in the toolbar with capture
    guide.click_button("Inverter", capture_name="inverter_add")

    # Wait for the dialog to appear
    dialog_title = guide.page.get_by_title("Inverter Configuration")
    dialog_title.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    # Fill inverter name
    guide.fill_textbox("Inverter Name", "Inverter", capture_name="inverter_name")

    # Select AC Connection with capture
    guide.select_combobox_option("AC Connection", "Switchboard", capture_name="inverter_connection")

    # Select power sensors with capture
    guide.select_entity(
        "Max DC to AC Power",
        "max active power",
        "Sigen Plant Max Active Power",
        capture_name="inverter_dc_ac",
    )
    guide.select_entity(
        "Max AC to DC Power",
        "max active power",
        "Sigen Plant Max Active Power",
        capture_name="inverter_ac_dc",
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
    dialog_title = guide.page.get_by_title("Battery Configuration")
    dialog_title.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    # Fill name with capture
    guide.fill_textbox("Battery Name", "Battery", capture_name="battery_name")

    # Select connection
    guide.select_combobox_option("Connection", "Inverter", capture_name="battery_connection")

    # Entity selections with captures
    guide.select_entity(
        "Capacity",
        "rated energy",
        "Rated Energy Capacity",
        capture_name="battery_capacity",
    )
    guide.select_entity(
        "State of Charge",
        "state of charge",
        "Battery State of Charge",
        capture_name="battery_soc",
    )
    guide.select_entity(
        "Max Charging Power",
        "rated charging",
        "Rated Charging Power",
        capture_name="battery_charge",
    )
    guide.select_entity(
        "Max Discharging Power",
        "rated discharging",
        "Rated Discharging Power",
        capture_name="battery_discharge",
    )

    # Submit step 1 - entity selection
    guide.click_button("Submit", capture_name="battery_submit")

    # Step 2: Values page - battery may show configurable values for min/max charge
    # Check if there's a Submit button (meaning we're on step 2) or Finish button (success dialog)
    submit_button = guide.page.get_by_role("button", name="Submit")
    if submit_button.count() > 0 and submit_button.is_visible(timeout=1000):
        # We're on step 2 - fill in any visible spinbuttons and submit
        min_charge = guide.page.get_by_role("spinbutton", name="Min Charge Level")
        if min_charge.count() > 0 and min_charge.is_visible(timeout=1000):
            guide.fill_spinbutton("Min Charge Level", "10", capture_name="battery_min_soc")

        max_charge = guide.page.get_by_role("spinbutton", name="Max Charge Level")
        if max_charge.count() > 0 and max_charge.is_visible(timeout=1000):
            guide.fill_spinbutton("Max Charge Level", "100", capture_name="battery_max_soc")

        # Submit step 2
        guide.click_button("Submit", capture_name="battery_values_submit")

    # Close the success dialog
    guide.close_element_dialog(capture_name="battery_close")

    _LOGGER.info("Battery added")


def add_solar(guide: SigenergyGuide) -> None:
    """Add Solar element with multiple forecast sensors."""
    _LOGGER.info("Adding Solar...")

    guide.click_button("Solar", capture_name="solar_add")

    dialog_title = guide.page.get_by_title("Solar Configuration")
    dialog_title.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Solar Name", "Solar", capture_name="solar_name")
    guide.select_combobox_option("Connection", "Inverter", capture_name="solar_connection")

    # First forecast sensor
    guide.select_entity(
        "Forecast",
        "east solar today",
        "East solar production forecast",
        capture_name="solar_forecast",
    )

    # Add the other three array forecasts
    guide.add_another_entity(
        "Forecast",
        "north solar today",
        "North solar production forecast",
        capture_name="solar_forecast2",
    )
    guide.add_another_entity(
        "Forecast",
        "south solar today",
        "South solar prediction forecast",
        capture_name="solar_forecast3",
    )
    guide.add_another_entity(
        "Forecast",
        "west solar today",
        "West solar production forecast",
        capture_name="solar_forecast4",
    )

    guide.click_button("Submit", capture_name="solar_submit")
    guide.close_element_dialog(capture_name="solar_close")

    _LOGGER.info("Solar added")


def add_grid(guide: SigenergyGuide) -> None:
    """Add Grid element."""
    _LOGGER.info("Adding Grid...")

    guide.click_button("Grid", capture_name="grid_add")

    dialog_title = guide.page.get_by_title("Grid Configuration")
    dialog_title.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Grid Name", "Grid", capture_name="grid_name")
    guide.select_combobox_option("Connection", "Switchboard", capture_name="grid_connection")

    # Pause here to debug entity selection highlighting
    if guide.pause_mode:
        guide.pause("Before grid entity selection - inspect the dialog")

    # Import price with capture
    guide.select_entity(
        "Import Price",
        "general price",
        "Home - General Price",
        capture_name="grid_import_price",
    )
    guide.add_another_entity(
        "Import Price",
        "general forecast",
        "Home - General Forecast",
        capture_name="grid_import_price2",
    )

    # Export price
    guide.select_entity(
        "Export Price",
        "feed in price",
        "Home - Feed In Price",
        capture_name="grid_export_price",
    )
    guide.add_another_entity(
        "Export Price",
        "feed in forecast",
        "Home - Feed In Forecast",
        capture_name="grid_export_price2",
    )

    # Submit step 1 → moves to step 2 (values) for limit spinbuttons
    guide.click_button("Submit", capture_name="grid_step1_submit")

    # Step 2: Wait for Import Limit spinbutton to appear, then fill values
    import_limit = guide.page.get_by_role("spinbutton", name="Import Limit")
    import_limit.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.fill_spinbutton("Import Limit", "55", capture_name="grid_import_limit")
    guide.fill_spinbutton("Export Limit", "30", capture_name="grid_export_limit")

    # Submit step 2
    guide.click_button("Submit", capture_name="grid_submit")
    guide.close_element_dialog(capture_name="grid_close")

    _LOGGER.info("Grid added")


def add_load(guide: SigenergyGuide) -> None:
    """Add Load element.

    For a constant load, we use "HAEO Configurable" which requires a two-step flow:
    1. Select the configurable entity in step 1
    2. Enter the constant value in step 2
    """
    _LOGGER.info("Adding Load...")

    guide.click_button("Load", capture_name="load_add")

    dialog_title = guide.page.get_by_title("Load Configuration")
    dialog_title.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Load Name", "Constant Load", capture_name="load_name")
    guide.select_combobox_option("Connection", "Switchboard", capture_name="load_connection")

    # For constant load, select the HAEO Configurable entity
    guide.select_entity("Forecast", "configurable", "Configurable Entity", capture_name="load_forecast")

    # Step 1 submit - triggers step 2 for configurable values
    guide.click_button("Submit", capture_name="load_submit_step1")

    # Step 2: Wait for Forecast spinbutton to appear, then enter the constant load value
    forecast_spinbutton = guide.page.get_by_role("spinbutton", name="Forecast")
    forecast_spinbutton.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    guide.fill_spinbutton("Forecast", "1", capture_name="load_forecast_value")

    # Step 2 submit
    guide.click_button("Submit", capture_name="load_submit_step2")
    guide.close_element_dialog(capture_name="load_close")

    _LOGGER.info("Load added")


def verify_setup(guide: SigenergyGuide) -> None:
    """Verify the complete setup."""
    _LOGGER.info("Verifying setup...")

    # Navigate to HAEO integration page
    guide.page.goto(f"{guide.url}/config/integrations/integration/haeo")
    guide.page.wait_for_load_state("networkidle")

    # Wait for page to be ready - look for an element that indicates the page is loaded
    # Use .first because there may be multiple elements with same name (toolbar + card)
    guide.page.get_by_role("button", name="Inverter").first.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

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
        username_field = guide.page.get_by_role("textbox", name="Username")
        username_field.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        # Fill credentials (hardcoded for test environment)
        username_field.fill("testuser")
        guide.page.get_by_role("textbox", name="Password").fill("testpass")
        guide.page.get_by_role("button", name="Log in").click()

        # Wait for redirect to complete
        guide.page.wait_for_url("**/lovelace/**", timeout=DEFAULT_TIMEOUT * 2)
        guide.page.wait_for_load_state("networkidle")

        _LOGGER.info("Logged in successfully")
    else:
        _LOGGER.info("Already authenticated")


def run_guide(
    hass: LiveHomeAssistant,
    output_dir: Path,
    *,
    headless: bool = True,
    dark_mode: bool = False,
    pause_mode: bool | None = None,
) -> list[dict[str, Any]]:
    """Run the complete Sigenergy guide.

    Args:
        hass: LiveHomeAssistant instance
        output_dir: Directory to save screenshots
        headless: Whether to run browser headlessly
        dark_mode: Whether to use dark theme
        pause_mode: Whether to pause after each step (default: from GUIDE_PAUSE env var)

    Returns:
        List of captured screenshot results

    """
    # Check environment variable for pause mode if not explicitly set
    if pause_mode is None:
        pause_mode = os.environ.get("GUIDE_PAUSE", "").lower() in ("1", "true", "yes")

    # Log connection info for debugging
    _LOGGER.info("\n%s", "=" * 60)
    _LOGGER.info("Home Assistant URL: %s", hass.url)
    _LOGGER.info("Port: %s", hass.port)
    if pause_mode:
        _LOGGER.info("PAUSE MODE ENABLED - will pause after each step")
    _LOGGER.info("%s\n", "=" * 60)

    with sync_playwright() as p:
        # Use remote debugging port so SingleFile CLI can capture HTML snapshots
        browser = p.chromium.launch(
            headless=headless,
            args=["--remote-debugging-port=9222"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})

        # Note: inject_auth sets up localStorage but HA may still redirect to login
        # since the frontend validates tokens via websocket
        hass.inject_auth(context, dark_mode=dark_mode)

        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            guide = SigenergyGuide(
                page=page,
                hass=hass,
                output_dir=output_dir,
                dark_mode=dark_mode,
                pause_mode=pause_mode,
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
    """Run the complete Sigenergy guide as a standalone script.

    Usage:
        python run_guide.py           # Normal headless run
        python run_guide.py --pause   # Non-headless with pause for debugging
    """
    pause_mode = "--pause" in sys.argv
    headless = not pause_mode  # Non-headless when pausing

    # Configure logging for CLI output
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    _LOGGER.info("Sigenergy System Setup Guide")
    _LOGGER.info("=" * 50)
    _LOGGER.info("Output directory: %s", SCREENSHOTS_DIR)
    if pause_mode:
        _LOGGER.info("PAUSE MODE: Browser will be visible, pauses enabled")

    # Clean and create output directory
    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(parents=True)

    with live_home_assistant(timeout=120) as hass:
        _LOGGER.info("Home Assistant running at %s", hass.url)

        # Load entity states from scenario1
        _LOGGER.info("Loading entity states...")
        hass.load_states_from_file(INPUTS_FILE)
        _LOGGER.info("Loaded states from %s", INPUTS_FILE.name)

        # Run guide
        results = run_guide(hass, SCREENSHOTS_DIR, headless=headless, pause_mode=pause_mode)

        _LOGGER.info("=" * 50)
        _LOGGER.info("Guide complete! %d screenshots captured", len(results))
        _LOGGER.info("Screenshots saved to: %s", SCREENSHOTS_DIR)


if __name__ == "__main__":
    main()
