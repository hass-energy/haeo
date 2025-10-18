"""Test hub options flow for network configuration."""

from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_HORIZON_HOURS,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_OPTIMIZER,
    CONF_PERIOD_MINUTES,
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
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 5,
            CONF_OPTIMIZER: "highs",
        },
    )
    entry.add_to_hass(hass)

    result = cast("FlowResultDict", await hass.config_entries.options.async_init(entry.entry_id))

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    assert result["data_schema"] is not None
    schema_keys = {vol_key.schema: vol_key for vol_key in result["data_schema"].schema}
    assert schema_keys[CONF_HORIZON_HOURS].default() == 24
    assert schema_keys[CONF_PERIOD_MINUTES].default() == 5
    assert schema_keys[CONF_OPTIMIZER].default() == "highs"


async def test_options_flow_configure_network_success(hass: HomeAssistant) -> None:
    """Test successful network configuration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 5,
            CONF_OPTIMIZER: "highs",
        },
    )
    entry.add_to_hass(hass)

    result = cast("FlowResultDict", await hass.config_entries.options.async_init(entry.entry_id))
    assert result["type"] == FlowResultType.FORM

    result = cast(
        "FlowResultDict",
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HORIZON_HOURS: 48,
                CONF_PERIOD_MINUTES: 15,
                CONF_OPTIMIZER: "pulp_cbc_cmd",
            },
        ),
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_HORIZON_HOURS] == 48
    assert entry.data[CONF_PERIOD_MINUTES] == 15
    assert entry.data[CONF_OPTIMIZER] == "pulp_cbc_cmd"
