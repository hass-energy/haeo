"""Test hub options flow for network configuration."""

from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_DURATION,
    CONF_TIER_1_UNTIL,
    CONF_TIER_2_DURATION,
    CONF_TIER_2_UNTIL,
    CONF_TIER_3_DURATION,
    CONF_TIER_3_UNTIL,
    CONF_TIER_4_DURATION,
    CONF_TIER_4_UNTIL,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_1_UNTIL,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_2_UNTIL,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_3_UNTIL,
    DEFAULT_TIER_4_DURATION,
    DEFAULT_TIER_4_UNTIL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)

type FlowResultDict = dict[str, Any]


async def test_options_flow_init(hass: HomeAssistant) -> None:
    """Test options flow initialization."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_UNTIL: DEFAULT_TIER_1_UNTIL,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_UNTIL: DEFAULT_TIER_2_UNTIL,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_UNTIL: DEFAULT_TIER_3_UNTIL,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_UNTIL: DEFAULT_TIER_4_UNTIL,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
    )
    entry.add_to_hass(hass)

    result = cast("FlowResultDict", await hass.config_entries.options.async_init(entry.entry_id))

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    assert result["data_schema"] is not None
    schema_keys = {vol_key.schema: vol_key for vol_key in result["data_schema"].schema}
    assert schema_keys[CONF_TIER_1_UNTIL].default() == DEFAULT_TIER_1_UNTIL
    assert schema_keys[CONF_TIER_1_DURATION].default() == DEFAULT_TIER_1_DURATION


async def test_options_flow_configure_network_success(hass: HomeAssistant) -> None:
    """Test successful network configuration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_UNTIL: DEFAULT_TIER_1_UNTIL,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_UNTIL: DEFAULT_TIER_2_UNTIL,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_UNTIL: DEFAULT_TIER_3_UNTIL,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_UNTIL: DEFAULT_TIER_4_UNTIL,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
    )
    entry.add_to_hass(hass)

    result = cast("FlowResultDict", await hass.config_entries.options.async_init(entry.entry_id))
    assert result["type"] == FlowResultType.FORM

    # Test updating tier 1 configuration
    result = cast(
        "FlowResultDict",
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_TIER_1_UNTIL: 10,
                CONF_TIER_1_DURATION: 2,
                CONF_TIER_2_UNTIL: DEFAULT_TIER_2_UNTIL,
                CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
                CONF_TIER_3_UNTIL: DEFAULT_TIER_3_UNTIL,
                CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
                CONF_TIER_4_UNTIL: DEFAULT_TIER_4_UNTIL,
                CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
                CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
                CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
            },
        ),
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_TIER_1_UNTIL] == 10
    assert entry.data[CONF_TIER_1_DURATION] == 2
