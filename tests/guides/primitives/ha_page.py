"""Low-level Home Assistant UI primitives.

This module contains primitives for interacting with the Home Assistant UI.
These may need updates when Home Assistant changes its frontend.

The HAPage class wraps a Playwright Page with HA-specific interactions
like entity pickers, dialogs, and screenshot capture with indicators.

Screenshots are automatically collected using the ScreenshotContext.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .capture import ScreenshotContext

if TYPE_CHECKING:
    from playwright.sync_api import Page

_LOGGER = logging.getLogger(__name__)

# Timeouts - kept tight since everything runs locally
DEFAULT_TIMEOUT = 2000  # 2 seconds max for UI interactions
SEARCH_TIMEOUT = 5000  # 5 seconds for entity search results

# Load JavaScript from external file
_JS_DIR = Path(__file__).parent / "js"
_CLICK_INDICATOR_JS = (_JS_DIR / "click_indicator.js").read_text()

# JavaScript to find the scroll container for a given element.
# HA dialogs scroll inside their own container, not the window.
_GET_SCROLL_TOP_JS = """
(el) => {
    let node = el;
    while (node) {
        if (node.scrollHeight > node.clientHeight + 1 && node.clientHeight > 0) {
            return node.scrollTop;
        }
        // Walk through shadow roots
        node = node.parentElement || (node.getRootNode && node.getRootNode()).host;
    }
    return window.scrollY;
}
"""


@dataclass
class HAPage:
    """Low-level Home Assistant page interactions.

    All methods automatically capture screenshots using the active ScreenshotContext.
    Screenshot names are built hierarchically from the context stack.
    """

    page: Page
    url: str

    # region: Screenshot Capture

    def _capture(self, step: str) -> None:
        """Capture screenshot with current context naming."""
        ctx = ScreenshotContext.current()
        if ctx:
            ctx.capture(self.page, step)

    def _capture_with_indicator(self, step: str, locator: Any) -> None:
        """Capture screenshot with click indicator on target element."""
        self._scroll_into_view(locator)
        self._show_click_indicator(locator)
        self._capture(step)
        self._remove_click_indicator()

    def _show_click_indicator(self, locator: Any) -> None:
        """Show click indicator overlay at target element."""
        self._remove_click_indicator()

        element = locator.element_handle(timeout=1000)
        if not element:
            return

        clickable_selector = (
            "button, [role='button'], [role='option'], [role='listitem'], a, "
            "ha-list-item, ha-combo-box-item, mwc-list-item, "
            "ha-md-list-item, md-item, "
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

    def _scroll_into_view(self, locator: Any) -> bool:
        """Scroll element into view if needed.

        Returns True if the page actually scrolled, False if the element
        was already visible.
        """
        element = locator.element_handle(timeout=DEFAULT_TIMEOUT)
        if not element:
            return False

        before = element.evaluate(_GET_SCROLL_TOP_JS)
        locator.scroll_into_view_if_needed(timeout=DEFAULT_TIMEOUT)
        after = element.evaluate(_GET_SCROLL_TOP_JS)
        return abs(after - before) > 1

    def _scroll_and_capture(self, locator: Any) -> None:
        """Scroll element into view and capture a screenshot if scrolling occurred."""
        scrolled = self._scroll_into_view(locator)
        if scrolled:
            self._capture("scrolled")

    def _wait_for_stable_layout(self, locator: Any) -> None:
        """Wait for an element's layout to stabilize across animation frames."""
        locator.evaluate("""
            (el) => new Promise((resolve) => {
                let lastRect = JSON.stringify(el.getBoundingClientRect());
                let stableFrames = 0;
                let totalFrames = 0;
                function check() {
                    totalFrames++;
                    if (totalFrames > 30) { resolve(); return; }
                    const rect = JSON.stringify(el.getBoundingClientRect());
                    if (rect === lastRect) {
                        stableFrames++;
                        if (stableFrames >= 3) { resolve(); return; }
                    } else {
                        stableFrames = 0;
                        lastRect = rect;
                    }
                    requestAnimationFrame(check);
                }
                requestAnimationFrame(check);
            })
        """)

    # endregion

    # region: Navigation

    def goto(self, path: str) -> None:
        """Navigate to a path within Home Assistant.

        Only used for the initial page load. All subsequent navigation
        should use click-based methods to demonstrate the real user flow.
        """
        full_url = f"{self.url}{path}" if path.startswith("/") else path
        self.page.goto(full_url)
        self.page.wait_for_load_state("networkidle")

    def wait_for_load(self) -> None:
        """Wait for page to finish loading."""
        self.page.wait_for_load_state("networkidle")

    def navigate_to_settings(self) -> None:
        """Navigate to Settings via sidebar click."""
        ctx = ScreenshotContext.current()
        settings = self.page.get_by_text("Settings")
        settings.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("navigate_settings"):
                self._capture("home")
                self._capture_with_indicator("sidebar", settings)
                settings.click()
                self.page.wait_for_load_state("networkidle")
                self._capture("settings_page")
        else:
            settings.click()
            self.page.wait_for_load_state("networkidle")

    def navigate_to_integrations(self) -> None:
        """Navigate to Devices & services from Settings page."""
        ctx = ScreenshotContext.current()
        ds = self.page.get_by_text("Devices & services")
        ds.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("navigate_integrations"):
                self._capture_with_indicator("settings_item", ds)
                ds.click()
                self.page.wait_for_load_state("networkidle")
        else:
            ds.click()
            self.page.wait_for_load_state("networkidle")

    def navigate_to_integration(self, name: str) -> None:
        """Navigate to a specific integration page by clicking its card."""
        ctx = ScreenshotContext.current()
        card = self.page.locator("ha-integration-card").filter(has_text=name)
        card.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("navigate_integration"):
                self._scroll_and_capture(card)
                # Target the inner ha-card which has the visible rounded corners
                inner_card = card.locator("ha-card")
                self._capture_with_indicator("card", inner_card)
                card.click()
                self.page.wait_for_load_state("networkidle")
                self._capture("integration_page")
        else:
            card.click()
            self.page.wait_for_load_state("networkidle")

    # endregion

    # region: Form Interactions

    def click_button(self, name: str, *, first: bool = False) -> None:
        """Click a button by accessible name.

        Captures a screenshot with the target indicator before clicking.
        Does not capture a result screenshot — downstream actions (e.g.,
        wait_for_dialog) capture the resulting state when it is ready.

        Args:
            name: Accessible name of the button to click.
            first: If True, use the first matching button when multiple
                buttons share the same accessible name (e.g., an add-subentry
                button and a gear icon on an existing subentry row).

        """
        ctx = ScreenshotContext.current()

        button = self.page.get_by_role("button", name=name, exact=True)
        if first:
            button = button.first
        button.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope(f"click_{name}"):
                self._scroll_and_capture(button)
                self._capture_with_indicator("target", button)
                button.click(timeout=DEFAULT_TIMEOUT)
                self.page.wait_for_load_state("domcontentloaded")
        else:
            button.click(timeout=DEFAULT_TIMEOUT)
            self.page.wait_for_load_state("domcontentloaded")

    def fill_textbox(self, name: str, value: str) -> None:
        """Fill a textbox by accessible name."""
        textbox = self.page.get_by_role("textbox", name=name)

        current_value = textbox.input_value(timeout=DEFAULT_TIMEOUT)
        if current_value == value:
            return

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"fill_{name}"):
                self._scroll_and_capture(textbox)
                self._capture_with_indicator("field", textbox)
                textbox.fill(value)
                self._capture("filled")
        else:
            textbox.fill(value)

    def fill_spinbutton(self, name: str, value: str) -> None:
        """Fill a spinbutton by accessible name."""
        spinbutton = self.page.get_by_role("spinbutton", name=name)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"fill_{name}"):
                self._scroll_and_capture(spinbutton)
                self._capture_with_indicator("field", spinbutton)
                spinbutton.clear()
                spinbutton.fill(value)
                self._capture("filled")
        else:
            spinbutton.clear()
            spinbutton.fill(value)

    def select_combobox(self, combobox_name: str, option_text: str) -> None:
        """Select option from combobox dropdown."""
        combobox = self.page.get_by_role("combobox", name=combobox_name)
        combobox.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"select_{combobox_name}"):
                self._scroll_and_capture(combobox)
                self._capture_with_indicator("dropdown", combobox)
                combobox.click()

                option = self.page.get_by_role("option", name=option_text)
                option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._scroll_into_view(option)
                self._capture_with_indicator("option", option)

                option.click()
                option.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
                self._capture("selected")
        else:
            combobox.click()
            option = self.page.get_by_role("option", name=option_text)
            option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            option.click()
            option.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

    def select_dropdown(self, label: str, option_text: str) -> None:
        """Select an option from a SelectSelector in DROPDOWN mode.

        HA renders SelectSelector DROPDOWN as ``ha-select`` wrapping
        ``ha-md-select-option`` items. Clicking the select element opens
        a menu of options.
        """
        # ha-selector-select wraps the ha-select component
        selector = self.page.locator("ha-selector-select").filter(has_text=label)
        selector.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        # The ha-select element is the clickable trigger
        ha_select = selector.locator("ha-select")
        ha_select.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"select_{label}"):
                self._scroll_and_capture(ha_select)
                self._capture_with_indicator("dropdown", ha_select)
                ha_select.click()

                option = self.page.get_by_role("option", name=option_text)
                option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._scroll_into_view(option)
                self._capture_with_indicator("option", option)

                option.click()
                self.page.wait_for_timeout(300)
                self._capture("selected")
        else:
            ha_select.click()
            option = self.page.get_by_role("option", name=option_text)
            option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            option.click()
            self.page.wait_for_timeout(300)

    # endregion

    # region: Sections

    def expand_section(self, section_name: str) -> None:
        """Expand a collapsed form section by clicking its header.

        Sections are rendered as ``ha-expansion-panel`` within ``ha-form-expandable``.
        If the panel is already expanded, this is a no-op.
        """
        panel = self.page.locator("ha-expansion-panel").filter(has_text=section_name)
        panel.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        # Check if already expanded by looking for the attribute
        if panel.get_attribute("expanded") is not None:
            return

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"expand_{section_name}"):
                self._scroll_and_capture(panel)
                self._capture_with_indicator("collapsed", panel)
                panel.click()
                self._capture("expanded")
        else:
            panel.click()

    # endregion

    # region: ChooseSelector

    def choose_select_option(self, field_label: str, choice: str) -> None:
        """Select a choice in a ChooseSelector field (Entity/Constant/None).

        ChooseSelector renders toggle buttons via ``ha-button-toggle-group``.
        Each button shows a choice label (e.g., "Entity", "Constant", "None").
        """
        choose = self.page.locator("ha-selector-choose").filter(has_text=field_label)
        choose.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        button = choose.get_by_role("button", name=choice)
        button.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"choose_{field_label}_{choice}"):
                self._scroll_and_capture(button)
                self._capture_with_indicator("button", button)
                button.click(timeout=DEFAULT_TIMEOUT)
                self._capture("selected")
        else:
            button.click(timeout=DEFAULT_TIMEOUT)

    def choose_entity(
        self,
        field_label: str,
        search_term: str,
        entity_name: str,
    ) -> None:
        """Select an entity within a ChooseSelector field.

        Assumes the "Entity" choice is already active (the default for entity-mode fields).
        The nested entity picker uses the same combo-box-item -> dialog -> search pattern.
        """
        choose = self.page.locator("ha-selector-choose").filter(has_text=field_label)
        choose.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        picker = choose.locator("ha-combo-box-item").first
        picker.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"entity_{field_label}"):
                self._scroll_and_capture(picker)
                self._capture_with_indicator("picker", picker)

                picker.click()

                dialog = self.page.get_by_role("dialog", name="Select option")
                dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

                search_input = dialog.get_by_role("textbox", name="Search")
                search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture_with_indicator("search_box", search_input)

                search_input.fill(search_term)

                result_item = dialog.locator(f":text('{entity_name}')").first
                result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)
                self._capture("search_results")
                self._scroll_into_view(result_item)
                self._capture_with_indicator("select", result_item)

                result_item.click(timeout=DEFAULT_TIMEOUT)
                dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
                self._capture("selected")
        else:
            self._select_entity_no_capture(picker, search_term, entity_name)

    def choose_add_entity(
        self,
        field_label: str,
        search_term: str,
        entity_name: str,
    ) -> None:
        """Add another entity to a multi-select ChooseSelector field."""
        choose = self.page.locator("ha-selector-choose").filter(has_text=field_label)
        add_btn = choose.get_by_role("button", name="Add entity")
        add_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"add_entity_{field_label}"):
                self._scroll_and_capture(add_btn)
                self._capture_with_indicator("add_button", add_btn)

                add_btn.click(timeout=DEFAULT_TIMEOUT)

                dialog = self.page.get_by_role("dialog", name="Select option")
                dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

                search_input = dialog.get_by_role("textbox", name="Search")
                search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture_with_indicator("search_box", search_input)

                search_input.fill(search_term)

                result_item = dialog.locator(f":text('{entity_name}')").first
                result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)
                self._capture("search_results")
                self._scroll_into_view(result_item)
                self._capture_with_indicator("select", result_item)

                result_item.click(timeout=DEFAULT_TIMEOUT)
                dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
                self._capture("selected")
        else:
            add_btn.click(timeout=DEFAULT_TIMEOUT)
            dialog = self.page.get_by_role("dialog", name="Select option")
            dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            self._select_entity_no_capture(
                dialog.get_by_role("textbox", name="Search"),
                search_term,
                entity_name,
                already_in_dialog=True,
            )

    def choose_constant(self, field_label: str, value: str) -> None:
        """Fill a constant value within a ChooseSelector field.

        Assumes the "Constant" choice is already active. The nested NumberSelector
        renders as a spinbutton.
        """
        choose = self.page.locator("ha-selector-choose").filter(has_text=field_label)
        choose.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        spinbutton = choose.get_by_role("spinbutton")
        spinbutton.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"constant_{field_label}"):
                self._scroll_and_capture(spinbutton)
                self._capture_with_indicator("field", spinbutton)
                spinbutton.clear()
                spinbutton.fill(value)
                self._capture("filled")
        else:
            spinbutton.clear()
            spinbutton.fill(value)

    # endregion

    def _select_entity_no_capture(
        self,
        picker_or_search: Any,
        search_term: str,
        entity_name: str,
        *,
        already_in_dialog: bool = False,
    ) -> None:
        """Entity selection without screenshots."""
        if not already_in_dialog:
            picker_or_search.click()
            dialog = self.page.get_by_role("dialog", name="Select option")
            dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            search_input = dialog.get_by_role("textbox", name="Search")
        else:
            search_input = picker_or_search
            dialog = self.page.get_by_role("dialog", name="Select option")

        search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        search_input.fill(search_term)

        result_item = dialog.locator(f":text('{entity_name}')").first
        result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)
        result_item.click(timeout=DEFAULT_TIMEOUT)
        dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

    # endregion

    # region: Entity Pickers (standalone EntitySelector fields)

    def select_entity(
        self,
        field_label: str,
        search_term: str,
        entity_name: str,
    ) -> None:
        """Select an entity from a standalone EntitySelector field.

        EntitySelector fields render within shadow DOM of ha-form elements.
        Clicking the ha-combo-box-item trigger opens an inline dropdown
        with a search box and entity list (not a dialog).
        """
        label = self.page.locator(f"text='{field_label}'").first
        label.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        # Find the ha-combo-box-item nearest to this label by bounding box
        all_pickers = self.page.locator("ha-combo-box-item")
        label_box = label.bounding_box()
        picker = None

        if label_box:
            count = all_pickers.count()
            best_y_diff = float("inf")
            for i in range(count):
                item = all_pickers.nth(i)
                item_box = item.bounding_box()
                if item_box and item_box["y"] >= label_box["y"]:
                    y_diff = item_box["y"] - label_box["y"]
                    if y_diff < best_y_diff:
                        best_y_diff = y_diff
                        picker = item

        if picker is None:
            msg = f"Could not find entity picker for '{field_label}'"
            raise RuntimeError(msg)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"select_entity_{field_label}"):
                self._scroll_and_capture(picker)
                self._capture_with_indicator("picker", picker)

                picker.click()

                search_input = self.page.locator("vaadin-combo-box-overlay input").first
                search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture_with_indicator("search_box", search_input)

                search_input.fill(search_term)

                result_item = self.page.locator(f"ha-combo-box-item:has-text('{entity_name}')").first
                result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)
                self._capture("search_results")
                self._capture_with_indicator("select", result_item)

                result_item.click(timeout=DEFAULT_TIMEOUT)
                self.page.wait_for_timeout(500)
                self._capture("selected")
        else:
            picker.click()
            search_input = self.page.locator("vaadin-combo-box-overlay input").first
            search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            search_input.fill(search_term)
            result_item = self.page.locator(f"ha-combo-box-item:has-text('{entity_name}')").first
            result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)
            result_item.click(timeout=DEFAULT_TIMEOUT)
            self.page.wait_for_timeout(500)

    # endregion

    # region: Dialogs

    def close_element_dialog(self) -> None:
        """Close element creation success dialog.

        Captures the success dialog state (showing Skip and Finish buttons)
        before indicating and clicking Finish.
        """
        button = self.page.get_by_role("button", name="Finish")
        button.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope("finish_dialog"):
                self._capture("dialog")
                self._capture_with_indicator("button", button)
                button.click(timeout=DEFAULT_TIMEOUT)
                button.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
                self._capture("result")
        else:
            button.click(timeout=DEFAULT_TIMEOUT)
            button.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
            self.page.wait_for_timeout(500)

        _LOGGER.info("Dialog closed successfully")

    def close_success_dialog(self) -> None:
        """Close the config flow success dialog shown after creating an entry.

        HA shows a success dialog with area selection and a Finish button
        after a config flow creates an entry. The dialog only appears after
        the POST response is received (entry setup runs inline in the handler).
        Waiting for this dialog prevents navigating away while the entry
        setup is still running.
        """
        button = self.page.get_by_role("button", name="Finish")
        button.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope("success_dialog"):
                self._capture("dialog")
                self._capture_with_indicator("finish_button", button)
                button.click(timeout=DEFAULT_TIMEOUT)
                button.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
                self._capture("result")
        else:
            button.click(timeout=DEFAULT_TIMEOUT)
            button.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
            self.page.wait_for_timeout(500)

        _LOGGER.info("Success dialog closed")

    def wait_for_dialog(self, title: str) -> None:
        """Wait for dialog with given title to appear and be fully rendered.

        Uses state="attached" because ha-dialog is a Shadow DOM component
        whose internal visibility transitions aren't detected by Playwright's
        visibility checks. The [open] attribute selector ensures we only
        match once the dialog has finished its internal transition.
        """
        dialog = self.page.locator("ha-dialog[open]").filter(has_text=title)
        dialog.wait_for(state="attached", timeout=SEARCH_TIMEOUT)
        self.page.wait_for_load_state("domcontentloaded")
        self._wait_for_stable_layout(dialog)
        self._capture("dialog_opened")

    def submit(self) -> None:
        """Click Submit button."""
        self.click_button("Submit")

    def select_list_option(self, option_text: str) -> None:
        """Select an option from a SelectSelector in LIST mode.

        LIST mode renders as a group of radio-style list items.
        Clicking the list item container doesn't always toggle the radio
        input, so we target the radio button by its value or the list
        item's inner interactive element.
        """
        ctx = ScreenshotContext.current()
        option = self.page.get_by_role("radio", name=option_text)
        option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope(f"select_list_{option_text}"):
                self._scroll_and_capture(option)
                self._capture_with_indicator("option", option)
                option.click(timeout=DEFAULT_TIMEOUT)
                self._capture("selected")
        else:
            option.click(timeout=DEFAULT_TIMEOUT)

    def toggle_switch(self, name: str) -> None:
        """Toggle a switch/checkbox by accessible name.

        BooleanSelector fields render as ``ha-switch`` toggle elements.
        """
        switch = self.page.locator("ha-switch").filter(has_text=name)
        switch.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"toggle_{name}"):
                self._scroll_and_capture(switch)
                self._capture_with_indicator("switch", switch)
                switch.click(timeout=DEFAULT_TIMEOUT)
                self._capture("toggled")
        else:
            switch.click(timeout=DEFAULT_TIMEOUT)

    # endregion

    # region: Integration Search

    def search_integration(self, integration_name: str) -> None:
        """Search for and select integration from add dialog."""
        search_box = self.page.get_by_role("textbox", name="Search for a brand name")
        search_box.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        # Wait for brand images in the dialog to load before screenshots
        dialog = self.page.locator("ha-dialog")
        self._wait_for_images(dialog)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope("search_integration"):
                self._capture("dialog")
                self._capture_with_indicator("search_box", search_box)

                search_box.click()
                search_box.fill(integration_name)

                item = self.page.locator("ha-integration-list-item", has_text=integration_name)
                item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                # Wait for brand images to load
                self._wait_for_images(item)
                self._capture("results")
                self._capture_with_indicator("select", item)

                item.click(timeout=DEFAULT_TIMEOUT)
        else:
            search_box.click()
            search_box.fill(integration_name)
            item = self.page.locator("ha-integration-list-item", has_text=integration_name)
            item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            item.click(timeout=DEFAULT_TIMEOUT)

    def _wait_for_images(self, locator: Any) -> None:
        """Wait for all images within a locator to finish loading.

        Traverses shadow DOM boundaries to find images inside custom elements.
        Returns after all images load or after a 2 second timeout.
        """
        locator.evaluate("""
            (el) => {
                function findImages(root) {
                    const imgs = [...root.querySelectorAll('img')];
                    for (const child of root.querySelectorAll('*')) {
                        if (child.shadowRoot) {
                            imgs.push(...findImages(child.shadowRoot));
                        }
                    }
                    return imgs;
                }
                const imgs = findImages(el.shadowRoot || el);
                return Promise.race([
                    Promise.all(
                        imgs.map(img => {
                            if (!img.src || (img.complete && img.naturalWidth > 0))
                                return Promise.resolve();
                            return new Promise(resolve => {
                                img.addEventListener('load', resolve, { once: true });
                                img.addEventListener('error', resolve, { once: true });
                            });
                        })
                    ),
                    new Promise(resolve => setTimeout(resolve, 2000))
                ]);
            }
        """)

    def click_add_integration(self) -> None:
        """Click the Add integration FAB on the integrations list page."""
        add_btn = self.page.locator("ha-fab").get_by_role("button", name="Add integration")
        add_btn.wait_for(state="visible", timeout=SEARCH_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope("add_integration"):
                self._capture("page")
                self._capture_with_indicator("button", add_btn)
                add_btn.click()
        else:
            add_btn.click()

    # endregion

    # region: Calendar

    def navigate_to_calendar(self) -> None:
        """Navigate to Calendar page via sidebar."""
        ctx = ScreenshotContext.current()
        calendar_link = self.page.get_by_text("Calendar", exact=True)
        calendar_link.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("navigate_calendar"):
                self._capture_with_indicator("sidebar", calendar_link)
                calendar_link.click()
                self.page.wait_for_load_state("networkidle")
                self._capture("calendar_page")
        else:
            calendar_link.click()
            self.page.wait_for_load_state("networkidle")

    def create_calendar_event(
        self,
        *,
        title: str,
        location: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        recurrence: str | None = None,
    ) -> None:
        """Create a calendar event using the HA calendar UI.

        Opens the event creation dialog, fills in details, and saves.
        Assumes we're already on the Calendar page.

        Args:
            title: Event title/summary.
            location: Event location (optional).
            start_time: Start time in HH:MM format (optional).
            end_time: End time in HH:MM format (optional).
            recurrence: Recurrence rule label (e.g., "Weekly") or None.

        """
        ctx = ScreenshotContext.current()

        # Click the add event FAB
        add_btn = self.page.locator("ha-fab").first
        add_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("create_event"):
                self._capture_with_indicator("add_button", add_btn)
                add_btn.click()
                self.page.wait_for_load_state("domcontentloaded")

                # Wait for the event dialog
                dialog = self.page.locator("ha-dialog[open]")
                dialog.wait_for(state="attached", timeout=DEFAULT_TIMEOUT)
                self._wait_for_stable_layout(dialog)
                self._capture("event_dialog")

                # Fill title
                title_input = dialog.get_by_role("textbox", name="Title")
                title_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture_with_indicator("title_field", title_input)
                title_input.fill(title)
                self._capture("title_filled")

                if location:
                    location_input = dialog.get_by_role("textbox", name="Location")
                    location_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                    self._capture_with_indicator("location_field", location_input)
                    location_input.fill(location)
                    self._capture("location_filled")

                self._fill_event_times(dialog, start_time, end_time)

                if recurrence:
                    self._set_event_recurrence(dialog, recurrence)

                # Save the event
                save_btn = dialog.locator("ha-button[slot='primaryAction']").first
                save_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                # Use the inner button for proper border-radius highlighting
                inner_btn = save_btn.locator("button").first
                if inner_btn.is_visible(timeout=500):
                    self._scroll_into_view(inner_btn)
                    self._capture_with_indicator("save_button", inner_btn)
                else:
                    self._scroll_into_view(save_btn)
                    self._capture_with_indicator("save_button", save_btn)
                save_btn.click()
                dialog.wait_for(state="hidden", timeout=SEARCH_TIMEOUT)
                self.page.wait_for_timeout(500)
                self._capture("event_saved")
        else:
            add_btn.click()
            dialog = self.page.locator("ha-dialog[open]")
            dialog.wait_for(state="attached", timeout=DEFAULT_TIMEOUT)
            title_input = dialog.get_by_role("textbox", name="Title")
            title_input.fill(title)
            if location:
                location_input = dialog.get_by_role("textbox", name="Location")
                location_input.fill(location)
            self._fill_event_times(dialog, start_time, end_time)
            if recurrence:
                self._set_event_recurrence(dialog, recurrence)
            save_btn = dialog.locator("ha-button[slot='primaryAction']").first
            save_btn.click()
            dialog.wait_for(state="hidden", timeout=SEARCH_TIMEOUT)

    def _fill_event_times(
        self,
        dialog: Any,
        start_time: str | None,
        end_time: str | None,
    ) -> None:
        """Fill start and end times in the event dialog.

        HA's event dialog defaults to all-day events. We need to
        uncheck the all-day toggle to reveal time fields, then fill
        the hour, minute, and AM/PM fields by clicking into them.

        Times are specified in 24-hour format (e.g. "08:00", "17:30").
        """
        ctx = ScreenshotContext.current()

        # Toggle off all-day if we're setting specific times
        if start_time or end_time:
            all_day_toggle = dialog.locator("ha-formfield").filter(has_text="All day")
            all_day_toggle.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            switch = all_day_toggle.locator("ha-switch")
            is_checked = switch.evaluate("(el) => el.checked === true")
            if is_checked:
                if ctx:
                    self._capture_with_indicator("all_day_toggle", all_day_toggle)
                all_day_toggle.click()
                self.page.wait_for_timeout(500)

        time_inputs = dialog.locator("ha-time-input")

        if start_time and time_inputs.count() >= 1:
            self._fill_single_time(time_inputs.first, start_time, "start_time")

        if end_time and time_inputs.count() >= 2:
            self._fill_single_time(time_inputs.nth(1), end_time, "end_time")

    def _fill_single_time(
        self,
        time_input: Any,
        time_value: str,
        screenshot_prefix: str,
    ) -> None:
        """Fill a single ha-time-input by clicking into hh/mm fields and setting AM/PM.

        Args:
            time_input: The ha-time-input locator.
            time_value: Time in 24-hour format (e.g. "08:00", "17:30").
            screenshot_prefix: Name prefix for screenshots.

        """
        ctx = ScreenshotContext.current()
        hour_24, minute = (int(p) for p in time_value.split(":"))

        # Convert 24h to 12h format
        if hour_24 == 0:
            hour_12, period = 12, "AM"
        elif hour_24 < 12:
            hour_12, period = hour_24, "AM"
        elif hour_24 == 12:
            hour_12, period = 12, "PM"
        else:
            hour_12, period = hour_24 - 12, "PM"

        # HA's ha-time-input renders input fields inside shadow DOM.
        hour_field = time_input.locator("input").first
        minute_field = time_input.locator("input").nth(1)

        # Set AM/PM first to avoid HA auto-adjusting end time
        # when the period changes mid-edit.
        period_select = time_input.locator("ha-select").first
        current_period = period_select.evaluate("(el) => el.value || el.textContent.trim().split('\\n')[0].trim()")
        if current_period != period:
            period_select.click()
            option = self.page.get_by_role("option", name=period)
            option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            if ctx:
                self._capture_with_indicator(f"{screenshot_prefix}_period", option)
            option.click()
            self.page.wait_for_timeout(300)

        # Fill hour
        hour_field.click()
        hour_field.fill(str(hour_12))
        self.page.wait_for_timeout(200)
        if ctx:
            self._capture_with_indicator(f"{screenshot_prefix}_hour", hour_field)

        # Fill minute
        minute_field.click()
        minute_field.fill(f"{minute:02d}")
        self.page.wait_for_timeout(200)
        if ctx:
            self._capture_with_indicator(f"{screenshot_prefix}_minute", minute_field)

    def _set_event_recurrence(self, dialog: Any, recurrence: str) -> None:
        """Set event recurrence in the event dialog.

        Args:
            dialog: The event dialog locator.
            recurrence: The recurrence label (e.g., "Weekly").

        """
        ctx = ScreenshotContext.current()

        repeat_selector = dialog.locator("ha-select").filter(has_text="repeat")
        repeat_selector.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            self._capture_with_indicator("recurrence_selector", repeat_selector)
        repeat_selector.click()

        option = self.page.get_by_role("option", name=recurrence)
        option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        if ctx:
            self._capture_with_indicator("recurrence_option", option)
        option.click()
        self.page.wait_for_timeout(300)

        if ctx:
            self._capture("recurrence_set")

    # endregion
