"""HAEO element primitives for guide automation.

High-level functions that add elements to an HAEO network, handling
navigation, form filling, and screenshot capture.

These primitives accept ElementSchema TypedDicts and translate them
to the appropriate HA config flow interactions.
"""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from custom_components.haeo.elements.battery.schema import BatteryConfigSchema
    from custom_components.haeo.elements.grid.schema import GridConfigSchema
    from custom_components.haeo.elements.inverter.schema import InverterConfigSchema
    from custom_components.haeo.elements.load.schema import LoadConfigSchema
    from custom_components.haeo.elements.node.schema import NodeConfigSchema
    from custom_components.haeo.elements.solar.schema import SolarConfigSchema

    from .context import GuideContext

_LOGGER = logging.getLogger(__name__)

# Default timeout for UI interactions
DEFAULT_TIMEOUT = 5000


def add_integration(ctx: GuideContext, network_name: str) -> None:
    """Add HAEO integration to Home Assistant.

    Navigates to integrations page, adds HAEO, and configures the network name.
    """
    _LOGGER.info("Adding HAEO integration with network: %s", network_name)
    page = ctx.page

    # Navigate to integrations page
    page.goto("/config/integrations")

    # Click "Add integration" button
    page.click_add_integration(capture=True)

    # Search for and select HAEO
    page.search_integration("HAEO", capture=True)

    # Wait for setup dialog
    page.wait_for_dialog("HAEO Setup")
    page.capture("network_form")

    # Fill system name
    page.fill_textbox("System Name", network_name, capture=True)

    # Submit
    page.submit(capture=True)
    page.wait_for_load()

    # Navigate to HAEO integration page
    page.goto("/config/integrations/integration/haeo")
    page.capture("haeo_integration_page")

    _LOGGER.info("HAEO integration added")


def add_inverter(ctx: GuideContext, config: InverterConfigSchema) -> None:
    """Add inverter element to HAEO network.

    Args:
        ctx: Guide execution context
        config: Inverter configuration with fields:
            - name: Display name
            - connection: AC node to connect to
            - max_power_dc_to_ac: Entity ID or constant
            - max_power_ac_to_dc: Entity ID or constant

    """
    _LOGGER.info("Adding Inverter: %s", config["name"])
    page = ctx.page

    # Navigate to HAEO integration page
    page.goto("/config/integrations/integration/haeo")

    # Click Inverter button
    page.click_button("Inverter", capture=True)
    page.wait_for_dialog("Inverter Configuration")

    # Fill name
    page.fill_textbox("Inverter Name", config["name"], capture=True)

    # Select connection
    page.select_combobox("AC Connection", config["connection"], capture=True)

    # Select power sensors - these are the required fields
    dc_to_ac = config["max_power_dc_to_ac"]
    ac_to_dc = config["max_power_ac_to_dc"]

    if isinstance(dc_to_ac, str):
        # Entity selection - use search terms from entity ID
        page.select_entity(
            "Max DC to AC Power",
            _entity_search_term(dc_to_ac),
            _entity_display_name(dc_to_ac),
            capture=True,
        )
    # For float values, the field would be a spinbutton instead

    if isinstance(ac_to_dc, str):
        page.select_entity(
            "Max AC to DC Power",
            _entity_search_term(ac_to_dc),
            _entity_display_name(ac_to_dc),
            capture=True,
        )

    # Submit and close
    page.submit(capture=True)
    page.close_element_dialog(capture=True)

    _LOGGER.info("Inverter added: %s", config["name"])


def add_battery(ctx: GuideContext, config: BatteryConfigSchema) -> None:
    """Add battery element to HAEO network.

    Args:
        ctx: Guide execution context
        config: Battery configuration with fields:
            - name: Display name
            - connection: Element to connect to
            - capacity: Entity ID or constant (kWh)
            - initial_charge_percentage: Entity ID or constant (%)
            - min_charge_percentage: Optional min SOC (%)
            - max_charge_percentage: Optional max SOC (%)
            - max_charge_power: Optional entity ID or constant (kW)
            - max_discharge_power: Optional entity ID or constant (kW)

    """
    _LOGGER.info("Adding Battery: %s", config["name"])
    page = ctx.page

    # Navigate to HAEO integration page
    page.goto("/config/integrations/integration/haeo")

    # Click Battery button
    page.click_button("Battery", capture=True)
    page.wait_for_dialog("Battery Configuration")

    # Fill name
    page.fill_textbox("Battery Name", config["name"], capture=True)

    # Select connection
    page.select_combobox("Connection", config["connection"], capture=True)

    # Entity selections for required fields
    capacity = config["capacity"]
    if isinstance(capacity, str):
        page.select_entity(
            "Capacity",
            _entity_search_term(capacity),
            _entity_display_name(capacity),
            capture=True,
        )

    soc = config["initial_charge_percentage"]
    if isinstance(soc, str):
        page.select_entity(
            "State of Charge",
            _entity_search_term(soc),
            _entity_display_name(soc),
            capture=True,
        )

    # Optional power limits
    if "max_charge_power" in config:
        charge_power = config["max_charge_power"]
        if isinstance(charge_power, str):
            page.select_entity(
                "Max Charging Power",
                _entity_search_term(charge_power),
                _entity_display_name(charge_power),
                capture=True,
            )

    if "max_discharge_power" in config:
        discharge_power = config["max_discharge_power"]
        if isinstance(discharge_power, str):
            page.select_entity(
                "Max Discharging Power",
                _entity_search_term(discharge_power),
                _entity_display_name(discharge_power),
                capture=True,
            )

    # Submit step 1
    page.submit(capture=True)

    # Check if step 2 exists (spinbuttons for configurable values)
    _handle_step2_spinbuttons(page, config)

    # Close dialog
    page.close_element_dialog(capture=True)

    _LOGGER.info("Battery added: %s", config["name"])


def add_solar(ctx: GuideContext, config: SolarConfigSchema) -> None:
    """Add solar element to HAEO network.

    Args:
        ctx: Guide execution context
        config: Solar configuration with fields:
            - name: Display name
            - connection: Element to connect to
            - forecast: Entity ID(s) or constant (kW)

    """
    _LOGGER.info("Adding Solar: %s", config["name"])
    page = ctx.page

    # Navigate to HAEO integration page
    page.goto("/config/integrations/integration/haeo")

    # Click Solar button
    page.click_button("Solar", capture=True)
    page.wait_for_dialog("Solar Configuration")

    # Fill name
    page.fill_textbox("Solar Name", config["name"], capture=True)

    # Select connection
    page.select_combobox("Connection", config["connection"], capture=True)

    # Handle forecast field - can be list of entity IDs
    _select_entity_field(page, "Forecast", config["forecast"])

    # Submit and close
    page.submit(capture=True)
    page.close_element_dialog(capture=True)

    _LOGGER.info("Solar added: %s", config["name"])


def add_grid(ctx: GuideContext, config: GridConfigSchema) -> None:
    """Add grid element to HAEO network.

    Args:
        ctx: Guide execution context
        config: Grid configuration with fields:
            - name: Display name
            - connection: Element to connect to
            - import_price: Entity ID(s) or constant ($/kWh)
            - export_price: Entity ID(s) or constant ($/kWh)
            - import_limit: Optional limit (kW)
            - export_limit: Optional limit (kW)

    """
    _LOGGER.info("Adding Grid: %s", config["name"])
    page = ctx.page

    # Navigate to HAEO integration page
    page.goto("/config/integrations/integration/haeo")

    # Click Grid button
    page.click_button("Grid", capture=True)
    page.wait_for_dialog("Grid Configuration")

    # Fill name
    page.fill_textbox("Grid Name", config["name"], capture=True)

    # Select connection
    page.select_combobox("Connection", config["connection"], capture=True)

    # Import price - can be list of entities
    _select_entity_field(page, "Import Price", config["import_price"])

    # Export price - can be list of entities
    _select_entity_field(page, "Export Price", config["export_price"])

    # Submit step 1 (entities)
    page.submit(capture=True)

    # Step 2: Handle limits if present
    _handle_step2_spinbuttons(page, config)

    # Close dialog
    page.close_element_dialog(capture=True)

    _LOGGER.info("Grid added: %s", config["name"])


def add_load(ctx: GuideContext, config: LoadConfigSchema) -> None:
    """Add load element to HAEO network.

    Args:
        ctx: Guide execution context
        config: Load configuration with fields:
            - name: Display name
            - connection: Element to connect to
            - forecast: Entity ID(s) or constant (kW)

    """
    _LOGGER.info("Adding Load: %s", config["name"])
    page = ctx.page

    # Navigate to HAEO integration page
    page.goto("/config/integrations/integration/haeo")

    # Click Load button
    page.click_button("Load", capture=True)
    page.wait_for_dialog("Load Configuration")

    # Fill name
    page.fill_textbox("Load Name", config["name"], capture=True)

    # Select connection
    page.select_combobox("Connection", config["connection"], capture=True)

    # Handle forecast field
    _select_entity_field(page, "Forecast", config["forecast"])

    # Submit step 1
    page.submit(capture=True)

    # Check if step 2 exists (spinbuttons for configurable values)
    _handle_step2_spinbuttons(page, config)

    # Close dialog
    page.close_element_dialog(capture=True)

    _LOGGER.info("Load added: %s", config["name"])


def add_node(ctx: GuideContext, config: NodeConfigSchema) -> None:
    """Add node element to HAEO network.

    Args:
        ctx: Guide execution context
        config: Node configuration with fields:
            - name: Display name
            - is_source: Optional bool (default False)
            - is_sink: Optional bool (default False)

    """
    _LOGGER.info("Adding Node: %s", config["name"])
    page = ctx.page

    # Navigate to HAEO integration page
    page.goto("/config/integrations/integration/haeo")

    # Click Node button
    page.click_button("Node", capture=True)
    page.wait_for_dialog("Node Configuration")

    # Fill name
    page.fill_textbox("Node Name", config["name"], capture=True)

    # Note: is_source and is_sink would need checkbox handling if present

    # Submit and close
    page.submit(capture=True)
    page.close_element_dialog(capture=True)

    _LOGGER.info("Node added: %s", config["name"])


# region: Helper Functions


def _entity_search_term(entity_id: str) -> str:
    """Extract search term from entity ID.

    Takes an entity ID like 'sensor.battery_soc' and returns
    a search term like 'battery soc'.
    """
    # Remove domain prefix and convert to search term
    if "." in entity_id:
        entity_id = entity_id.split(".", 1)[1]
    return entity_id.replace("_", " ")


def _entity_display_name(entity_id: str) -> str:
    """Extract expected display name from entity ID.

    Takes an entity ID like 'sensor.battery_soc' and returns
    a title-cased display name like 'Battery Soc'.

    Note: This is an approximation - actual display names may differ.
    Guides should specify explicit display names in their config.
    """
    if "." in entity_id:
        entity_id = entity_id.split(".", 1)[1]
    return entity_id.replace("_", " ").title()


def _select_entity_field(page: Any, field_label: str, value: list[str] | str | float) -> None:
    """Select one or more entities for a field.

    Handles entity ID strings, lists of entity IDs, and skips float constants.
    """
    if isinstance(value, list):
        # First entity
        if len(value) > 0:
            page.select_entity(
                field_label,
                _entity_search_term(value[0]),
                _entity_display_name(value[0]),
                capture=True,
            )
        # Additional entities
        for entity_id in value[1:]:
            page.add_another_entity(
                field_label,
                _entity_search_term(entity_id),
                _entity_display_name(entity_id),
                capture=True,
            )
    elif isinstance(value, str):
        page.select_entity(
            field_label,
            _entity_search_term(value),
            _entity_display_name(value),
            capture=True,
        )
    # Skip float constants - those are handled in step 2


def _handle_step2_spinbuttons(page: Any, config: Mapping[str, Any]) -> None:
    """Handle step 2 spinbuttons if present.

    Some config flows have a second step for entering constant values.
    This handles common fields like min/max charge, import/export limits.
    """
    # Check if Submit button exists (meaning we're on step 2)
    submit_button = page.page.get_by_role("button", name="Submit")
    if submit_button.count() == 0:
        return

    try:
        if not submit_button.is_visible(timeout=1000):
            return
    except Exception:
        return

    # Map of config field names to form field labels
    spinbutton_mappings = {
        "min_charge_percentage": "Min Charge Level",
        "max_charge_percentage": "Max Charge Level",
        "import_limit": "Import Limit",
        "export_limit": "Export Limit",
        "forecast": "Forecast",  # For configurable loads
    }

    for config_key, form_label in spinbutton_mappings.items():
        if config_key in config:
            value = config[config_key]
            if isinstance(value, int | float):
                spinbutton = page.page.get_by_role("spinbutton", name=form_label)
                if spinbutton.count() > 0:
                    try:
                        if spinbutton.is_visible(timeout=1000):
                            page.fill_spinbutton(form_label, str(value), capture=True)
                    except Exception:
                        pass

    # Submit step 2
    page.submit(capture=True)


# endregion
