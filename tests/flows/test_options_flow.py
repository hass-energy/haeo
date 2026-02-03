"""Test hub options flow for network configuration."""

from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_PRESET,
    CONF_INTEGRATION_TYPE,
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
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.flows import (
    HORIZON_PRESET_3_DAYS,
    HORIZON_PRESET_5_DAYS,
    HORIZON_PRESET_CUSTOM,
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
    """Test options flow initialization shows preset dropdown."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Hub",
                CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS,
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
    # Verify preset dropdown is shown with current value as default
    assert CONF_HORIZON_PRESET in schema_keys
    assert schema_keys[CONF_HORIZON_PRESET].default() == HORIZON_PRESET_5_DAYS


async def test_options_flow_select_preset(hass: HomeAssistant) -> None:
    """Test selecting a preset applies the correct tier values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Hub",
                CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS,
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

    # Select 3 days preset
    result = cast(
        "FlowResultDict",
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=_wrap_options_input(
                {CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS},
                {CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS},
            ),
        ),
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Verify preset is stored
    assert entry.data[HUB_SECTION_COMMON][CONF_HORIZON_PRESET] == HORIZON_PRESET_3_DAYS
    # Verify tier values match the 3 days preset
    preset_config = HORIZON_PRESETS[HORIZON_PRESET_3_DAYS]
    assert entry.data[HUB_SECTION_TIERS][CONF_TIER_4_COUNT] == preset_config[CONF_TIER_4_COUNT]


async def test_options_flow_custom_tiers(hass: HomeAssistant) -> None:
    """Test selecting custom preset shows custom tier configuration step."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Hub",
                CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS,
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

    # Select custom preset - should go to custom_tiers step
    result = cast(
        "FlowResultDict",
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=_wrap_options_input(
                {CONF_HORIZON_PRESET: HORIZON_PRESET_CUSTOM},
                {CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS},
            ),
        ),
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "custom_tiers"

    # Configure custom tier values
    result = cast(
        "FlowResultDict",
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_TIER_1_COUNT: 10,
                CONF_TIER_1_DURATION: 2,
                CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
                CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
                CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
                CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
                CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
                CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
            },
        ),
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[HUB_SECTION_COMMON][CONF_HORIZON_PRESET] == HORIZON_PRESET_CUSTOM
    assert entry.data[HUB_SECTION_TIERS][CONF_TIER_1_COUNT] == 10
    assert entry.data[HUB_SECTION_TIERS][CONF_TIER_1_DURATION] == 2
