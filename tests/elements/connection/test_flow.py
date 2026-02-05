"""Tests for connection element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import battery, grid, node
from custom_components.haeo.elements.connection import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_ENDPOINTS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value

from ..conftest import add_participant, create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat connection input values into sectioned config."""
    if SECTION_COMMON in flat:
        return dict(flat)
    common = {
        CONF_NAME: flat[CONF_NAME],
    }
    endpoints = {
        CONF_SOURCE: flat[CONF_SOURCE],
        CONF_TARGET: flat[CONF_TARGET],
    }
    limits = {key: flat[key] for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE) if key in flat}
    return {
        SECTION_COMMON: common,
        SECTION_ENDPOINTS: endpoints,
        SECTION_POWER_LIMITS: limits,
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat connection config values into sectioned config with element type."""
    if SECTION_COMMON in flat:
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


async def test_reconfigure_with_deleted_participant(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Connection reconfigure should include deleted participant in options."""
    # Add only one participant (the target)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    # Create connection that references a deleted source
    existing_config = _wrap_config(
        {
            CONF_NAME: "Old Connection",
            CONF_SOURCE: "DeletedBattery",  # This element no longer exists
            CONF_TARGET: "Grid1",
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Old Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - should not error
    # Entity-first pattern uses step_id="user" for both new and reconfigure
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    # The form should be shown without errors


async def test_get_participant_names_skips_unknown_element_types(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_participant_names should skip subentries with unknown element types."""
    # Add a valid participant
    add_participant(hass, hub_entry, "ValidNode", node.ELEMENT_TYPE)

    # Add a subentry with unknown element type
    unknown_data = MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"})
    unknown_subentry = ConfigSubentry(
        data=unknown_data,
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Get participant names - should only include ValidNode
    participants = flow._get_participant_names()

    assert "ValidNode" in participants
    assert "Unknown" not in participants


async def test_get_subentry_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_subentry should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # During user flow, _get_reconfigure_subentry will raise
    subentry = flow._get_subentry()

    assert subentry is None


async def test_reconfigure_with_entity_value_shows_defaults(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with entity schema value should show entity choice in defaults."""
    add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    # Create existing entry with entity schema values
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Connection",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
            CONF_MAX_POWER_SOURCE_TARGET: as_entity_value(["sensor.max_power_st"]),
            CONF_MAX_POWER_TARGET_SOURCE: as_entity_value(["sensor.max_power_ts"]),
        }
    )
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

    # Show reconfigure form (user_input=None)
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Check defaults - should have entity choice with the string entity IDs wrapped in lists
    defaults = flow._build_defaults("Test Connection", dict(existing_subentry.data))

    # Defaults should contain entity choice with the original entity IDs as lists
    assert defaults[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == ["sensor.max_power_st"]
    assert defaults[SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == ["sensor.max_power_ts"]


async def test_reconfigure_with_scalar_shows_constant_defaults(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with scalar value should show constant choice in defaults."""
    add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    # Create existing entry with constant schema values
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Connection",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
            CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
            CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(10.0),
        }
    )
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

    # Check defaults - should resolve to constant choice with scalar values
    defaults = flow._build_defaults("Test Connection", dict(existing_subentry.data))

    # Defaults should contain constant choice with scalar values
    assert defaults[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == 10.0
    assert defaults[SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == 10.0


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
    assert create_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_entity_value(["sensor.power_st"])
    assert create_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_entity_value(["sensor.power_ts"])
