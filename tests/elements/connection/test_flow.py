"""Tests for connection element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import battery, grid, node
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET, ELEMENT_TYPE

from ..conftest import add_participant, create_flow


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

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Existing Connection",
        CONF_SOURCE: "Battery1",
        CONF_TARGET: "Grid1",
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Existing Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
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
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Old Connection",
        CONF_SOURCE: "DeletedBattery",  # This element no longer exists
        CONF_TARGET: "Grid1",
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Old Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
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


async def test_reconfigure_with_string_entity_id_v010_format(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with v0.1.0 string entity ID should show entity in defaults."""
    add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    # Create existing entry with v0.1.0 format: string entity IDs (not list, not scalar)
    from custom_components.haeo.elements.connection import CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Connection",
        CONF_SOURCE: "Battery1",
        CONF_TARGET: "Grid1",
        CONF_MAX_POWER_SOURCE_TARGET: "sensor.max_power_st",  # v0.1.0: single string entity ID
        CONF_MAX_POWER_TARGET_SOURCE: "sensor.max_power_ts",  # v0.1.0: single string entity ID
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form (user_input=None)
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Check defaults - should have the string entity IDs wrapped in lists
    defaults = flow._build_step1_defaults("Test Connection", dict(existing_subentry.data))

    # Defaults should contain the original entity IDs as lists
    assert defaults[CONF_MAX_POWER_SOURCE_TARGET] == ["sensor.max_power_st"]
    assert defaults[CONF_MAX_POWER_TARGET_SOURCE] == ["sensor.max_power_ts"]


async def test_reconfigure_with_scalar_value_shows_configurable_entity(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with scalar value should show configurable entity in defaults."""
    from custom_components.haeo.elements.connection import CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE
    from custom_components.haeo.flows.field_schema import get_configurable_entity_id

    add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    # Create existing entry with scalar values (from configurable entity setup)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Connection",
        CONF_SOURCE: "Battery1",
        CONF_TARGET: "Grid1",
        CONF_MAX_POWER_SOURCE_TARGET: 10.0,  # Scalar value
        CONF_MAX_POWER_TARGET_SOURCE: 10.0,  # Scalar value
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults - should resolve to configurable entity since no HAEO entity exists
    defaults = flow._build_step1_defaults("Test Connection", dict(existing_subentry.data))

    # Without a registered HAEO entity, resolves to configurable entity
    configurable_entity_id = get_configurable_entity_id()
    assert defaults[CONF_MAX_POWER_SOURCE_TARGET] == [configurable_entity_id]
    assert defaults[CONF_MAX_POWER_TARGET_SOURCE] == [configurable_entity_id]
