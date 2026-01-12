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
    debug_indicators: bool = False  # Full-screen crosshairs for debugging
    dark_mode: bool = False  # Use dark theme for screenshots

    @property
    def url(self) -> str:
        """Get the Home Assistant URL."""
        return self.hass.url

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
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    def _ensure_click_indicator_styles(self) -> None:
        """Inject the click indicator stylesheet if not already present.

        Uses a class-based approach so the indicator styling can be toggled
        off later by removing or disabling the stylesheet.

        Note: This CSS only affects elements in the light DOM.
        For Shadow DOM elements, we apply inline styles directly in
        _show_click_indicator().
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

    # Box-shadow CSS value for click indicator (used for inline styles on Shadow DOM elements)
    _CLICK_INDICATOR_STYLE = (
        "0 0 0 3px rgba(255, 0, 0, 0.9), "
        "0 0 0 5px white, "
        "0 0 0 7px rgba(255, 0, 0, 0.9), "
        "0 0 15px 5px rgba(255, 0, 0, 0.4)"
    )

    def _show_click_indicator(self, locator: Any) -> None:
        """Mark the target element as a click target using a data attribute and inline styles.

        The indicator styling is applied both via CSS (for light DOM elements)
        and inline styles (for Shadow DOM elements where external CSS doesn't apply).
        Box-shadow is used because it's drawn outside the element and isn't affected
        by overflow settings.

        When debug_indicators is True, also draws full-screen crosshairs in a
        separate top-layer dialog.
        """
        # Remove any existing indicators first
        self._remove_click_indicator()

        # Ensure stylesheet is present (for light DOM elements)
        self._ensure_click_indicator_styles()

        # Get the element handle and add the data attribute + inline styles
        element = locator.element_handle(timeout=1000)
        if not element:
            return

        # Find a more visually meaningful element to highlight
        # Sometimes locators resolve to tiny inner elements; we want the visual container
        box_shadow = self._CLICK_INDICATOR_STYLE
        element.evaluate(
            """(el, boxShadow) => {
                // Try to find a better element to highlight
                // Walk up the DOM to find a semantically meaningful clickable element
                let target = el;
                
                // Minimum size for a meaningful indicator (e.g., not just text content)
                const minSize = 20;
                const rect = el.getBoundingClientRect();
                
                // If the element is very small, look for a better parent
                if (rect.width < minSize || rect.height < minSize) {
                    // Look for common clickable parent patterns
                    const clickableParent = el.closest('button, [role="button"], [role="option"], [role="listitem"], a, ha-list-item, ha-combo-box-item, mwc-list-item, md-item, ha-button, ha-icon-button, .mdc-text-field, ha-textfield, input, select, ha-select, ha-integration-list-item');
                    if (clickableParent) {
                        target = clickableParent;
                    }
                }
                
                // Always prefer ha-integration-list-item, md-item, or similar list items
                const integrationItem = el.closest('ha-integration-list-item');
                if (integrationItem) {
                    target = integrationItem;
                }
                
                const mdItem = el.closest('md-item');
                if (mdItem) {
                    target = mdItem;
                }
                
                // For list items and options, prefer the item element itself
                const listItem = el.closest('[role="listitem"], [role="option"]');
                if (listItem) {
                    target = listItem;
                }
                
                // Also check if we're inside a form field and should highlight the field container
                const textField = el.closest('.mdc-text-field, ha-textfield, ha-select, ha-combo-box');
                if (textField) {
                    const fieldRect = textField.getBoundingClientRect();
                    const elRect = el.getBoundingClientRect();
                    // If the text field is reasonably sized and contains our element, use it
                    if (fieldRect.width > elRect.width * 1.5 || fieldRect.height > elRect.height * 1.5) {
                        target = textField;
                    }
                }
                
                // Apply box-shadow indicator
                target.setAttribute('data-click-target', 'true');
                target.dataset.originalBoxShadow = target.style.boxShadow || '';
                target.dataset.originalOutline = target.style.outline || '';
                target.dataset.originalPosition = target.style.position || '';
                target.dataset.originalZIndex = target.style.zIndex || '';
                target.dataset.originalOverflow = target.style.overflow || '';
                
                // Use outline instead of box-shadow for better visibility on list items
                // Outline is not clipped by parent overflow:hidden
                target.style.outline = '3px solid rgba(255, 0, 0, 0.9)';
                target.style.outlineOffset = '2px';
                target.style.boxShadow = '0 0 15px 5px rgba(255, 0, 0, 0.4)';
                
                // Ensure the element is visible above siblings
                const currentPosition = getComputedStyle(target).position;
                if (currentPosition === 'static') {
                    target.style.position = 'relative';
                }
                target.style.zIndex = '9999';
            }""",
            box_shadow,
        )

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
        """Remove click indicator from any marked elements and restore original styles."""
        self.page.evaluate("""
            // Remove the data attribute and restore original styles from any marked elements
            function restoreElement(el) {
                el.removeAttribute('data-click-target');
                // Restore all saved styles
                if (el.dataset.originalBoxShadow !== undefined) {
                    el.style.boxShadow = el.dataset.originalBoxShadow;
                    delete el.dataset.originalBoxShadow;
                } else {
                    el.style.boxShadow = '';
                }
                if (el.dataset.originalOutline !== undefined) {
                    el.style.outline = el.dataset.originalOutline;
                    el.style.outlineOffset = '';
                    delete el.dataset.originalOutline;
                } else {
                    el.style.outline = '';
                    el.style.outlineOffset = '';
                }
                if (el.dataset.originalPosition !== undefined) {
                    el.style.position = el.dataset.originalPosition;
                    delete el.dataset.originalPosition;
                }
                if (el.dataset.originalZIndex !== undefined) {
                    el.style.zIndex = el.dataset.originalZIndex;
                    delete el.dataset.originalZIndex;
                }
            }
            
            const marked = document.querySelectorAll('[data-click-target]');
            for (const el of marked) {
                restoreElement(el);
            }

            // Also traverse shadow roots to find any marked elements there
            function walkShadowRoots(root) {
                root.querySelectorAll('*').forEach(el => {
                    if (el.hasAttribute('data-click-target')) {
                        restoreElement(el);
                    }
                    if (el.shadowRoot) {
                        walkShadowRoots(el.shadowRoot);
                    }
                });
            }
            walkShadowRoots(document);

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
        _LOGGER.info("Capturing: %s", filename)

        png_path = self.output_dir / f"{filename}.png"
        self.page.screenshot(path=str(png_path))

        self.results.append(
            {
                "step": self.step_number,
                "name": name,
                "png": str(png_path),
            }
        )

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

    def add_another_entity(
        self, field_label: str, search_term: str, entity_name: str, *, capture_name: str | None = None
    ) -> None:
        """Add another entity to a multi-select field.

        For fields that accept multiple entities, an "Add entity" button appears after first selection.
        Uses the same HA dialog pattern as select_entity.
        """
        # Find the ha-selector containing this field
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")

        # Click the "Add entity" button within the selector
        add_btn = selector.get_by_role("button", name="Add entity")

        if capture_name:
            self._scroll_into_view(add_btn)
            self.capture(f"{capture_name}_before")
            self._capture_with_indicator(f"{capture_name}_add_btn", add_btn)

        add_btn.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

        # Wait for a dialog to appear - HA uses "Select option" as the dialog name
        dialog = self.page.get_by_role("dialog", name="Select option")
        dialog.wait_for(timeout=DEFAULT_TIMEOUT)

        if capture_name:
            self.capture(f"{capture_name}_dialog")

        # Fill the search textbox within the dialog
        search_input = dialog.get_by_role("textbox", name="Search")
        search_input.fill(search_term)
        self.page.wait_for_timeout(1000)  # Wait 1s for search results to populate

        if capture_name:
            self.capture(f"{capture_name}_search")

        # Click the matching item in the dialog's results
        # HA uses different selectors: listitem in some dialogs, ha-combo-box-item in others
        try:
            result_item = dialog.get_by_role("listitem").filter(has_text=entity_name).first
            if capture_name:
                self._scroll_into_view(result_item)
                self.capture(f"{capture_name}_select_before")
                self._capture_with_indicator(f"{capture_name}_select", result_item)
            result_item.click(timeout=1000)
        except Exception:
            # Fall back to ha-combo-box-item
            result_item = dialog.locator("ha-combo-box-item").filter(has_text=entity_name).first
            if capture_name:
                self._scroll_into_view(result_item)
                self.capture(f"{capture_name}_select_before")
                self._capture_with_indicator(f"{capture_name}_select", result_item)
            result_item.click(timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(SHORT_WAIT * 1000)

        if capture_name:
            self.capture(f"{capture_name}_result")

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
        """Close the element creation dialog.

        Home Assistant subentry flows typically show a success dialog after creation.
        We need to wait for the dialog to appear and then close it.
        """
        # Wait longer for the success dialog to appear after submit
        self.page.wait_for_timeout(MEDIUM_WAIT * 1000)

        # Try various button names that might appear
        for button_name in ["Finish", "OK", "Close", "Done"]:
            button = self.page.get_by_role("button", name=button_name)
            if button.count() > 0:
                _LOGGER.info("Found '%s' button - clicking to close dialog", button_name)
                if capture_name:
                    self._scroll_into_view(button)
                    self.capture(f"{capture_name}_before")
                    self._capture_with_indicator(f"{capture_name}_click", button)
                button.click(timeout=DEFAULT_TIMEOUT)
                break
        else:
            _LOGGER.info("No close button found - waiting for dialog to auto-close")
            if capture_name:
                self.capture(f"{capture_name}_auto_closed")

        # Wait for dialog to actually close
        try:
            self.page.wait_for_selector("dialog-data-entry-flow", state="hidden", timeout=5000)
            _LOGGER.info("Dialog closed successfully")
        except Exception:
            _LOGGER.warning("Dialog may still be open after timeout")
            # Take a screenshot to debug
            if capture_name:
                self.capture(f"{capture_name}_dialog_stuck")

        # Wait for Home Assistant to process the creation and update the UI
        self.page.wait_for_timeout(LONG_WAIT * 1000)


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

    # Search for our integration
    search_box = guide.page.get_by_role("textbox", name="Search for a brand name")
    search_box.fill("HAEO")
    guide.page.wait_for_timeout(LONG_WAIT * 1000)

    guide.capture("search_haeo")

    # Click on the HAEO integration result
    haeo_item = guide.page.locator("ha-integration-list-item", has_text="HAEO")
    guide._capture_with_indicator("select_haeo_click", haeo_item)
    haeo_item.click(timeout=DEFAULT_TIMEOUT)

    # Wait for the HAEO Setup dialog
    guide.page.wait_for_selector("text=HAEO Setup", timeout=DEFAULT_TIMEOUT)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("network_form")

    # Fill system name with capture
    guide.fill_textbox("System Name", NETWORK_NAME, capture_name="network_name")

    # Submit with capture
    guide.click_button("Submit", capture_name="network_submit")

    # Wait for the integration to be set up and navigate to the integration page
    guide.page.wait_for_timeout(LONG_WAIT * 1000)
    guide.page.wait_for_load_state("networkidle")

    # Navigate to the HAEO integration page to add elements
    guide.page.goto(f"{guide.url}/config/integrations/integration/haeo")
    guide.page.wait_for_load_state("networkidle")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    guide.capture("haeo_integration_page")

    _LOGGER.info("HAEO integration added")


def add_inverter(guide: SigenergyGuide) -> None:
    """Add Inverter element."""
    _LOGGER.info("Adding Inverter...")

    # Click the Inverter button in the toolbar with capture
    guide.click_button("Inverter", capture_name="inverter_add")

    # Wait for the dialog to appear
    guide.page.wait_for_selector("text=Inverter Configuration", timeout=DEFAULT_TIMEOUT)

    # Fill inverter name
    guide.fill_textbox("Inverter Name", "Inverter", capture_name="inverter_name")

    # Select AC Connection with capture
    guide.select_combobox_option("AC Connection", "Switchboard", capture_name="inverter_connection")

    # Select power sensors with capture
    guide.select_entity(
        "Max DC to AC Power", "max active power", "Sigen Plant Max Active Power", capture_name="inverter_dc_ac"
    )
    guide.select_entity(
        "Max AC to DC Power", "max active power", "Sigen Plant Max Active Power", capture_name="inverter_ac_dc"
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
    guide.page.wait_for_selector("text=Battery Configuration", timeout=DEFAULT_TIMEOUT)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    # Fill name with capture
    guide.fill_textbox("Battery Name", "Battery", capture_name="battery_name")

    # Select connection
    guide.select_combobox_option("Connection", "Inverter", capture_name="battery_connection")

    # Entity selections with captures
    guide.select_entity("Capacity", "rated energy", "Rated Energy Capacity", capture_name="battery_capacity")
    guide.select_entity(
        "State of Charge", "state of charge", "Battery State of Charge", capture_name="battery_soc"
    )
    guide.select_entity("Max Charging Power", "rated charging", "Rated Charging Power", capture_name="battery_charge")
    guide.select_entity(
        "Max Discharging Power", "rated discharging", "Rated Discharging Power", capture_name="battery_discharge"
    )

    # Optional fields (min/max charge, efficiency, early charge incentive) use defaults.
    # These only appear in step 2 if "HAEO Configurable" is selected in the entity picker.
    # Since we're using entity sensors, step 2 is skipped and defaults are applied.

    # Submit step 1
    guide.click_button("Submit", capture_name="battery_submit")

    # Wait for the async processing to complete - battery might auto-close
    guide.page.wait_for_timeout(LONG_WAIT * 1000)

    # Check if there's a step 2 "Battery Values" form or if we went straight to finish
    try:
        values_title = guide.page.locator("text=Battery Values")
        if values_title.count() > 0:
            _LOGGER.info("Battery step 2 (Values) detected - submitting")
            guide.capture("battery_values_form")
            guide.click_button("Submit", capture_name="battery_submit_step2")
            guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)
    except Exception:
        _LOGGER.info("No Battery Values step - proceeding to close")

    guide.close_element_dialog(capture_name="battery_close")

    _LOGGER.info("Battery added")


def add_solar(guide: SigenergyGuide) -> None:
    """Add Solar element with multiple forecast sensors."""
    _LOGGER.info("Adding Solar...")

    guide.click_button("Solar", capture_name="solar_add")

    guide.page.wait_for_selector("text=Solar Configuration", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Solar Name", "Solar", capture_name="solar_name")
    guide.select_combobox_option("Connection", "Inverter", capture_name="solar_connection")

    # First forecast sensor
    guide.select_entity(
        "Forecast", "east solar today", "East solar production forecast", capture_name="solar_forecast"
    )

    # Add the other three array forecasts
    guide.add_another_entity(
        "Forecast", "north solar today", "North solar production forecast", capture_name="solar_forecast2"
    )
    guide.add_another_entity(
        "Forecast", "south solar today", "South solar prediction forecast", capture_name="solar_forecast3"
    )
    guide.add_another_entity(
        "Forecast", "west solar today", "West solar production forecast", capture_name="solar_forecast4"
    )

    guide.click_button("Submit", capture_name="solar_submit")
    guide.close_element_dialog(capture_name="solar_close")

    _LOGGER.info("Solar added")


def add_grid(guide: SigenergyGuide) -> None:
    """Add Grid element."""
    _LOGGER.info("Adding Grid...")

    guide.click_button("Grid", capture_name="grid_add")

    guide.page.wait_for_selector("text=Grid Configuration", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Grid Name", "Grid", capture_name="grid_name")
    guide.select_combobox_option("Connection", "Switchboard", capture_name="grid_connection")

    # Import price with capture
    guide.select_entity(
        "Import Price", "general price", "Home - General Price", capture_name="grid_import_price"
    )
    guide.add_another_entity(
        "Import Price", "general forecast", "Home - General Forecast", capture_name="grid_import_price2"
    )

    # Export price
    guide.select_entity(
        "Export Price", "feed in price", "Home - Feed In Price", capture_name="grid_export_price"
    )
    guide.add_another_entity(
        "Export Price", "feed in forecast", "Home - Feed In Forecast", capture_name="grid_export_price2"
    )

    # Submit step 1 → moves to step 2 (values) for limit spinbuttons
    guide.click_button("Submit", capture_name="grid_step1_submit")

    # Step 2: Fill spinbuttons for import/export limits (pre-selected as configurable)
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)
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

    guide.page.wait_for_selector("text=Load Configuration", timeout=DEFAULT_TIMEOUT)

    guide.fill_textbox("Load Name", "Constant Load", capture_name="load_name")
    guide.select_combobox_option("Connection", "Switchboard", capture_name="load_connection")

    # For constant load, select the HAEO Configurable entity
    guide.select_entity("Forecast", "configurable", "Configurable Entity", capture_name="load_forecast")

    # Step 1 submit - triggers step 2 for configurable values
    guide.click_button("Submit", capture_name="load_submit_step1")
    guide.page.wait_for_timeout(MEDIUM_WAIT * 1000)

    # Step 2: Enter the constant load value
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


def run_guide(
    hass: LiveHomeAssistant,
    output_dir: Path,
    *,
    headless: bool = True,
    dark_mode: bool = False,
) -> list[dict[str, Any]]:
    """Run the complete Sigenergy guide.

    Args:
        hass: LiveHomeAssistant instance
        output_dir: Directory to save screenshots
        headless: Whether to run browser headlessly
        dark_mode: Whether to use dark theme

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
        hass.inject_auth(context, dark_mode=dark_mode)

        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            guide = SigenergyGuide(
                page=page,
                hass=hass,
                output_dir=output_dir,
                dark_mode=dark_mode,
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
