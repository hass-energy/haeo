"""Tests for battery_section element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
)

from ..conftest import create_flow


async def test_reconfigure_shows_form(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Battery section reconfigure should show user form."""
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery Section",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE: 5.0,
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - entity-first pattern uses step_id="user"
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_reconfigure_with_entity_links(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Battery section reconfigure should handle entity link values."""
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery Section",
        CONF_CAPACITY: ["sensor.capacity"],  # Entity link
        CONF_INITIAL_CHARGE: 5.0,  # Scalar
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_get_subentry_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_subentry should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # During user flow, _get_reconfigure_subentry will raise
    subentry = flow._get_subentry()

    assert subentry is None


async def test_reconfigure_with_string_entity_id_v010_format(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with v0.1.0 string entity ID should show entity in defaults."""
    # Create existing entry with v0.1.0 format: string entity IDs (not list, not scalar)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery Section",
        CONF_CAPACITY: "sensor.section_capacity",  # v0.1.0: single string entity ID
        CONF_INITIAL_CHARGE: "sensor.section_charge",  # v0.1.0: single string entity ID
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
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
    defaults = flow._build_step1_defaults("Test Battery Section", dict(existing_subentry.data))

    # Defaults should contain the original entity IDs as lists
    assert defaults[CONF_CAPACITY] == ["sensor.section_capacity"]
    assert defaults[CONF_INITIAL_CHARGE] == ["sensor.section_charge"]


async def test_reconfigure_with_scalar_value_shows_configurable_entity(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with scalar value should show configurable entity in defaults."""
    from custom_components.haeo.flows.field_schema import get_configurable_entity_id

    # Create existing entry with scalar values (from configurable entity setup)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery Section",
        CONF_CAPACITY: 10.0,  # Scalar value
        CONF_INITIAL_CHARGE: 5.0,  # Scalar value
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults - should resolve to configurable entity since no HAEO entity exists
    defaults = flow._build_step1_defaults("Test Battery Section", dict(existing_subentry.data))

    # Without a registered HAEO entity, resolves to configurable entity
    configurable_entity_id = get_configurable_entity_id()
    assert defaults[CONF_CAPACITY] == [configurable_entity_id]
    assert defaults[CONF_INITIAL_CHARGE] == [configurable_entity_id]


async def test_reconfigure_with_missing_field_shows_empty_selection(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with missing optional field should show empty selection in defaults."""
    # Create existing entry with only some fields (simulating optional field not set)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery Section",
        CONF_CAPACITY: 10.0,  # Only capacity set
        # CONF_INITIAL_CHARGE intentionally missing to test else branch
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults - missing field should show empty selection
    defaults = flow._build_step1_defaults("Test Battery Section", dict(existing_subentry.data))

    # Missing field should result in empty selection
    assert defaults[CONF_INITIAL_CHARGE] == []
