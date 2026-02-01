"""Tests for battery_section element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    SECTION_BASIC,
    SECTION_STORAGE,
)

from ..conftest import create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat battery section input values into sectioned config."""
    if SECTION_BASIC in flat:
        return dict(flat)
    return {
        SECTION_BASIC: {CONF_NAME: flat[CONF_NAME]},
        SECTION_STORAGE: {
            CONF_CAPACITY: flat[CONF_CAPACITY],
            CONF_INITIAL_CHARGE: flat[CONF_INITIAL_CHARGE],
        },
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat battery section config values into sectioned config with element type."""
    if SECTION_BASIC in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **_wrap_input(flat)}


async def test_reconfigure_shows_form(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Battery section reconfigure should show user form."""
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: 10.0,
            CONF_INITIAL_CHARGE: 5.0,
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - entity-first pattern uses step_id="user"
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_reconfigure_with_entity_links(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Battery section reconfigure should handle entity link values."""
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: "sensor.capacity",  # Entity link (string)
            CONF_INITIAL_CHARGE: 5.0,  # Scalar
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
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
    """Reconfigure with v0.1.0 string entity ID should show entity choice in defaults."""
    # Create existing entry with v0.1.0 format: string entity IDs (not list, not scalar)
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: "sensor.section_capacity",  # v0.1.0: single string entity ID
            CONF_INITIAL_CHARGE: "sensor.section_charge",  # v0.1.0: single string entity ID
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
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
    defaults = flow._build_defaults("Test Battery Section", dict(existing_subentry.data))

    # Defaults should contain entity choice with the original entity IDs as lists
    assert defaults[SECTION_STORAGE][CONF_CAPACITY] == ["sensor.section_capacity"]
    assert defaults[SECTION_STORAGE][CONF_INITIAL_CHARGE] == ["sensor.section_charge"]


async def test_reconfigure_with_scalar_shows_constant_defaults(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with scalar value should show constant choice in defaults."""
    # Create existing entry with scalar values (from constant config)
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: 10.0,  # Scalar value
            CONF_INITIAL_CHARGE: 5.0,  # Scalar value
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults - should resolve to constant choice with scalar values
    defaults = flow._build_defaults("Test Battery Section", dict(existing_subentry.data))

    # Defaults should contain constant choice with the scalar values
    assert defaults[SECTION_STORAGE][CONF_CAPACITY] == 10.0
    assert defaults[SECTION_STORAGE][CONF_INITIAL_CHARGE] == 5.0


async def test_reconfigure_with_missing_field_shows_none_default(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with missing optional field should show None in defaults."""
    # Create existing entry with only some fields (simulating optional field not set)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        SECTION_BASIC: {CONF_NAME: "Test Battery Section"},
        SECTION_STORAGE: {
            CONF_CAPACITY: 10.0,  # Only capacity set
            # CONF_INITIAL_CHARGE intentionally missing to test else branch
        },
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery Section",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults - missing field should show None
    defaults = flow._build_defaults("Test Battery Section", dict(existing_subentry.data))

    # Missing field should result in None default
    assert defaults.get(SECTION_STORAGE, {}).get(CONF_INITIAL_CHARGE) is None


async def test_user_step_with_constant_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with constant values should create entry directly."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Battery Section",
            "data": {},
        }
    )

    # Submit with constant values using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: 10.0,
            CONF_INITIAL_CHARGE: 5.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == 10.0
    assert create_kwargs["data"][SECTION_STORAGE][CONF_INITIAL_CHARGE] == 5.0


async def test_user_step_with_entity_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with entity selections should create entry with entity IDs."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Battery Section",
            "data": {},
        }
    )

    # Submit with entity selections
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: ["sensor.capacity"],
            CONF_INITIAL_CHARGE: ["sensor.charge"],
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity IDs as strings (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == "sensor.capacity"
    assert create_kwargs["data"][SECTION_STORAGE][CONF_INITIAL_CHARGE] == "sensor.charge"


async def test_user_step_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with empty required field should show validation error."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit with empty capacity (required field)
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: [],  # Empty list = invalid
            CONF_INITIAL_CHARGE: 5.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert CONF_CAPACITY in result.get("errors", {})


# --- Tests for _is_valid_choose_value ---
