"""Tests for connection element config flow."""

from types import MappingProxyType
from typing import Any, cast
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import battery, grid, node
from custom_components.haeo.core.schema.elements.connection import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_EFFICIENCY,
    SECTION_ENDPOINTS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.flows.conftest import create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat connection input values into sectioned config."""
    if SECTION_ENDPOINTS in flat:
        return dict(flat)
    endpoints = {
        CONF_SOURCE: flat[CONF_SOURCE],
        CONF_TARGET: flat[CONF_TARGET],
    }
    limits = {key: flat[key] for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE) if key in flat}
    return {
        CONF_NAME: flat[CONF_NAME],
        SECTION_ENDPOINTS: endpoints,
        SECTION_POWER_LIMITS: limits,
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat connection config values into sectioned config with element type."""
    if SECTION_ENDPOINTS in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    config = _wrap_input(flat)
    endpoints = config.get(SECTION_ENDPOINTS, {})
    for key in (CONF_SOURCE, CONF_TARGET):
        if key in endpoints and isinstance(endpoints[key], str):
            endpoints[key] = as_connection_target(endpoints[key])
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **config}


async def test_flow_source_equals_target_error(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Connection flow should error when source equals target."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit with source == target
    result = await flow.async_step_user(
        user_input={
            CONF_NAME: "Test Connection",
            CONF_SOURCE: "Node1",
            CONF_TARGET: "Node1",
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_TARGET: "cannot_connect_to_self"}


async def test_reconfigure_source_equals_target_error(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Connection reconfigure should error when source equals target."""
    add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    existing_config = _wrap_config(
        {
            CONF_NAME: "Existing Connection",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Existing Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Submit with source == target
    result = await flow.async_step_reconfigure(
        user_input={
            CONF_NAME: "Existing Connection",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Battery1",
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_TARGET: "cannot_connect_to_self"}


def test_build_config_normalizes_endpoints(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_config normalizes endpoint strings into connection targets."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    user_input = _wrap_input(
        {
            CONF_NAME: "Test Connection",
            CONF_SOURCE: "Node1",
            CONF_TARGET: "Node2",
        }
    )

    config = flow._build_config(user_input)

    endpoints = config[SECTION_ENDPOINTS]
    assert endpoints[CONF_SOURCE] == as_connection_target("Node1")
    assert endpoints[CONF_TARGET] == as_connection_target("Node2")


@pytest.mark.parametrize(
    ("source", "target", "add_source", "config_values", "expected_defaults"),
    [
        pytest.param(
            "Battery1",
            "Grid1",
            True,
            {
                CONF_NAME: "Test Connection",
                CONF_SOURCE: "Battery1",
                CONF_TARGET: "Grid1",
                CONF_MAX_POWER_SOURCE_TARGET: as_entity_value(["sensor.max_power_st"]),
                CONF_MAX_POWER_TARGET_SOURCE: as_entity_value(["sensor.max_power_ts"]),
            },
            {
                CONF_MAX_POWER_SOURCE_TARGET: ["sensor.max_power_st"],
                CONF_MAX_POWER_TARGET_SOURCE: ["sensor.max_power_ts"],
            },
            id="entity_values",
        ),
        pytest.param(
            "DeletedBattery",
            "Grid1",
            False,
            {
                CONF_NAME: "Test Connection",
                CONF_SOURCE: "DeletedBattery",
                CONF_TARGET: "Grid1",
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(10.0),
            },
            {
                CONF_MAX_POWER_SOURCE_TARGET: 10.0,
                CONF_MAX_POWER_TARGET_SOURCE: 10.0,
            },
            id="constant_values_deleted_source",
        ),
    ],
)
async def test_reconfigure_defaults_handle_schema_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    source: str,
    target: str,
    add_source: bool,
    config_values: dict[str, Any],
    expected_defaults: dict[str, Any],
) -> None:
    """Reconfigure defaults reflect schema values and tolerate missing endpoints."""
    if add_source:
        add_participant(hass, hub_entry, source, battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, target, grid.ELEMENT_TYPE)

    existing_config = _wrap_config(config_values)
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_defaults("Test Connection", input_fields, dict(existing_subentry.data))

    for key, expected in expected_defaults.items():
        assert defaults[SECTION_POWER_LIMITS][key] == expected


async def test_user_step_with_constant_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with constant values should create entry directly."""
    add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Connection",
            "data": {},
        }
    )

    # Submit with constant values using choose selector format
    user_input = {
        CONF_NAME: "Test Connection",
        CONF_SOURCE: "Battery1",
        CONF_TARGET: "Grid1",
        CONF_MAX_POWER_SOURCE_TARGET: 10.0,
        CONF_MAX_POWER_TARGET_SOURCE: 10.0,
    }
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(10.0)
    assert create_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(10.0)


async def test_user_step_with_entity_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with entity selections should create entry with entity IDs."""
    add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Connection",
            "data": {},
        }
    )

    # Submit with entity selections
    user_input = {
        CONF_NAME: "Test Connection",
        CONF_SOURCE: "Battery1",
        CONF_TARGET: "Grid1",
        CONF_MAX_POWER_SOURCE_TARGET: ["sensor.power_st"],
        CONF_MAX_POWER_TARGET_SOURCE: ["sensor.power_ts"],
    }
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity schema values (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_entity_value(
        ["sensor.power_st"]
    )
    assert create_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_entity_value(
        ["sensor.power_ts"]
    )
