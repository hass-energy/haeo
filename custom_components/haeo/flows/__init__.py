"""Base classes and utilities for HAEO config flows."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Final

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
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_DEBOUNCE_SECONDS,
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.core.schema import HORIZON_PRESET_CUSTOM, is_horizon_entity_value
from custom_components.haeo.flows.field_schema import SectionDefinition, build_section_schema
from custom_components.haeo.flows.horizon_schema import (
    build_horizon_choose_selector,
    get_horizon_preferred_choice,
    horizon_config_to_form_default,
    stored_horizon_from_common,
)

_LOGGER = logging.getLogger(__name__)

# Horizon preset options (UI — custom tiers removed; use entity mode instead)
HORIZON_PRESET_2_DAYS: Final = "2_days"
HORIZON_PRESET_3_DAYS: Final = "3_days"
HORIZON_PRESET_7_DAYS: Final = "7_days"

HORIZON_PRESET_OPTIONS: Final = [
    HORIZON_PRESET_2_DAYS,
    HORIZON_PRESET_3_DAYS,
    HORIZON_PRESET_5_DAYS,
    HORIZON_PRESET_7_DAYS,
]


def _create_horizon_preset(days: int) -> dict[str, int]:
    """Create tier configuration for a given horizon in days."""
    min_days = 2
    if days < min_days:
        msg = f"Horizon must be at least {min_days} days"
        raise ValueError(msg)

    total_minutes = days * 24 * 60

    return {
        CONF_TIER_1_COUNT: 5,
        CONF_TIER_1_DURATION: 1,
        CONF_TIER_2_COUNT: 11,
        CONF_TIER_2_DURATION: 5,
        CONF_TIER_3_COUNT: 46,
        CONF_TIER_3_DURATION: 30,
        CONF_TIER_4_COUNT: (total_minutes - 1440) // 60,
        CONF_TIER_4_DURATION: 60,
    }


HORIZON_PRESETS: Final[dict[str, dict[str, int]]] = {
    HORIZON_PRESET_2_DAYS: _create_horizon_preset(2),
    HORIZON_PRESET_3_DAYS: _create_horizon_preset(3),
    HORIZON_PRESET_5_DAYS: _create_horizon_preset(5),
    HORIZON_PRESET_7_DAYS: _create_horizon_preset(7),
}


def get_tier_config_for_preset(preset: str) -> dict[str, int]:
    """Return tier configuration for a standard day preset."""
    return dict(HORIZON_PRESETS[preset])


def get_hub_setup_schema(suggested_name: str | None = None) -> vol.Schema:
    """Get simplified schema for initial hub setup."""
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
            CONF_HORIZON: (
                vol.Required(CONF_HORIZON, default=HORIZON_PRESET_5_DAYS),
                build_horizon_choose_selector(),
            ),
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
    """Get simplified schema for hub options (edit) flow."""
    common_data = config_entry.data.get(HUB_SECTION_COMMON, {})
    advanced_data = config_entry.data.get(HUB_SECTION_ADVANCED, {})
    preferred = get_horizon_preferred_choice(common_data)
    horizon_default = horizon_config_to_form_default(common_data)

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
            CONF_HORIZON: (
                vol.Required(CONF_HORIZON, default=horizon_default),
                build_horizon_choose_selector(preferred_choice=preferred),
            ),
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


def build_hub_entry_data(
    user_input: dict[str, Any],
    *,
    hub_name: str,
    existing_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build hub config entry data from validated flow input."""
    common_input = user_input[HUB_SECTION_COMMON]
    horizon_value = stored_horizon_from_common(common_input)

    base = dict(existing_data) if existing_data else {}
    common_section: dict[str, Any] = {
        CONF_NAME: hub_name,
        CONF_HORIZON: horizon_value,
    }

    if is_horizon_entity_value(horizon_value):
        tiers_section: dict[str, int] = {}
    else:
        preset = horizon_value["value"]
        if preset == HORIZON_PRESET_CUSTOM:
            tiers_section = dict(base.get(HUB_SECTION_TIERS, {}))
        else:
            tiers_section = get_tier_config_for_preset(preset)

    return {
        **{key: value for key, value in base.items() if key not in (HUB_SECTION_COMMON, HUB_SECTION_TIERS)},
        HUB_SECTION_COMMON: common_section,
        HUB_SECTION_TIERS: tiers_section,
        HUB_SECTION_ADVANCED: {
            **base.get(HUB_SECTION_ADVANCED, {}),
            **user_input.get(HUB_SECTION_ADVANCED, {}),
            CONF_DEBOUNCE_SECONDS: user_input.get(HUB_SECTION_ADVANCED, {}).get(
                CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS
            ),
            CONF_ADVANCED_MODE: user_input.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False),
        },
        CONF_RECORD_FORECASTS: user_input.get(HUB_SECTION_ADVANCED, {}).get(CONF_RECORD_FORECASTS, False),
    }


def get_element_flow_classes() -> dict[ElementType, type]:
    """Return mapping of element types to their config flow handler classes."""
    from custom_components.haeo.core.schema.elements import ElementType  # noqa: PLC0415
    from custom_components.haeo.flows.elements.battery import BatterySubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.battery_section import BatterySectionSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.connection import ConnectionSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.grid import GridSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.flows.elements.inverter import InverterSubentryFlowHandler  # noqa: PLC0415
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
        ElementType.NODE: NodeSubentryFlowHandler,
        ElementType.POLICY: PolicySubentryFlowHandler,
        ElementType.SOLAR: SolarSubentryFlowHandler,
    }
