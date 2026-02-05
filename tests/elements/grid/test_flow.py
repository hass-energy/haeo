"""Tests for grid element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import node
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    ELEMENT_TYPE,
    SECTION_COMMON,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.schema import as_constant_value, as_entity_value

from ..conftest import add_participant, create_flow

CONF_IMPORT_PRICE = CONF_PRICE_SOURCE_TARGET
CONF_EXPORT_PRICE = CONF_PRICE_TARGET_SOURCE
CONF_IMPORT_LIMIT = CONF_MAX_POWER_SOURCE_TARGET
CONF_EXPORT_LIMIT = CONF_MAX_POWER_TARGET_SOURCE
SECTION_LIMITS = SECTION_POWER_LIMITS


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat grid input values into sectioned config."""
    if SECTION_COMMON in flat:
        return dict(flat)
    common = {
        CONF_NAME: flat[CONF_NAME],
        CONF_CONNECTION: flat[CONF_CONNECTION],
    }
    pricing = {
        CONF_PRICE_SOURCE_TARGET: flat[CONF_PRICE_SOURCE_TARGET],
        CONF_PRICE_TARGET_SOURCE: flat[CONF_PRICE_TARGET_SOURCE],
    }
    power_limits = {key: flat[key] for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE) if key in flat}
    return {
        SECTION_COMMON: common,
        SECTION_PRICING: pricing,
        SECTION_POWER_LIMITS: power_limits,
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat grid config values into sectioned config with element type."""
    if SECTION_COMMON in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **_wrap_input(flat)}


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Grid reconfigure should include deleted connection target in options."""
    # Create grid that references a deleted connection target
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "DeletedNode",  # This node no longer exists
            CONF_IMPORT_PRICE: as_constant_value(0.30),
            CONF_EXPORT_PRICE: as_constant_value(0.05),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - should not error
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


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


async def test_get_current_subentry_id_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_current_subentry_id should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # During user flow, _get_reconfigure_subentry will raise
    subentry_id = flow._get_current_subentry_id()

    assert subentry_id is None


# --- Tests for validation errors ---


async def test_user_step_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with empty required choose field should show required error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit with empty import_price (required field) - entity choice with empty list
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: [],
            CONF_EXPORT_PRICE: 0.05,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


# --- Tests for single-step flow with choose selector ---


async def test_user_step_with_constant_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with constant values should create entry directly."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Grid",
            "data": {},
        }
    )

    # Submit with constant values using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: 0.25,
            CONF_EXPORT_PRICE: 0.05,
            CONF_IMPORT_LIMIT: 10.0,
            CONF_EXPORT_LIMIT: 10.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant schema values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_PRICING][CONF_IMPORT_PRICE] == as_constant_value(0.25)
    assert create_kwargs["data"][SECTION_PRICING][CONF_EXPORT_PRICE] == as_constant_value(0.05)


async def test_user_step_with_entity_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with entity selections should create entry with entity IDs."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Grid",
            "data": {},
        }
    )

    # Submit with entity selections
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
            CONF_IMPORT_LIMIT: 10.0,
            CONF_EXPORT_LIMIT: 10.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity schema values (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_PRICING][CONF_IMPORT_PRICE] == as_entity_value(["sensor.import_price"])
    assert create_kwargs["data"][SECTION_PRICING][CONF_EXPORT_PRICE] == as_entity_value(["sensor.export_price"])


# --- Tests for reconfigure flow ---


async def test_reconfigure_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with empty required field should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: as_constant_value(0.30),
            CONF_EXPORT_PRICE: as_constant_value(0.05),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Submit with empty import_price (required field)
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: [],
            CONF_EXPORT_PRICE: 0.05,
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    # Should show reconfigure form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


async def test_reconfigure_with_constant_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with constant values should update entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with entity links
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: as_entity_value(["sensor.import"]),
            CONF_EXPORT_PRICE: as_entity_value(["sensor.export"]),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # Change to constant values
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: 0.30,
            CONF_EXPORT_PRICE: 0.08,
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config contains the constant values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][SECTION_PRICING][CONF_IMPORT_PRICE] == as_constant_value(0.30)
    assert update_kwargs["data"][SECTION_PRICING][CONF_EXPORT_PRICE] == as_constant_value(0.08)


async def test_reconfigure_with_scalar_shows_constant_defaults(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with scalar values should show constant choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values (from prior constant config)
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: as_constant_value(0.30),
            CONF_EXPORT_PRICE: as_constant_value(0.08),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
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

    # Check defaults - should have constant choice with scalar values
    defaults = flow._build_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain constant choice with values
    assert defaults[SECTION_PRICING][CONF_IMPORT_PRICE] == 0.30
    assert defaults[SECTION_PRICING][CONF_EXPORT_PRICE] == 0.08


async def test_reconfigure_with_entity_value_shows_entity_defaults(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with entity schema value should show entity choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with entity schema values
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: as_entity_value(["sensor.import_price"]),
            CONF_EXPORT_PRICE: as_entity_value(["sensor.export_price"]),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
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
    defaults = flow._build_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain entity choice with the original entity IDs as lists
    assert defaults[SECTION_PRICING][CONF_IMPORT_PRICE] == ["sensor.import_price"]
    assert defaults[SECTION_PRICING][CONF_EXPORT_PRICE] == ["sensor.export_price"]


async def test_reconfigure_with_entity_list(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with entity list should show entity choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with entity schema values
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: as_entity_value(["sensor.import1", "sensor.import2"]),
            CONF_EXPORT_PRICE: as_entity_value(["sensor.export"]),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults
    defaults = flow._build_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain entity choice with the entity lists
    assert defaults[SECTION_PRICING][CONF_IMPORT_PRICE] == ["sensor.import1", "sensor.import2"]
    assert defaults[SECTION_PRICING][CONF_EXPORT_PRICE] == ["sensor.export"]


# --- Tests for _is_valid_choose_value ---
