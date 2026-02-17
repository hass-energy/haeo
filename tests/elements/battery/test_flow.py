"""Tests for battery element config flow."""

from typing import Any
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements import node
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_PRICE,
    CONF_CHARGE_VIOLATION_PRICE,
    CONF_CONFIGURE_PARTITIONS,
    CONF_CONNECTION,
    CONF_DISCHARGE_PRICE,
    CONF_DISCHARGE_VIOLATION_PRICE,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PARTITION_NAMES,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SALVAGE_VALUE,
    CONF_THRESHOLD_KWH,
    ELEMENT_TYPE,
    SECTION_PARTITIONS,
)
from custom_components.haeo.schema import as_constant_value, as_entity_value

from ..conftest import add_participant, create_flow


def _wrap_main_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Wrap battery user input into sectioned form data."""
    common = {key: user_input[key] for key in (CONF_NAME, CONF_CONNECTION) if key in user_input}
    pricing = {
        key: user_input[key]
        for key in (
            CONF_PRICE_SOURCE_TARGET,
            CONF_PRICE_TARGET_SOURCE,
            CONF_SALVAGE_VALUE,
        )
        if key in user_input
    }
    pricing.setdefault(CONF_SALVAGE_VALUE, 0.0)

    return {
        "common": common,
        "storage": {key: user_input[key] for key in (CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE) if key in user_input},
        "limits": {key: user_input[key] for key in (CONF_MIN_CHARGE_PERCENTAGE, CONF_MAX_CHARGE_PERCENTAGE) if key in user_input},
        "power_limits": {key: user_input[key] for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE) if key in user_input},
        "pricing": pricing,
        "efficiency": {key: user_input[key] for key in (CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE) if key in user_input},
        "partitioning": {key: user_input[key] for key in (CONF_CONFIGURE_PARTITIONS,) if key in user_input},
    }


def _wrap_partition_names(names: str) -> dict[str, Any]:
    return {CONF_PARTITION_NAMES: names}


def _wrap_zone_input(
    *,
    threshold_kwh: Any,
    charge_violation_price: Any = None,
    discharge_violation_price: Any = None,
    charge_price: Any = None,
    discharge_price: Any = None,
) -> dict[str, Any]:
    return {
        "zone": {
            CONF_THRESHOLD_KWH: threshold_kwh,
            CONF_CHARGE_VIOLATION_PRICE: charge_violation_price,
            CONF_DISCHARGE_VIOLATION_PRICE: discharge_violation_price,
            CONF_CHARGE_PRICE: charge_price,
            CONF_DISCHARGE_PRICE: discharge_price,
        }
    }


async def test_user_step_with_constant_values_creates_entry(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Submitting with constant values should create entry directly."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    user_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: 0.95,
        CONF_EFFICIENCY_TARGET_SOURCE: 0.95,
        CONF_MAX_POWER_TARGET_SOURCE: 5.0,
        CONF_MAX_POWER_SOURCE_TARGET: 5.0,
        CONF_PRICE_TARGET_SOURCE: 0.001,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    invalid_input = {**user_input, CONF_CAPACITY: []}
    result = await flow.async_step_user(user_input=_wrap_main_input(invalid_input))
    assert result.get("type") == FlowResultType.FORM
    assert CONF_CAPACITY in result.get("errors", {})

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data["storage"][CONF_CAPACITY] == as_constant_value(10.0)
    assert created_data["storage"][CONF_INITIAL_CHARGE_PERCENTAGE] == as_entity_value(["sensor.battery_soc"])
    assert created_data["power_limits"][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(5.0)


async def test_partition_flow_enabled_shows_partition_names_step(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When configure_partitions is True, flow proceeds to partition_names step."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_CONFIGURE_PARTITIONS: True,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(step1_input))
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partition_names"


async def test_partition_flow_two_zones_creates_entry(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Complete flow with two zones creates entry with partitions dict."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_CONFIGURE_PARTITIONS: True,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(step1_input))
    assert result.get("step_id") == "partition_names"

    result = await flow.async_step_partition_names(user_input=_wrap_partition_names("Reserve\nHeadroom"))
    assert result.get("step_id") == "partition"

    # Reserve
    result = await flow.async_step_partition(user_input=_wrap_zone_input(threshold_kwh=2.0, discharge_violation_price=0.2, charge_price=0.05))
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partition"

    # Headroom
    result = await flow.async_step_partition(user_input=_wrap_zone_input(threshold_kwh=8.0, charge_violation_price=0.1, discharge_price=0.04))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert SECTION_PARTITIONS in created_data
    partitions = created_data[SECTION_PARTITIONS]
    assert "Reserve" in partitions
    assert partitions["Reserve"][CONF_THRESHOLD_KWH] == as_constant_value(2.0)
    assert partitions["Reserve"][CONF_DISCHARGE_VIOLATION_PRICE] == as_constant_value(0.2)
    assert partitions["Reserve"][CONF_CHARGE_PRICE] == as_constant_value(0.05)
    assert "Headroom" in partitions
    assert partitions["Headroom"][CONF_THRESHOLD_KWH] == as_constant_value(8.0)
    assert partitions["Headroom"][CONF_CHARGE_VIOLATION_PRICE] == as_constant_value(0.1)
    assert partitions["Headroom"][CONF_DISCHARGE_PRICE] == as_constant_value(0.04)


async def test_partition_zone_requires_price(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Zone step requires at least one of charge/discharge price."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_CONFIGURE_PARTITIONS: True,
    }
    await flow.async_step_user(user_input=_wrap_main_input(step1_input))
    await flow.async_step_partition_names(user_input=_wrap_partition_names("Reserve"))

    result = await flow.async_step_partition(
        user_input=_wrap_zone_input(
            threshold_kwh=2.0,
            charge_violation_price=None,
            discharge_violation_price=None,
            charge_price=0.1,
            discharge_price=None,
        )
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partition"
    assert result.get("errors", {}).get("base") == "missing_zone_violation_price"
