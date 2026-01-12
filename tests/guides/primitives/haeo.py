"""HAEO element primitives for guide automation.

High-level functions that add elements to an HAEO network.
Each function is decorated with @guide_step for automatic screenshot naming.

All entity parameters are tuples of (search_term, display_name).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .capture import ScreenshotContext, guide_step

if TYPE_CHECKING:
    from .ha_page import HAPage

_LOGGER = logging.getLogger(__name__)

# Type alias for entity selection: (search_term, display_name)
Entity = tuple[str, str]


@guide_step
def login(page: HAPage) -> None:
    """Log in to Home Assistant."""
    _LOGGER.info("Logging in...")
    page.goto("/")

    if "/auth/authorize" in page.page.url:
        page.fill_textbox("Username", "testuser")
        page.fill_textbox("Password", "testpass")
        page.click_button("Log in")
        page.page.wait_for_url("**/lovelace/**", timeout=10000)

    _LOGGER.info("Logged in")


@guide_step
def add_integration(page: HAPage, *, network_name: str) -> None:
    """Add HAEO integration to Home Assistant."""
    _LOGGER.info("Adding HAEO integration: %s", network_name)

    page.goto("/config/integrations")
    page.click_add_integration()
    page.search_integration("HAEO")

    page.wait_for_dialog("HAEO Setup")
    page.fill_textbox("System Name", network_name)
    page.submit()
    page.wait_for_load()

    page.goto("/config/integrations/integration/haeo")
    page._capture("integration_page")

    _LOGGER.info("HAEO integration added")


@guide_step
def add_inverter(
    page: HAPage,
    *,
    name: str,
    connection: str,
    max_power_dc_to_ac: Entity,
    max_power_ac_to_dc: Entity,
) -> None:
    """Add inverter element to HAEO network."""
    _LOGGER.info("Adding Inverter: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Inverter")
    page.wait_for_dialog("Inverter Configuration")

    page.fill_textbox("Inverter Name", name)
    page.select_combobox("AC Connection", connection)

    page.select_entity("Max DC to AC Power", max_power_dc_to_ac[0], max_power_dc_to_ac[1])
    page.select_entity("Max AC to DC Power", max_power_ac_to_dc[0], max_power_ac_to_dc[1])

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Inverter added: %s", name)


@guide_step
def add_battery(
    page: HAPage,
    *,
    name: str,
    connection: str,
    capacity: Entity,
    initial_soc: Entity,
    max_charge_power: Entity | None = None,
    max_discharge_power: Entity | None = None,
    min_charge_level: int | None = None,
    max_charge_level: int | None = None,
) -> None:
    """Add battery element to HAEO network."""
    _LOGGER.info("Adding Battery: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Battery")
    page.wait_for_dialog("Battery Configuration")

    page.fill_textbox("Battery Name", name)
    page.select_combobox("Connection", connection)

    page.select_entity("Capacity", capacity[0], capacity[1])
    page.select_entity("State of Charge", initial_soc[0], initial_soc[1])

    if max_charge_power:
        page.select_entity("Max Charging Power", max_charge_power[0], max_charge_power[1])

    if max_discharge_power:
        page.select_entity("Max Discharging Power", max_discharge_power[0], max_discharge_power[1])

    page.submit()

    # Step 2: min/max charge levels if present
    _handle_step2(page, min_charge_level=min_charge_level, max_charge_level=max_charge_level)

    page.close_element_dialog()

    _LOGGER.info("Battery added: %s", name)


@guide_step
def add_solar(
    page: HAPage,
    *,
    name: str,
    connection: str,
    forecasts: list[Entity],
) -> None:
    """Add solar element to HAEO network."""
    _LOGGER.info("Adding Solar: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Solar")
    page.wait_for_dialog("Solar Configuration")

    page.fill_textbox("Solar Name", name)
    page.select_combobox("Connection", connection)

    # First forecast
    if forecasts:
        first = forecasts[0]
        page.select_entity("Forecast", first[0], first[1])

        # Additional forecasts
        for forecast in forecasts[1:]:
            page.add_another_entity("Forecast", forecast[0], forecast[1])

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Solar added: %s", name)


@guide_step
def add_grid(
    page: HAPage,
    *,
    name: str,
    connection: str,
    import_prices: list[Entity],
    export_prices: list[Entity],
    import_limit: float | None = None,
    export_limit: float | None = None,
) -> None:
    """Add grid element to HAEO network."""
    _LOGGER.info("Adding Grid: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Grid")
    page.wait_for_dialog("Grid Configuration")

    page.fill_textbox("Grid Name", name)
    page.select_combobox("Connection", connection)

    # Import prices
    if import_prices:
        first = import_prices[0]
        page.select_entity("Import Price", first[0], first[1])
        for price in import_prices[1:]:
            page.add_another_entity("Import Price", price[0], price[1])

    # Export prices
    if export_prices:
        first = export_prices[0]
        page.select_entity("Export Price", first[0], first[1])
        for price in export_prices[1:]:
            page.add_another_entity("Export Price", price[0], price[1])

    page.submit()

    # Step 2: import/export limits
    _handle_step2(page, import_limit=import_limit, export_limit=export_limit)

    page.close_element_dialog()

    _LOGGER.info("Grid added: %s", name)


@guide_step
def add_load(
    page: HAPage,
    *,
    name: str,
    connection: str,
    forecast: Entity | None = None,
    constant_value: float | None = None,
) -> None:
    """Add load element to HAEO network."""
    _LOGGER.info("Adding Load: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Load")
    page.wait_for_dialog("Load Configuration")

    page.fill_textbox("Load Name", name)
    page.select_combobox("Connection", connection)

    if forecast:
        page.select_entity("Forecast", forecast[0], forecast[1])

    page.submit()

    # Step 2: constant value if configurable entity was selected
    _handle_step2(page, constant_value=constant_value)

    page.close_element_dialog()

    _LOGGER.info("Load added: %s", name)


@guide_step
def add_node(page: HAPage, *, name: str) -> None:
    """Add node element to HAEO network."""
    _LOGGER.info("Adding Node: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Node")
    page.wait_for_dialog("Node Configuration")

    page.fill_textbox("Node Name", name)

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Node added: %s", name)


@guide_step
def verify_setup(page: HAPage) -> None:
    """Verify the HAEO setup is complete."""
    _LOGGER.info("Verifying setup...")

    page.goto("/config/integrations/integration/haeo")
    page.page.get_by_role("button", name="Inverter").first.wait_for(state="visible", timeout=5000)
    page._capture("final_overview")

    _LOGGER.info("Setup verified")


# Helper functions


def _handle_step2(page: HAPage, **fields: Any) -> None:
    """Handle step 2 spinbuttons if present."""
    submit = page.page.get_by_role("button", name="Submit")
    if submit.count() == 0:
        return

    try:
        if not submit.is_visible(timeout=1000):
            return
    except Exception:
        return

    # Map field names to form labels
    field_mappings = {
        "min_charge_level": "Min Charge Level",
        "max_charge_level": "Max Charge Level",
        "import_limit": "Import Limit",
        "export_limit": "Export Limit",
        "constant_value": "Forecast",
    }

    ctx = ScreenshotContext.current()
    if ctx:
        ctx.push("step2")

    try:
        for field_name, value in fields.items():
            if value is not None:
                label = field_mappings.get(field_name)
                if label:
                    spinbutton = page.page.get_by_role("spinbutton", name=label)
                    if spinbutton.count() > 0:
                        try:
                            if spinbutton.is_visible(timeout=1000):
                                page.fill_spinbutton(label, str(value))
                        except Exception:
                            pass

        page.submit()
    finally:
        if ctx:
            ctx.pop()
