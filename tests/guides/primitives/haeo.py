"""HAEO element primitives for guide automation.

High-level functions that add elements to an HAEO network, handling
navigation, form filling, and screenshot capture.

These primitives accept guide-specific configuration with entity selections
that include search terms and display names for the HA entity picker.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .context import GuideContext
    from .ha_page import HAPage

_LOGGER = logging.getLogger(__name__)


# Type for entity selection: (search_term, display_name)
# Example: ("rated energy", "Rated Energy Capacity")
Entity = tuple[str, str]


@dataclass
class InverterConfig:
    """Inverter element configuration for guides."""

    name: str
    connection: str
    max_power_dc_to_ac: Entity
    max_power_ac_to_dc: Entity


@dataclass
class BatteryConfig:
    """Battery element configuration for guides."""

    name: str
    connection: str
    capacity: Entity
    initial_soc: Entity
    max_charge_power: Entity | None = None
    max_discharge_power: Entity | None = None
    min_charge_level: int | None = None
    max_charge_level: int | None = None


@dataclass
class SolarConfig:
    """Solar element configuration for guides."""

    name: str
    connection: str
    forecasts: list[Entity]


@dataclass
class GridConfig:
    """Grid element configuration for guides."""

    name: str
    connection: str
    import_prices: list[Entity]
    export_prices: list[Entity]
    import_limit: float | None = None
    export_limit: float | None = None


@dataclass
class LoadConfig:
    """Load element configuration for guides."""

    name: str
    connection: str
    forecast: Entity | None = None
    constant_value: float | None = None


@dataclass
class NodeConfig:
    """Node element configuration for guides."""

    name: str


def add_integration(ctx: GuideContext, network_name: str) -> None:
    """Add HAEO integration to Home Assistant."""
    _LOGGER.info("Adding HAEO integration: %s", network_name)
    page = ctx.page

    page.goto("/config/integrations")
    page.click_add_integration(capture=True)
    page.search_integration("HAEO", capture=True)

    page.wait_for_dialog("HAEO Setup")
    page.capture("network_form")

    page.fill_textbox("System Name", network_name, capture=True)
    page.submit(capture=True)
    page.wait_for_load()

    page.goto("/config/integrations/integration/haeo")
    page.capture("haeo_integration_page")

    _LOGGER.info("HAEO integration added")


def add_inverter(ctx: GuideContext, config: InverterConfig) -> None:
    """Add inverter element to HAEO network."""
    _LOGGER.info("Adding Inverter: %s", config.name)
    page = ctx.page

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Inverter", capture=True)
    page.wait_for_dialog("Inverter Configuration")

    page.fill_textbox("Inverter Name", config.name, capture=True)
    page.select_combobox("AC Connection", config.connection, capture=True)

    page.select_entity(
        "Max DC to AC Power",
        config.max_power_dc_to_ac[0],
        config.max_power_dc_to_ac[1],
        capture=True,
    )
    page.select_entity(
        "Max AC to DC Power",
        config.max_power_ac_to_dc[0],
        config.max_power_ac_to_dc[1],
        capture=True,
    )

    page.submit(capture=True)
    page.close_element_dialog(capture=True)

    _LOGGER.info("Inverter added: %s", config.name)


def add_battery(ctx: GuideContext, config: BatteryConfig) -> None:
    """Add battery element to HAEO network."""
    _LOGGER.info("Adding Battery: %s", config.name)
    page = ctx.page

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Battery", capture=True)
    page.wait_for_dialog("Battery Configuration")

    page.fill_textbox("Battery Name", config.name, capture=True)
    page.select_combobox("Connection", config.connection, capture=True)

    page.select_entity("Capacity", config.capacity[0], config.capacity[1], capture=True)
    page.select_entity("State of Charge", config.initial_soc[0], config.initial_soc[1], capture=True)

    if config.max_charge_power:
        page.select_entity(
            "Max Charging Power",
            config.max_charge_power[0],
            config.max_charge_power[1],
            capture=True,
        )

    if config.max_discharge_power:
        page.select_entity(
            "Max Discharging Power",
            config.max_discharge_power[0],
            config.max_discharge_power[1],
            capture=True,
        )

    page.submit(capture=True)

    # Step 2: min/max charge levels if present
    _handle_step2(page, config)

    page.close_element_dialog(capture=True)

    _LOGGER.info("Battery added: %s", config.name)


def add_solar(ctx: GuideContext, config: SolarConfig) -> None:
    """Add solar element to HAEO network."""
    _LOGGER.info("Adding Solar: %s", config.name)
    page = ctx.page

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Solar", capture=True)
    page.wait_for_dialog("Solar Configuration")

    page.fill_textbox("Solar Name", config.name, capture=True)
    page.select_combobox("Connection", config.connection, capture=True)

    # First forecast
    if config.forecasts:
        first = config.forecasts[0]
        page.select_entity("Forecast", first[0], first[1], capture=True)

        # Additional forecasts
        for forecast in config.forecasts[1:]:
            page.add_another_entity("Forecast", forecast[0], forecast[1], capture=True)

    page.submit(capture=True)
    page.close_element_dialog(capture=True)

    _LOGGER.info("Solar added: %s", config.name)


def add_grid(ctx: GuideContext, config: GridConfig) -> None:
    """Add grid element to HAEO network."""
    _LOGGER.info("Adding Grid: %s", config.name)
    page = ctx.page

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Grid", capture=True)
    page.wait_for_dialog("Grid Configuration")

    page.fill_textbox("Grid Name", config.name, capture=True)
    page.select_combobox("Connection", config.connection, capture=True)

    # Import prices
    if config.import_prices:
        first = config.import_prices[0]
        page.select_entity("Import Price", first[0], first[1], capture=True)
        for price in config.import_prices[1:]:
            page.add_another_entity("Import Price", price[0], price[1], capture=True)

    # Export prices
    if config.export_prices:
        first = config.export_prices[0]
        page.select_entity("Export Price", first[0], first[1], capture=True)
        for price in config.export_prices[1:]:
            page.add_another_entity("Export Price", price[0], price[1], capture=True)

    page.submit(capture=True)

    # Step 2: import/export limits
    _handle_step2(page, config)

    page.close_element_dialog(capture=True)

    _LOGGER.info("Grid added: %s", config.name)


def add_load(ctx: GuideContext, config: LoadConfig) -> None:
    """Add load element to HAEO network."""
    _LOGGER.info("Adding Load: %s", config.name)
    page = ctx.page

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Load", capture=True)
    page.wait_for_dialog("Load Configuration")

    page.fill_textbox("Load Name", config.name, capture=True)
    page.select_combobox("Connection", config.connection, capture=True)

    if config.forecast:
        page.select_entity("Forecast", config.forecast[0], config.forecast[1], capture=True)

    page.submit(capture=True)

    # Step 2: constant value if configurable entity was selected
    _handle_step2(page, config)

    page.close_element_dialog(capture=True)

    _LOGGER.info("Load added: %s", config.name)


def add_node(ctx: GuideContext, config: NodeConfig) -> None:
    """Add node element to HAEO network."""
    _LOGGER.info("Adding Node: %s", config.name)
    page = ctx.page

    page.goto("/config/integrations/integration/haeo")
    page.click_button("Node", capture=True)
    page.wait_for_dialog("Node Configuration")

    page.fill_textbox("Node Name", config.name, capture=True)

    page.submit(capture=True)
    page.close_element_dialog(capture=True)

    _LOGGER.info("Node added: %s", config.name)


def login(ctx: GuideContext) -> None:
    """Log in to Home Assistant."""
    _LOGGER.info("Logging in...")
    page = ctx.page

    page.goto("/")

    if "/auth/authorize" in page.page.url:
        page.fill_textbox("Username", "testuser")
        page.fill_textbox("Password", "testpass")
        page.click_button("Log in")
        page.page.wait_for_url("**/lovelace/**", timeout=10000)

    _LOGGER.info("Logged in")


def verify_setup(ctx: GuideContext) -> None:
    """Verify the HAEO setup is complete."""
    _LOGGER.info("Verifying setup...")
    page = ctx.page

    page.goto("/config/integrations/integration/haeo")
    page.page.get_by_role("button", name="Inverter").first.wait_for(state="visible", timeout=5000)
    page.capture("final_overview")

    _LOGGER.info("Setup verified")


# Helper functions


def _handle_step2(page: HAPage, config: Any) -> None:
    """Handle step 2 spinbuttons if present."""
    submit = page.page.get_by_role("button", name="Submit")
    if submit.count() == 0:
        return

    try:
        if not submit.is_visible(timeout=1000):
            return
    except Exception:
        return

    # Map config attributes to form labels
    field_mappings = {
        "min_charge_level": "Min Charge Level",
        "max_charge_level": "Max Charge Level",
        "import_limit": "Import Limit",
        "export_limit": "Export Limit",
        "constant_value": "Forecast",
    }

    for attr, label in field_mappings.items():
        value = getattr(config, attr, None)
        if value is not None:
            spinbutton = page.page.get_by_role("spinbutton", name=label)
            if spinbutton.count() > 0:
                try:
                    if spinbutton.is_visible(timeout=1000):
                        page.fill_spinbutton(label, str(value), capture=True)
                except Exception:
                    pass

    page.submit(capture=True)
