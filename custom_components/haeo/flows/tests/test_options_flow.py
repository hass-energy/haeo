"""Test hub options flow for network configuration."""

from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import (
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
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
)
from custom_components.haeo.core.schema import as_horizon_preset_value, is_horizon_preset_value
from custom_components.haeo.flows import (
    HORIZON_PRESET_3_DAYS,
    HORIZON_PRESET_5_DAYS,
    HORIZON_PRESETS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)

type FlowResultDict = dict[str, Any]


def _wrap_options_input(
    common: dict[str, Any],
    advanced: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap options input values into sectioned form data."""
    return {
        HUB_SECTION_COMMON: common,
        HUB_SECTION_ADVANCED: advanced or {},
    }


def _get_section_schema(data_schema: Any, key: str) -> vol.Schema:
    """Return the schema for a specific section key."""
    section_map = {marker.schema: section for marker, section in data_schema.schema.items()}
    return section_map[key].schema


async def test_options_flow_init(hass: HomeAssistant) -> None:
    """Test options flow initialization shows horizon choose selector."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Hub",
                CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_5_DAYS),
            },
            HUB_SECTION_TIERS: {
                CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
                CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
                CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
                CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
                CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
                CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
                CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
                CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
            },
            HUB_SECTION_ADVANCED: {
                CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
            },
        },
    )
    entry.add_to_hass(hass)

    result = cast("FlowResultDict", await hass.config_entries.options.async_init(entry.entry_id))

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    assert result["data_schema"] is not None
    common_schema = _get_section_schema(result["data_schema"], HUB_SECTION_COMMON)
    schema_keys = {vol_key.schema: vol_key for vol_key in common_schema.schema}
    assert CONF_HORIZON in schema_keys
    assert schema_keys[CONF_HORIZON].default() == HORIZON_PRESET_5_DAYS


async def test_options_flow_select_preset(hass: HomeAssistant) -> None:
    """Test selecting a preset applies the correct tier values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Hub",
                CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_5_DAYS),
            },
            HUB_SECTION_TIERS: {
                CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
                CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
                CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
                CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
                CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
                CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
                CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
                CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
            },
            HUB_SECTION_ADVANCED: {
                CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
            },
        },
    )
    entry.add_to_hass(hass)

    result = cast("FlowResultDict", await hass.config_entries.options.async_init(entry.entry_id))
    assert result["type"] == FlowResultType.FORM

    result = cast(
        "FlowResultDict",
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=_wrap_options_input(
                {CONF_HORIZON: HORIZON_PRESET_3_DAYS},
                {CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS},
            ),
        ),
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    horizon = entry.data[HUB_SECTION_COMMON][CONF_HORIZON]
    assert is_horizon_preset_value(horizon)
    assert horizon["value"] == HORIZON_PRESET_3_DAYS
    preset_config = HORIZON_PRESETS[HORIZON_PRESET_3_DAYS]
    assert entry.data[HUB_SECTION_TIERS][CONF_TIER_4_COUNT] == preset_config[CONF_TIER_4_COUNT]
