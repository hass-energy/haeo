"""Tests for inverter element config flow."""

from types import MappingProxyType
from typing import Any, cast
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.inverter import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    ELEMENT_TYPE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements import get_input_fields
from tests.conftest import add_participant

from .conftest import create_flow

CONF_MAX_POWER_DC_TO_AC = CONF_MAX_POWER_SOURCE_TARGET
CONF_MAX_POWER_AC_TO_DC = CONF_MAX_POWER_TARGET_SOURCE
SECTION_LIMITS = SECTION_POWER_LIMITS


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat inverter input values into sectioned config."""
    if SECTION_COMMON in flat:
        return dict(flat)
    common = {
        CONF_NAME: flat[CONF_NAME],
        CONF_CONNECTION: flat[CONF_CONNECTION],
    }
    limits = {
        CONF_MAX_POWER_DC_TO_AC: flat[CONF_MAX_POWER_DC_TO_AC],
        CONF_MAX_POWER_AC_TO_DC: flat[CONF_MAX_POWER_AC_TO_DC],
    }
    return {
        SECTION_COMMON: common,
        SECTION_LIMITS: limits,
        SECTION_EFFICIENCY: {},
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat inverter config values into sectioned config with element type."""
    if SECTION_COMMON in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    config = _wrap_input(flat)
    common = config.get(SECTION_COMMON, {})
    if CONF_CONNECTION in common and isinstance(common[CONF_CONNECTION], str):
        common[CONF_CONNECTION] = as_connection_target(common[CONF_CONNECTION])
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **config}


@pytest.mark.parametrize(
    ("config_values", "expected_defaults", "add_node"),
    [
        pytest.param(
            {
                CONF_NAME: "Test Inverter",
                CONF_CONNECTION: "TestNode",
                CONF_MAX_POWER_DC_TO_AC: as_entity_value(["sensor.dc_to_ac_power"]),
                CONF_MAX_POWER_AC_TO_DC: as_entity_value(["sensor.ac_to_dc_power"]),
            },
            {
                CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_to_ac_power"],
                CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_to_dc_power"],
            },
            True,
            id="entity_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Inverter",
                CONF_CONNECTION: "TestNode",
                CONF_MAX_POWER_DC_TO_AC: as_constant_value(10.0),
                CONF_MAX_POWER_AC_TO_DC: as_constant_value(8.0),
            },
            {
                CONF_MAX_POWER_DC_TO_AC: 10.0,
                CONF_MAX_POWER_AC_TO_DC: 8.0,
            },
            True,
            id="constant_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Inverter",
                CONF_CONNECTION: "TestNode",
                CONF_MAX_POWER_DC_TO_AC: as_entity_value(["sensor.dc1", "sensor.dc2"]),
                CONF_MAX_POWER_AC_TO_DC: as_entity_value(["sensor.ac"]),
            },
            {
                CONF_MAX_POWER_DC_TO_AC: ["sensor.dc1", "sensor.dc2"],
                CONF_MAX_POWER_AC_TO_DC: ["sensor.ac"],
            },
            True,
            id="entity_list",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Inverter",
                CONF_CONNECTION: "DeletedNode",
                CONF_MAX_POWER_DC_TO_AC: as_constant_value(10.0),
                CONF_MAX_POWER_AC_TO_DC: as_constant_value(8.0),
            },
            {
                CONF_MAX_POWER_DC_TO_AC: 10.0,
                CONF_MAX_POWER_AC_TO_DC: 8.0,
            },
            False,
            id="deleted_connection",
        ),
    ],
)
async def test_reconfigure_defaults_handle_schema_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    config_values: dict[str, Any],
    expected_defaults: dict[str, object],
    add_node: bool,
) -> None:
    """Reconfigure defaults reflect schema values and missing participants."""
    if add_node:
        add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    unknown_data = MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"})
    unknown_subentry = ConfigSubentry(
        data=unknown_data,
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    existing_config = _wrap_config(config_values)
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    participants = flow._get_participant_names()
    assert "Unknown" not in participants

    result = await flow.async_step_reconfigure(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_defaults("Test Inverter", input_fields, dict(existing_subentry.data))
    assert defaults[SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == expected_defaults[CONF_MAX_POWER_DC_TO_AC]
    assert defaults[SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == expected_defaults[CONF_MAX_POWER_AC_TO_DC]


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
            "title": "Test Inverter",
            "data": {},
        }
    )

    assert flow._get_current_subentry_id() is None

    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: [],
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    invalid_result = await flow.async_step_user(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert CONF_MAX_POWER_DC_TO_AC in invalid_result.get("errors", {})

    # Submit with constant values using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: 10.0,
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == as_constant_value(10.0)
    assert create_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == as_constant_value(8.0)


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
            "title": "Test Inverter",
            "data": {},
        }
    )

    # Submit with entity selections
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_power"],
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity schema values (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == as_entity_value(["sensor.dc_power"])
    assert create_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == as_entity_value(["sensor.ac_power"])


# --- Tests for reconfigure flow ---


async def test_reconfigure_with_constant_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with constant values should update entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: as_entity_value(["sensor.dc_power"]),
            CONF_MAX_POWER_AC_TO_DC: as_entity_value(["sensor.ac_power"]),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: [],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_power"],
        }
    )
    invalid_result = await flow.async_step_reconfigure(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert CONF_MAX_POWER_DC_TO_AC in invalid_result.get("errors", {})

    # Change to constant values
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: 10.0,
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config contains the constant values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == as_constant_value(10.0)
    assert update_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == as_constant_value(8.0)


async def test_reconfigure_selecting_entity_stores_entity_id(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting entity in reconfigure stores the entity ID."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with constant schema values
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: as_constant_value(10.0),
            CONF_MAX_POWER_AC_TO_DC: as_constant_value(8.0),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    # Register HAEO number entities in entity registry
    registry = er.async_get(hass)
    dc_to_ac_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_MAX_POWER_DC_TO_AC}",
        suggested_object_id="test_inverter_max_power_dc_to_ac",
    )
    ac_to_dc_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_MAX_POWER_AC_TO_DC}",
        suggested_object_id="test_inverter_max_power_ac_to_dc",
    )

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # User selects entities using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: [dc_to_ac_entity.entity_id],
            CONF_MAX_POWER_AC_TO_DC: [ac_to_dc_entity.entity_id],
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    # Should complete
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # When entity mode is selected, the entity ID is stored
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == as_entity_value(
        [dc_to_ac_entity.entity_id]
    )
    assert update_kwargs["data"][SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == as_entity_value(
        [ac_to_dc_entity.entity_id]
    )


# --- Tests for _is_valid_choose_value ---
