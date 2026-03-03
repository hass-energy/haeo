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
                self._capture_with_indicator("card", card)
                card.click()
                self.page.wait_for_load_state("networkidle")
                self._capture("integration_page")
        else:
            card.click()
            self.page.wait_for_load_state("networkidle")

    # endregion

    # region: Form Interactions

    def click_button(self, name: str) -> None:
        """Click a button by accessible name.

        Captures a screenshot with the target indicator before clicking.
        Does not capture a result screenshot — downstream actions (e.g.,
        wait_for_dialog) capture the resulting state when it is ready.
        """
        ctx = ScreenshotContext.current()

        button = self.page.get_by_role("button", name=name)
        button.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope(f"click_{name}"):
                self._scroll_and_capture(button)
                self._capture_with_indicator("target", button)
                button.click(timeout=DEFAULT_TIMEOUT)
                self.page.wait_for_load_state("domcontentloaded")
        else:
            button.click(timeout=DEFAULT_TIMEOUT)

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

        _LOGGER.info("Success dialog closed")

    def wait_for_dialog(self, title: str) -> None:
        """Wait for dialog with given title to appear and be fully rendered.

        Waits for an ha-dialog element with the open attribute set, filtering
        by title text. The open attribute is the reliable signal that the
        dialog has finished its internal visibility transition.
        """
        dialog = self.page.locator("ha-dialog[open]").filter(has_text=title)
        dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        self.page.wait_for_load_state("domcontentloaded")
        self._wait_for_stable_layout(dialog)
        self._capture("dialog_opened")

    def submit(self) -> None:
        """Click Submit button."""
        self.click_button("Submit")

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
        """Click the Add integration button."""
        add_btn = self.page.locator("ha-button").get_by_role("button", name="Add integration")
        add_btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope("add_integration"):
                self._capture("page")
                self._capture_with_indicator("button", add_btn)
                add_btn.click()
        else:
            add_btn.click()

    # endregion
