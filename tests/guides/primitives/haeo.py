"""HAEO element primitives for guide automation.

High-level functions that add elements to an HAEO network.
Each function is decorated with @guide_step for automatic screenshot naming.

The current config flow uses single-step forms with collapsible sections
and ChooseSelector widgets (Entity/Constant/None) for each field.

All entity parameters are tuples of (search_term, display_name).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .capture import guide_step

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
    """Add inverter element to HAEO network.

    Inverter form structure:
    - Top-level: Inverter Name, AC Connection
    - Power limits section (expanded): Max DC to AC power, Max AC to DC power
    - Efficiency section (collapsed): DC to AC efficiency, AC to DC efficiency
    """
    _LOGGER.info("Adding Inverter: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Inverter")
    page.wait_for_dialog("Inverter Configuration")

    page.fill_textbox("Inverter Name", name)
    page.select_combobox("AC Connection", connection)

    # Power limits section is expanded by default
    page.choose_entity("Max DC to AC power", max_power_dc_to_ac[0], max_power_dc_to_ac[1])
    page.choose_entity("Max AC to DC power", max_power_ac_to_dc[0], max_power_ac_to_dc[1])

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
    """Add battery element to HAEO network.

    Battery form structure (single step with sections):
    - Top-level: Battery Name, Connection
    - Storage section (expanded): Capacity, State of Charge
    - Limits section (expanded): Min Charge Level, Max Charge Level
    - Power limits section (expanded): Max charge power, Max discharge power
    - Pricing section (expanded): Discharge price, Charge price, Salvage value
    - Efficiency section (collapsed): Discharge efficiency, Charge efficiency
    - Partitioning section (collapsed): Configure battery partitions
    """
    _LOGGER.info("Adding Battery: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Battery")
    page.wait_for_dialog("Battery Configuration")

    # Top-level fields
    page.fill_textbox("Battery Name", name)
    page.select_combobox("Connection", connection)

    # Storage section (expanded by default)
    page.choose_entity("Capacity", capacity[0], capacity[1])
    page.choose_entity("State of Charge", initial_soc[0], initial_soc[1])

    # Limits section (expanded by default) — switch to Constant for percentage values
    if min_charge_level is not None:
        page.choose_select_option("Min Charge Level", "Constant")
        page.choose_constant("Min Charge Level", str(min_charge_level))

    if max_charge_level is not None:
        page.choose_select_option("Max Charge Level", "Constant")
        page.choose_constant("Max Charge Level", str(max_charge_level))

    # Power limits section (expanded by default)
    if max_charge_power:
        page.choose_entity("Max charge power", max_charge_power[0], max_charge_power[1])

    if max_discharge_power:
        page.choose_entity("Max discharge power", max_discharge_power[0], max_discharge_power[1])

    page.submit()
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
    """Add solar element to HAEO network.

    Solar form structure:
    - Top-level: Solar Name, Connection
    - Forecast section (expanded): Forecast
    - Pricing section (expanded): Production price
    - Curtailment section (collapsed): Allow Curtailment
    """
    _LOGGER.info("Adding Solar: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Solar")
    page.wait_for_dialog("Solar Configuration")

    page.fill_textbox("Solar Name", name)
    page.select_combobox("Connection", connection)

    # Forecast section (expanded by default)
    if forecasts:
        first = forecasts[0]
        page.choose_entity("Forecast", first[0], first[1])

        # Additional forecasts
        for forecast in forecasts[1:]:
            page.choose_add_entity("Forecast", forecast[0], forecast[1])

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
    """Add grid element to HAEO network.

    Grid form structure (single step with sections):
    - Top-level: Grid Name, Connection
    - Pricing section (expanded): Import price, Export price
    - Power limits section (collapsed): Import limit, Export limit
    """
    _LOGGER.info("Adding Grid: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Grid")
    page.wait_for_dialog("Grid Configuration")

    page.fill_textbox("Grid Name", name)
    page.select_combobox("Connection", connection)

    # Pricing section (expanded by default)
    if import_prices:
        first = import_prices[0]
        page.choose_select_option("Import price", "Entity")
        page.choose_entity("Import price", first[0], first[1])
        for price in import_prices[1:]:
            page.choose_add_entity("Import price", price[0], price[1])

    if export_prices:
        first = export_prices[0]
        page.choose_select_option("Export price", "Entity")
        page.choose_entity("Export price", first[0], first[1])
        for price in export_prices[1:]:
            page.choose_add_entity("Export price", price[0], price[1])

    # Power limits section (collapsed by default) — expand if limits are specified
    if import_limit is not None or export_limit is not None:
        page.expand_section("Power limits")

        if import_limit is not None:
            page.choose_select_option("Import limit", "Constant")
            page.choose_constant("Import limit", str(import_limit))

        if export_limit is not None:
            page.choose_select_option("Export limit", "Constant")
            page.choose_constant("Export limit", str(export_limit))

    page.submit()
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
    """Add load element to HAEO network.

    Load form structure:
    - Top-level: Load Name, Connection
    - Forecast section (expanded): Forecast (ChooseSelector — Entity or Constant)

    Use ``forecast`` for an entity-based forecast, or ``constant_value`` for a
    fixed constant forecast. If both are provided, entity takes precedence.
    """
    _LOGGER.info("Adding Load: %s", name)

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Load")
    page.wait_for_dialog("Load Configuration")

    page.fill_textbox("Load Name", name)
    page.select_combobox("Connection", connection)

    # Forecast section (expanded by default)
    if forecast:
        page.choose_entity("Forecast", forecast[0], forecast[1])
    elif constant_value is not None:
        page.choose_select_option("Forecast", "Constant")
        page.choose_constant("Forecast", str(constant_value))

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Load added: %s", name)


@guide_step
def add_node(page: HAPage, *, name: str) -> None:
    """Add node element to HAEO network.

    Node form structure:
    - Top-level: Node Name
    - Role section (collapsed): Is source, Is sink
    """
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
