"""Base classes and utilities for HAEO config flows."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.haeo.core.schema.elements import ElementType

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
import voluptuous as vol

from custom_components.haeo.const import CONF_RECORD_FORECASTS
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON,
    CONF_NAME,
    DEFAULT_DEBOUNCE_SECONDS,
)
from custom_components.haeo.core.const import HUB_SECTION_ADVANCED as HUB_SECTION_ADVANCED
from custom_components.haeo.core.const import HUB_SECTION_COMMON as HUB_SECTION_COMMON
from custom_components.haeo.flows.field_schema import SectionDefinition, build_section_schema
from custom_components.haeo.flows.horizon import horizon_field

_LOGGER = logging.getLogger(__name__)


def get_hub_setup_schema(suggested_name: str | None = None) -> vol.Schema:
    """Get simplified schema for initial hub setup.

    Args:
        suggested_name: Optional suggested name for the hub (translatable default)

    Returns:
        Voluptuous schema with name, planning horizon, and basic settings.

    """
    name_key = (
        vol.Required(CONF_NAME, description={"suggested_value": suggested_name})
        if suggested_name
        else vol.Required(CONF_NAME)
    )

    sections = (
        SectionDefinition(
            key=HUB_SECTION_COMMON,
            fields=(CONF_NAME, CONF_HORIZON),
            collapsed=False,
        ),
        SectionDefinition(
            key=HUB_SECTION_ADVANCED,
            fields=(CONF_ADVANCED_MODE,),
            collapsed=True,
        ),
    )
    field_entries = {
        HUB_SECTION_COMMON: {
            CONF_NAME: (
                name_key,
                vol.All(
                    str,
                    vol.Strip,
                    vol.Length(min=1, msg="Name cannot be empty"),
                    vol.Length(max=255, msg="Name cannot be longer than 255 characters"),
                ),
            ),
            CONF_HORIZON: horizon_field(),
        },
        HUB_SECTION_ADVANCED: {
            CONF_ADVANCED_MODE: (
                vol.Required(CONF_ADVANCED_MODE, default=False),
                bool,
            ),
        },
    }
    return vol.Schema(build_section_schema(sections, field_entries))


def get_hub_options_schema(config_entry: ConfigEntry) -> vol.Schema:
    """Get simplified schema for hub options (edit) flow.

    Args:
        config_entry: Config entry to get current values from

    Returns:
        Voluptuous schema with the planning horizon and basic settings.

    """
    advanced_data = config_entry.data.get(HUB_SECTION_ADVANCED, {})

    sections = (
        SectionDefinition(
            key=HUB_SECTION_COMMON,
            fields=(CONF_HORIZON,),
            collapsed=False,
        ),
        SectionDefinition(
            key=HUB_SECTION_ADVANCED,
            fields=(CONF_DEBOUNCE_SECONDS, CONF_ADVANCED_MODE, CONF_RECORD_FORECASTS),
            collapsed=True,
        ),
    )
    field_entries = {
        HUB_SECTION_COMMON: {
            CONF_HORIZON: horizon_field(config_entry.data[HUB_SECTION_COMMON][CONF_HORIZON]),
        },
        HUB_SECTION_ADVANCED: {
            CONF_DEBOUNCE_SECONDS: (
                vol.Required(
                    CONF_DEBOUNCE_SECONDS,
                    default=advanced_data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS),
                ),
                vol.All(
                    NumberSelector(
                        NumberSelectorConfig(min=0, max=30, step=1, mode=NumberSelectorMode.BOX),
                    ),
                    vol.Coerce(int),
                ),
            ),
            CONF_ADVANCED_MODE: (
                vol.Required(
                    CONF_ADVANCED_MODE,
                    default=advanced_data.get(CONF_ADVANCED_MODE, False),
                ),
                bool,
            ),
            CONF_RECORD_FORECASTS: (
                vol.Required(
                    CONF_RECORD_FORECASTS,
                    default=config_entry.data.get(CONF_RECORD_FORECASTS, False),
                ),
                bool,
            ),
        },
    }
    return vol.Schema(build_section_schema(sections, field_entries))


def get_element_flow_classes() -> dict[ElementType, type]:
    """Return mapping of element types to their config flow handler classes.

    This function performs lazy imports to avoid circular dependencies
    (flows import adapters, not the other way around).
    """
    from custom_components.haeo.core.schema.elements import ElementType  # noqa: PLC0415
    from custom_components.haeo.flows.elements.battery import BatterySubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.battery_section import BatterySectionSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.connection import ConnectionSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.grid import GridSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.inverter import InverterSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.junction import JunctionSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.load import LoadSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.node import NodeSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.policy import PolicySubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.solar import SolarSubentryFlowHandler  # noqa: PLC0415

    return {
        ElementType.BATTERY: BatterySubentryFlowHandler,
        ElementType.BATTERY_SECTION: BatterySectionSubentryFlowHandler,
        ElementType.CONNECTION: ConnectionSubentryFlowHandler,
        ElementType.GRID: GridSubentryFlowHandler,
        ElementType.INVERTER: InverterSubentryFlowHandler,
        ElementType.LOAD: LoadSubentryFlowHandler,
        ElementType.JUNCTION: JunctionSubentryFlowHandler,
        ElementType.NODE: NodeSubentryFlowHandler,
        ElementType.POLICY: PolicySubentryFlowHandler,
        ElementType.SOLAR: SolarSubentryFlowHandler,
    }
