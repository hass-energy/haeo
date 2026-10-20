"""Low-level Home Assistant UI primitives.

This module contains primitives for interacting with the Home Assistant UI.
These may need updates when Home Assistant changes its frontend.

The HAPage class wraps a Playwright Page with HA-specific interactions
like entity pickers, dialogs, and screenshot capture with indicators.

Screenshots are automatically collected using the ScreenshotContext.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import logging
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

from tools.live_hass import LiveHomeAssistant

from .capture import SETTLE_DEADLINE_MS, ScreenshotContext, wait_until_settled

_LOGGER = logging.getLogger(__name__)

# Timeouts - kept tight since everything runs locally
DEFAULT_TIMEOUT = 2000  # 2 seconds max for UI interactions
SEARCH_TIMEOUT = 5000  # 5 seconds for entity search results

# Load JavaScript from external file
_JS_DIR = Path(__file__).parent / "js"
_CLICK_INDICATOR_JS = (_JS_DIR / "click_indicator.js").read_text()

# Bring the frontend up to date with Home Assistant. Home Assistant answers a
# connection's messages in order, so once a ping returns, every update it
# pushed before has been handled. The entity and device registries are then
# refetched, since the frontend debounces their change notices on the leading
# edge and can drop the later ones of a burst.
_SYNC_FRONTEND_JS = """
async () => {
    const connection = document.querySelector('home-assistant').hass.connection;
    await connection.ping();
    const registries = [connection._entityRegistry, connection._dr].filter((registry) => registry !== undefined);
    await Promise.all(registries.map((registry) => registry.refresh()));
}
"""

# Make every virtualized list in a dialog measure its rows again, failing after
# the deadline if one never lays them out end to end. lit-virtualizer measures
# rows as they first render, which in a dialog can be while the dialog is still
# scaled down for its opening animation. A transform never fires the
# ResizeObserver it relies on, so it keeps placing rows by those shrunken
# heights. Narrowing each list by a pixel and back resizes its rows, so it
# measures them again; the promise resolves once every list's rows sit end to
# end at their full heights.
_REMEASURE_LISTS_JS = """
async (dialog, deadlineMs) => {
    const deadline = performance.now() + deadlineMs;
    const frame = () => new Promise((resolve) => requestAnimationFrame(() => resolve()));
    const lists = [];
    const visit = (root) => {
        for (const el of root.querySelectorAll('*')) {
            if (el.localName === 'lit-virtualizer') lists.push(el);
            if (el.shadowRoot) visit(el.shadowRoot);
        }
    };
    visit(dialog.shadowRoot ?? dialog);
    visit(dialog);
    const laidOut = (list) => {
        const rows = [...list.children]
            .filter((row) => !row.hasAttribute('virtualizer-sizer'))
            .map((row) => row.getBoundingClientRect())
            .sort((a, b) => a.top - b.top);
        return rows.every((row, i) => i === 0 || Math.abs(row.top - rows[i - 1].bottom) < 1);
    };
    const settle = async (list) => {
        while (!laidOut(list)) {
            if (performance.now() > deadline) throw new Error('A virtualized list never laid its rows out end to end');
            await frame();
        }
    };
    for (const list of lists) {
        const width = list.style.width;
        list.style.width = `${list.clientWidth - 1}px`;
        await settle(list);
        list.style.width = width;
        await settle(list);
    }
}
"""

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
    ha: LiveHomeAssistant | None = None

    # region: Screenshot Capture

    def _capture(self, step: str) -> None:
        """Capture screenshot with current context naming."""
        ctx = ScreenshotContext.current()
        if ctx:
            ctx.capture(self.page, step)

    def _capture_with_indicator(self, step: str, locator: Locator) -> None:
        """Capture screenshot with click indicator on target element."""
        self._scroll_into_view(locator)
        self._show_click_indicator(locator)
        self._capture(step)
        self._remove_click_indicator()

    def _show_click_indicator(self, locator: Locator) -> None:
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
            "input, select, ha-select, ha-integration-list-item, ha-checkbox"
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

    def _scroll_into_view(self, locator: Locator) -> bool:
        """Scroll element into view if needed.

        Returns True if the page actually scrolled, False if the element
        was already visible. The page settles first, so the decision rests on
        the final layout rather than one still taking shape.
        """
        self._settle()
        element = locator.element_handle(timeout=DEFAULT_TIMEOUT)
        if not element:
            return False

        before = element.evaluate(_GET_SCROLL_TOP_JS)
        locator.scroll_into_view_if_needed(timeout=DEFAULT_TIMEOUT)
        after = element.evaluate(_GET_SCROLL_TOP_JS)
        return abs(after - before) > 1

    def _scroll_and_capture(self, locator: Locator) -> None:
        """Scroll element into view and capture a screenshot if scrolling occurred."""
        scrolled = self._scroll_into_view(locator)
        if scrolled:
            self._capture("scrolled")

    def _settle(self) -> None:
        """Wait for the page to finish reacting to the last interaction."""
        wait_until_settled(self.page)

    # endregion

    # region: Navigation

    def goto(self, path: str) -> None:
        """Navigate to a path within Home Assistant.

        Only used for the initial page load. All subsequent navigation
        should use click-based methods to demonstrate the real user flow.
        """
        full_url = f"{self.url}{path}" if path.startswith("/") else path
        # The initial load drives the trusted_networks auto-login redirect chain
        # (/ -> /auth/authorize -> token exchange -> app), which takes longer than
        # an in-app navigation, so allow a generous timeout. networkidle would wait
        # on the HA WebSocket and OAuth static assets, leaving aiohttp file handles
        # open when the browser closes; domcontentloaded plus leaving /auth/ is enough.
        initial_load_timeout = 30000
        self.page.goto(full_url, timeout=initial_load_timeout, wait_until="domcontentloaded")
        self.page.wait_for_function(
            "() => !window.location.pathname.startsWith('/auth/')",
            timeout=initial_load_timeout,
        )
        self.page.locator("ha-sidebar").wait_for(state="visible", timeout=initial_load_timeout)
        self._settle()

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
                self.page.wait_for_url("**/config/dashboard")
                self._capture("settings_page")
        else:
            settings.click()
            self.page.wait_for_url("**/config/dashboard")

    def navigate_to_integrations(self) -> None:
        """Navigate to Devices & services from Settings page."""
        ctx = ScreenshotContext.current()
        ds = self.page.get_by_text("Devices & services")
        ds.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("navigate_integrations"):
                self._capture_with_indicator("settings_item", ds)
                ds.click()
                self.page.wait_for_url("**/config/integrations/dashboard")
        else:
            ds.click()
            self.page.wait_for_url("**/config/integrations/dashboard")

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
                self.page.wait_for_url("**/config/integrations/integration/*")
                self._capture("integration_page")
        else:
            card.click()
            self.page.wait_for_url("**/config/integrations/integration/*")

    def navigate_to_developer_tools_actions(self) -> None:
        """Navigate to Developer Tools > Actions via Settings."""
        ctx = ScreenshotContext.current()

        # Developer Tools is under Settings in modern HA
        self.navigate_to_settings()

        dev_tools = self.page.get_by_text("Developer tools")
        dev_tools.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("navigate_developer_tools"):
                self._capture_with_indicator("sidebar", dev_tools)
                dev_tools.click()
                self.page.wait_for_url("**/developer-tools/**")
                self._capture("developer_tools_page")
        else:
            dev_tools.click()
            self.page.wait_for_url("**/developer-tools/**")

        # Click Actions tab if not already active
        actions_tab = self.page.get_by_role("tab", name="Actions")
        actions_tab.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        if ctx:
            with ctx.scope("actions_tab"):
                self._capture_with_indicator("tab", actions_tab)
                actions_tab.click()
                self.page.wait_for_url("**/developer-tools/action")
                self._capture("actions_page")
        else:
            actions_tab.click()
            self.page.wait_for_url("**/developer-tools/action")

    def fill_service_action(self, service_name: str, display_name: str) -> None:
        """Fill the service/action field in Developer Tools.

        The action picker in HA uses a custom web component with shadow DOM.
        We clear the current selection, type the service name to filter,
        and click the matching dropdown item.

        Args:
            service_name: The service identifier to search (e.g., "haeo.save_diagnostics").
            display_name: The visible display name in the dropdown (e.g., "Save diagnostics").

        """
        ctx = ScreenshotContext.current()

        # The action picker shows the currently selected service with an X and dropdown
        picker = self.page.locator("ha-service-picker")
        picker.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        # Clear the current selection by clicking the X button
        clear_btn = picker.locator("ha-svg-icon").first
        clear_btn.click()

        if ctx:
            with ctx.scope("fill_action"):
                # Now the picker shows an input field for searching.
                # The following wait_for absorbs the picker's appearance.
                search = picker.locator("input")
                search.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture_with_indicator("field", picker)

                search.fill(service_name)

                # Match the dropdown item by its display name;
                # the wait_for absorbs the picker's search debounce.
                option = self.page.get_by_text(display_name).first
                option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture_with_indicator("option", option)
                option.click()
                self._capture("selected")
        else:
            search = picker.locator("input")
            search.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            search.fill(service_name)
            option = self.page.get_by_text(display_name).first
            option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            option.click()

    def fill_datetime_field(self, label: str, value: str) -> None:
        """Fill a datetime selector field in a service form.

        HA datetime selectors have a checkbox to enable them (optional fields)
        and split date/time components. This method enables the checkbox,
        then fills the date and time inputs.

        Args:
            label: The visible label text of the datetime field (e.g., "Time").
            value: The datetime value as "YYYY-MM-DD HH:MM" string.

        """
        ctx = ScreenshotContext.current()

        # Find the checkbox associated with this label. HA renders optional service
        # fields with a ha-checkbox next to the label text inside a container element.
        # Scope by label to avoid clicking the wrong checkbox when multiple exist.
        field_container = self.page.locator(f"ha-checkbox:near(:text('{label}'))").first
        field_container.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        checkbox = field_container

        if ctx:
            with ctx.scope(f"fill_datetime_{label}"):
                self._capture_with_indicator("checkbox", checkbox)
                checkbox.click()
                self._settle()
                self._capture("enabled")

                # Parse the value to fill date and time separately
                parts = value.split(" ", 1)
                date_str = parts[0]  # YYYY-MM-DD
                time_str = parts[1] if len(parts) > 1 else "12:00"

                # Set the date via the underlying ha-date-input component's value property
                # The input is readonly (opens a calendar picker), so we set it via JS
                self.page.evaluate(
                    """(date) => {
                        const el = document.querySelector('ha-date-input')
                            || document.querySelector('home-assistant').shadowRoot
                                .querySelector('ha-date-input');
                        // Walk through all shadow roots to find ha-date-input
                        function find(root) {
                            if (!root) return null;
                            const direct = root.querySelector('ha-date-input');
                            if (direct) return direct;
                            for (const el of root.querySelectorAll('*')) {
                                if (el.shadowRoot) {
                                    const found = find(el.shadowRoot);
                                    if (found) return found;
                                }
                            }
                            return null;
                        }
                        const dateInput = find(document);
                        if (dateInput) {
                            dateInput.value = date;
                            dateInput.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    }""",
                    date_str,
                )
                self._settle()

                # Fill time inputs (hh, mm)
                time_parts = time_str.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                # HA uses 12-hour format with AM/PM
                am_pm = "AM" if hour < 12 else "PM"
                display_hour = hour % 12 or 12

                hh_input = self.page.locator("ha-base-time-input input").nth(0)
                mm_input = self.page.locator("ha-base-time-input input").nth(1)

                hh_input.fill(str(display_hour))
                mm_input.fill(str(minute).zfill(2))
                self._settle()

                # Set AM/PM if needed
                if am_pm == "PM":
                    # The AM/PM selector is an MDC select component inside shadow DOM
                    # Use the dropdown arrow icon to open it, then select PM
                    ampm_dropdown = self.page.locator("ha-base-time-input ha-select")
                    ampm_dropdown.click(force=True)
                    pm_option = self.page.get_by_text("PM", exact=True).last
                    pm_option.click()
                    self._settle()

                self._capture("filled")
        else:
            checkbox.click()
            self._settle()
            parts = value.split(" ", 1)
            date_str = parts[0]
            time_str = parts[1] if len(parts) > 1 else "12:00"
            self.page.evaluate(
                """(date) => {
                    function find(root) {
                        if (!root) return null;
                        const direct = root.querySelector('ha-date-input');
                        if (direct) return direct;
                        for (const el of root.querySelectorAll('*')) {
                            if (el.shadowRoot) {
                                const found = find(el.shadowRoot);
                                if (found) return found;
                            }
                        }
                        return null;
                    }
                    const dateInput = find(document);
                    if (dateInput) {
                        dateInput.value = date;
                        dateInput.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""",
                date_str,
            )
            time_parts = time_str.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            am_pm = "AM" if hour < 12 else "PM"
            display_hour = hour % 12 or 12
            hh_input = self.page.locator("ha-base-time-input input").nth(0)
            mm_input = self.page.locator("ha-base-time-input input").nth(1)
            hh_input.fill(str(display_hour))
            mm_input.fill(str(minute).zfill(2))
            if am_pm == "PM":
                ampm_dropdown = self.page.locator("ha-base-time-input ha-select")
                ampm_dropdown.click(force=True)
                pm_option = self.page.get_by_text("PM", exact=True).last
                pm_option.click()
                self._settle()

    def select_config_entry(self, name: str) -> None:
        """Select a config entry from the Integration dropdown.

        Clicks the Integration dropdown to open it, then selects
        the matching entry by display name.

        Args:
            name: The display name of the config entry to select.

        """
        ctx = ScreenshotContext.current()

        # Click the Integration dropdown to open it
        dropdown = self.page.get_by_text("Integration", exact=False).first
        dropdown.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("select_config_entry"):
                self._capture_with_indicator("dropdown", dropdown)
                dropdown.click()

                # Select the matching entry from the opened list
                option = self.page.get_by_text(name).first
                option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture_with_indicator("option", option)
                option.click()
                self._settle()
                self._capture("selected")
        else:
            dropdown.click()
            option = self.page.get_by_text(name).first
            option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            option.click()
            self._settle()

    def click_perform_action(self) -> None:
        """Click the Perform action button in Developer Tools."""
        ctx = ScreenshotContext.current()
        button = self.page.get_by_role("button", name="Perform action")
        button.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        if ctx:
            with ctx.scope("perform_action"):
                self._scroll_and_capture(button)
                self._capture_with_indicator("button", button)
                button.click()
                self._wait_for_action_result()
                self._capture("result")
        else:
            button.click()
            self._wait_for_action_result()

    def _wait_for_action_result(self) -> None:
        """Wait for the Perform action button to report how the action went.

        The button shows a check mark or a cross for two seconds once the
        action returns, so the result is captured while it shows.
        """
        result = self.page.locator("ha-progress-button ha-button.result")
        result.wait_for(state="visible", timeout=SEARCH_TIMEOUT)
        if "success" not in (result.get_attribute("class") or "").split():
            msg = "The action failed"
            raise RuntimeError(msg)

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
                expect(combobox).to_have_attribute("aria-expanded", "false", timeout=DEFAULT_TIMEOUT)
                self._capture("selected")
        else:
            combobox.click()
            option = self.page.get_by_role("option", name=option_text)
            option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            option.click()
            expect(combobox).to_have_attribute("aria-expanded", "false", timeout=DEFAULT_TIMEOUT)

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
                self._settle()
                self._capture("selected")
        else:
            ha_select.click()
            option = self.page.get_by_role("option", name=option_text)
            option.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            option.click()
            self._settle()

    # endregion

    # region: Sections

    def expand_section(self, section_name: str) -> None:
        """Expand a collapsed form section by clicking its header.

        Sections are rendered as ``ha-expansion-panel`` within ``ha-form-expandable``.
        If the panel is already expanded, this is a no-op.
        """
        panel = self.page.locator("ha-expansion-panel").filter(has_text=section_name)
        panel.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        expanded = self.page.locator("ha-expansion-panel[expanded]").filter(has_text=section_name)

        # Check if already expanded by looking for the attribute
        if panel.get_attribute("expanded") is not None:
            return

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"expand_{section_name}"):
                self._scroll_and_capture(panel)
                self._capture_with_indicator("collapsed", panel)
                panel.click()
                expanded.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture("expanded")
        else:
            panel.click()
            expanded.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

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

    def choose_dropdown_multi(self, field_label: str, options: list[str]) -> None:
        """Select multiple options from a SelectSelector nested inside a ChooseSelector.

        Assumes a choice with a multi-select DROPDOWN is already active.
        """
        choose = self.page.locator("ha-selector-choose").filter(has_text=field_label)
        choose.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        self._pick_multi(choose.locator("ha-picker-field"), field_label, options)

    def select_dropdown_multi(self, field_label: str, options: list[str]) -> None:
        """Select multiple options from a multi-select DROPDOWN SelectSelector.

        On its own the selector shows an add button named after the field, so it is
        found by that exact name rather than by text that a description could repeat.
        """
        button = self.page.locator("ha-selector-select").get_by_role("button", name=field_label, exact=True)
        self._pick_multi(button, field_label, options)

    def _pick_multi(self, picker: Locator, field_label: str, options: list[str]) -> None:
        """Pick each option from a multi-select picker by clicking it once per option.

        HA renders multi-select DROPDOWN as ``ha-generic-picker`` which opens
        a "Select option" dialog when its field or add button is clicked. HA closes the dialog after
        each selection, so we re-open the picker for each option.

        Screenshots per option: dialog open, option indicator, result chip.
        """
        picker.wait_for(state="attached", timeout=DEFAULT_TIMEOUT)

        select_dialog = self.page.get_by_role("dialog", name="Select option")

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope(f"dropdown_{field_label}"):
                for option_text in options:
                    with ctx.scope(option_text):
                        picker.click()
                        select_dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                        item = select_dialog.locator(f":text('{option_text}')").first
                        item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                        self._capture("dialog")
                        self._capture_with_indicator("select", item)
                        item.click()
                        select_dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)
                        self._capture("selected")
        else:
            for option_text in options:
                picker.click()
                select_dialog.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                item = select_dialog.locator(f":text('{option_text}')").first
                item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                item.click()
                select_dialog.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

    # endregion

    def _select_entity_no_capture(
        self,
        picker_or_search: Locator,
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
                self._settle()
                self._capture("selected")
        else:
            picker.click()
            search_input = self.page.locator("vaadin-combo-box-overlay input").first
            search_input.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            search_input.fill(search_term)
            result_item = self.page.locator(f"ha-combo-box-item:has-text('{entity_name}')").first
            result_item.wait_for(state="visible", timeout=SEARCH_TIMEOUT)
            result_item.click(timeout=DEFAULT_TIMEOUT)
            self._settle()

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
            self._settle()

        _LOGGER.info("Dialog closed successfully")

    @contextmanager
    def expect_config_reload(self) -> Iterator[None]:
        """Wait for the config-entry reload triggered inside the block to finish.

        Committing a subentry (adding or editing an element, saving a policy)
        schedules a full integration reload that rebuilds the element-add
        buttons. Starting the next action before that reload settles races the
        teardown, so callers wrap the triggering action::

            with page.expect_config_reload():
                page.submit()
                page.close_element_dialog()

        The HA state listener is registered on entry (before the action runs)
        so the reload's start can't be missed, and the block exits only once
        the entry is loaded again and the page has caught up with it.
        """
        if self.ha is None:
            yield
            return
        reload_wait = self.ha.begin_wait_for_config_reload()
        yield
        self.ha.wait_for_config_reload(reload_wait)
        self.sync_frontend()

    def sync_frontend(self) -> None:
        """Bring the page up to date with what Home Assistant holds now.

        The backend having settled does not mean the page has heard about it:
        updates are still in flight, and a burst of registry changes, such as
        a reload's new entities, can leave the page showing partial counts.
        """
        self.page.evaluate(_SYNC_FRONTEND_JS)

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
            self._settle()

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
        self._capture("dialog_opened")

    def submit(self) -> None:
        """Click the Submit button."""
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
        self._settle()
        dialog = self.page.locator("ha-dialog[open]").filter(has=search_box)
        dialog.evaluate(_REMEASURE_LISTS_JS, SETTLE_DEADLINE_MS)

        ctx = ScreenshotContext.current()
        if ctx:
            with ctx.scope("search_integration"):
                self._capture("dialog")
                self._capture_with_indicator("search_box", search_box)

                search_box.click()
                search_box.fill(integration_name)

                item = self.page.locator("ha-integration-list-item", has_text=integration_name)
                item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
                self._capture("results")
                self._capture_with_indicator("select", item)

                item.click(timeout=DEFAULT_TIMEOUT)
        else:
            search_box.click()
            search_box.fill(integration_name)
            item = self.page.locator("ha-integration-list-item", has_text=integration_name)
            item.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            item.click(timeout=DEFAULT_TIMEOUT)

        # Closing the search hands focus back to the button that opened it, so
        # let that finish before the setup dialog is shown
        search_box.wait_for(state="detached", timeout=SEARCH_TIMEOUT)

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
