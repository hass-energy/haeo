"""Low-level Home Assistant UI primitives.

This module contains primitives for interacting with the Home Assistant UI.
These may need updates when Home Assistant changes its frontend.

The HAPage class wraps a Playwright Page with HA-specific interactions
like entity pickers, dialogs, and screenshot capture with indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

_LOGGER = logging.getLogger(__name__)

# Timeouts
DEFAULT_TIMEOUT = 5000  # 5 seconds max
SEARCH_TIMEOUT = 10000  # 10 seconds for search results

# JavaScript for click indicator overlay (inline to avoid file loading)
_CLICK_INDICATOR_JS = """
(el, clickableSelector) => {
  if (el.focus) { try { el.focus(); } catch (e) {} }

  let target = el;
  const minSize = 20;
  const rect = el.getBoundingClientRect();

  if (rect.width < minSize || rect.height < minSize) {
    const clickableParent = el.closest(clickableSelector);
    if (clickableParent) target = clickableParent;
  }

  const mdcTextField = el.closest("label.mdc-text-field");
  if (mdcTextField) target = mdcTextField;

  const comboBoxRow = el.closest(".combo-box-row");
  if (comboBoxRow) target = comboBoxRow;

  const comboBoxItem = el.closest("ha-combo-box-item");
  if (comboBoxItem) {
    const row = comboBoxItem.closest(".combo-box-row");
    target = row || comboBoxItem;
  }

  const entityListItem = el.closest(
    "ha-list-item, mwc-list-item, md-list-item, " + '[role="listitem"], [role="option"]'
  );
  if (entityListItem) {
    const listItemParent = entityListItem.closest("ha-list-item, mwc-list-item, md-list-item, md-item");
    target = listItemParent || entityListItem;
  }

  const haListItem = el.closest("ha-list-item");
  if (haListItem) target = haListItem;

  const mdItem = el.closest("md-item");
  if (mdItem) target = mdItem;

  const integrationItem = el.closest("ha-integration-list-item");
  if (integrationItem) target = integrationItem;

  const roleItem = el.closest('[role="listitem"], [role="option"]');
  if (roleItem) {
    const haWrapper = roleItem.closest("ha-list-item, md-item, mwc-list-item, .combo-box-row");
    target = haWrapper || roleItem;
  }

  const targetRect = target.getBoundingClientRect();
  const computedStyle = getComputedStyle(target);
  const borderRadius = computedStyle.borderRadius || "0px";

  const overlay = document.createElement("div");
  overlay.id = "click-indicator-overlay";
  overlay.setAttribute("popover", "manual");
  overlay.style.cssText = `
    position: fixed;
    left: ${targetRect.left - 3}px;
    top: ${targetRect.top - 3}px;
    width: ${targetRect.width + 6}px;
    height: ${targetRect.height + 6}px;
    border: 3px solid rgba(255, 0, 0, 0.9);
    border-radius: ${borderRadius};
    box-shadow: 0 0 15px 5px rgba(255, 0, 0, 0.4);
    pointer-events: none;
    z-index: 2147483647;
    margin: 0; padding: 0;
    background: transparent;
    box-sizing: border-box;
  `;
  document.body.appendChild(overlay);
  try { overlay.showPopover(); } catch (e) {}
}
"""


@dataclass
class HAPage:
    """Low-level Home Assistant page interactions.

    Wraps a Playwright Page with HA-specific UI primitives for:
    - Screenshot capture with click indicators
    - Form interactions (textbox, spinbutton, combobox)
    - Entity picker dialogs
    - Dialog management
    """

    page: Page
    url: str
    output_dir: Path
    step_number: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)

    # region: Screenshot Capture

    def capture(self, name: str) -> None:
        """Capture PNG screenshot of current page state."""
        self.step_number += 1
        filename = f"{self.step_number:02d}_{name}"

        # Log visible text for debugging
        visible_text = self.page.locator("body").inner_text(timeout=1000)
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

    def capture_with_indicator(self, name: str, locator: Any) -> None:
        """Capture screenshot with click indicator on target element."""
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

    def _show_click_indicator(self, locator: Any) -> None:
        """Show click indicator overlay at target element."""
        self._remove_click_indicator()

        element = locator.element_handle(timeout=1000)
        if not element:
            return

        clickable_selector = (
            "button, [role='button'], [role='option'], [role='listitem'], a, "
            "ha-list-item, ha-combo-box-item, mwc-list-item, md-item, "
            "ha-button, ha-icon-button, .mdc-text-field, ha-textfield, "
            "input, select, ha-select, ha-integration-list-item"
        )

        element.evaluate(_CLICK_INDICATOR_JS, clickable_selector)

    def _remove_click_indicator(self) -> None:
        """Remove click indicator overlay."""
        self.page.evaluate("""
            const overlay = document.getElementById('click-indicator-overlay');
            if (overlay) {
                try { overlay.hidePopover(); } catch (e) {}
                overlay.remove();
            }
        """)

    def _scroll_into_view(self, locator: Any) -> None:
        """Scroll element into view."""
        locator.scroll_into_view_if_needed(timeout=DEFAULT_TIMEOUT)

    # endregion

    # region: Navigation

    def goto(self, path: str) -> None:
        """Navigate to a path within Home Assistant."""
        full_url = f"{self.url}{path}" if path.startswith("/") else path
        self.page.goto(full_url)
        self.page.wait_for_load_state("networkidle")

    def wait_for_load(self) -> None:
        """Wait for page to finish loading."""
        self.page.wait_for_load_state("networkidle")

    # endregion

    # region: Form Interactions

    def click_button(self, name: str, *, capture: bool = False) -> None:
        """Click a button by accessible name."""
        button = self.page.get_by_role("button", name=name)
        button.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self._scroll_into_view(button)
            self.capture(f"{name}_before")
            self.capture_with_indicator(f"{name}_click", button)

        button.click(timeout=DEFAULT_TIMEOUT)

        if capture:
            self.page.wait_for_load_state("domcontentloaded")
            self.capture(f"{name}_result")

    def fill_textbox(self, name: str, value: str, *, capture: bool = False) -> None:
        """Fill a textbox by accessible name."""
        textbox = self.page.get_by_role("textbox", name=name)

        current_value = textbox.input_value(timeout=DEFAULT_TIMEOUT)
        if current_value == value:
            return

        if capture:
            self._scroll_into_view(textbox)
            self.capture(f"{name}_before")
            self.capture_with_indicator(f"{name}_field", textbox)

        textbox.fill(value)

        if capture:
            self.capture(f"{name}_filled")

    def fill_spinbutton(self, name: str, value: str, *, capture: bool = False) -> None:
        """Fill a spinbutton by accessible name."""
        spinbutton = self.page.get_by_role("spinbutton", name=name)

        if capture:
            self._scroll_into_view(spinbutton)
            self.capture(f"{name}_before")
            self.capture_with_indicator(f"{name}_field", spinbutton)

        spinbutton.clear()
        spinbutton.fill(value)

        if capture:
            self.capture(f"{name}_filled")

    def select_combobox(self, combobox_name: str, option_text: str, *, capture: bool = False) -> None:
        """Select option from combobox dropdown."""
        combobox = self.page.get_by_role("combobox", name=combobox_name)
        combobox.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self._scroll_into_view(combobox)
            self.capture(f"{combobox_name}_before")
            self.capture_with_indicator(f"{combobox_name}_dropdown", combobox)

        combobox.click()

        option = self.page.get_by_role("option", name=option_text)
        option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self._scroll_into_view(option)
            self.capture_with_indicator(f"{combobox_name}_option", option)

        option.click()
        option.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture(f"{combobox_name}_selected")

    # endregion

    # region: Entity Picker

    def select_entity(
        self,
        field_label: str,
        search_term: str,
        entity_name: str,
        *,
        capture: bool = False,
    ) -> None:
        """Select entity from HA entity picker dialog."""
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")
        picker = selector.locator("ha-combo-box-item").first
        picker.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self._scroll_into_view(picker)
            self.capture(f"{field_label}_before")
            self.capture_with_indicator(f"{field_label}_picker", picker)

        picker.click()

        dialog = self.page.get_by_role("dialog", name="Select option")
        dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        search_input = dialog.get_by_role("textbox", name="Search")
        search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture_with_indicator(f"{field_label}_search_box", search_input)

        search_input.fill(search_term)

        result_item = dialog.locator(f":text('{entity_name}')").first
        result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        if capture:
            self.capture(f"{field_label}_search")
            self._scroll_into_view(result_item)
            self.capture_with_indicator(f"{field_label}_select", result_item)

        result_item.click(timeout=DEFAULT_TIMEOUT)
        dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture(f"{field_label}_result")

    def add_another_entity(
        self,
        field_label: str,
        search_term: str,
        entity_name: str,
        *,
        capture: bool = False,
    ) -> None:
        """Add another entity to multi-select field."""
        selector = self.page.locator(f"ha-selector:has-text('{field_label}')")
        add_btn = selector.get_by_role("button", name="Add entity")
        add_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self._scroll_into_view(add_btn)
            self.capture(f"{field_label}_add_before")
            self.capture_with_indicator(f"{field_label}_add_btn", add_btn)

        add_btn.click(timeout=DEFAULT_TIMEOUT)

        dialog = self.page.get_by_role("dialog", name="Select option")
        dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        search_input = dialog.get_by_role("textbox", name="Search")
        search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture_with_indicator(f"{field_label}_add_search", search_input)

        search_input.fill(search_term)

        result_item = dialog.locator(f":text('{entity_name}')").first
        result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        if capture:
            self.capture(f"{field_label}_add_search_results")
            self._scroll_into_view(result_item)
            self.capture_with_indicator(f"{field_label}_add_select", result_item)

        result_item.click(timeout=DEFAULT_TIMEOUT)
        dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture(f"{field_label}_add_result")

    # endregion

    # region: Dialogs

    def close_element_dialog(self, *, capture: bool = False) -> None:
        """Close element creation success dialog."""
        button = self.page.get_by_role("button", name="Finish")
        button.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        if capture:
            self._scroll_into_view(button)
            self.capture("dialog_finish_before")
            self.capture_with_indicator("dialog_finish_click", button)

        button.click(timeout=DEFAULT_TIMEOUT)
        button.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
        _LOGGER.info("Dialog closed successfully")

    def wait_for_dialog(self, title: str) -> None:
        """Wait for dialog with given title to appear."""
        dialog = self.page.get_by_title(title)
        dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

    def submit(self, *, capture: bool = False) -> None:
        """Click Submit button."""
        self.click_button("Submit", capture=capture)

    # endregion

    # region: Integration Search

    def search_integration(self, integration_name: str, *, capture: bool = False) -> None:
        """Search for and select integration from add dialog."""
        search_box = self.page.get_by_role("textbox", name="Search for a brand name")
        search_box.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture("add_integration_dialog")
            self.capture_with_indicator("search_box_click", search_box)

        search_box.click()
        search_box.fill(integration_name)

        item = self.page.locator("ha-integration-list-item", has_text=integration_name)
        item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture(f"search_{integration_name.lower()}")
            self.capture_with_indicator(f"select_{integration_name.lower()}", item)

        item.click(timeout=DEFAULT_TIMEOUT)

    def click_add_integration(self, *, capture: bool = False) -> None:
        """Click the Add integration button."""
        add_btn = self.page.locator("ha-button").get_by_role("button", name="Add integration")
        add_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if capture:
            self.capture("integrations_page")
            self.capture_with_indicator("add_integration_click", add_btn)

        add_btn.click()

    # endregion
