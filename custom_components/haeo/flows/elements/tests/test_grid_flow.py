"""Tests for grid element config flow."""

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
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.grid import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    ELEMENT_TYPE,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.flows.conftest import create_flow

CONF_IMPORT_PRICE = CONF_PRICE_SOURCE_TARGET
CONF_EXPORT_PRICE = CONF_PRICE_TARGET_SOURCE
CONF_IMPORT_LIMIT = CONF_MAX_POWER_SOURCE_TARGET
CONF_EXPORT_LIMIT = CONF_MAX_POWER_TARGET_SOURCE
SECTION_LIMITS = SECTION_POWER_LIMITS


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat grid input values into sectioned config."""
    if SECTION_PRICING in flat:
        return dict(flat)
    pricing = {
        CONF_PRICE_SOURCE_TARGET: flat[CONF_PRICE_SOURCE_TARGET],
        CONF_PRICE_TARGET_SOURCE: flat[CONF_PRICE_TARGET_SOURCE],
    }
    power_limits = {
        key: flat[key] for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE) if key in flat
    }
    return {
        CONF_NAME: flat[CONF_NAME],
        CONF_CONNECTION: flat[CONF_CONNECTION],
        SECTION_PRICING: pricing,
        SECTION_POWER_LIMITS: power_limits,
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat grid config values into sectioned config with element type."""
    if SECTION_PRICING in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    config = _wrap_input(flat)
    if CONF_CONNECTION in config and isinstance(config[CONF_CONNECTION], str):
        config[CONF_CONNECTION] = as_connection_target(config[CONF_CONNECTION])
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **config}


# --- Tests for validation errors ---


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
    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: [],
            CONF_EXPORT_PRICE: 0.05,
        }
    )
    invalid_result = await flow.async_step_user(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in invalid_result.get("errors", {})

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

    # Validate required field handling
    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: [],
            CONF_EXPORT_PRICE: 0.05,
        }
    )
    invalid_result = await flow.async_step_reconfigure(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in invalid_result.get("errors", {})

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


@pytest.mark.parametrize(
    ("config_values", "expected_defaults"),
    [
        pytest.param(
            {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: "TestNode",
                CONF_IMPORT_PRICE: as_constant_value(0.30),
                CONF_EXPORT_PRICE: as_constant_value(0.08),
            },
            {
                CONF_IMPORT_PRICE: 0.30,
                CONF_EXPORT_PRICE: 0.08,
            },
            id="constant_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: "TestNode",
                CONF_IMPORT_PRICE: as_entity_value(["sensor.import_price"]),
                CONF_EXPORT_PRICE: as_entity_value(["sensor.export_price"]),
            },
            {
                CONF_IMPORT_PRICE: ["sensor.import_price"],
                CONF_EXPORT_PRICE: ["sensor.export_price"],
            },
            id="entity_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: "TestNode",
                CONF_IMPORT_PRICE: as_entity_value(["sensor.import1", "sensor.import2"]),
                CONF_EXPORT_PRICE: as_entity_value(["sensor.export"]),
            },
            {
                CONF_IMPORT_PRICE: ["sensor.import1", "sensor.import2"],
                CONF_EXPORT_PRICE: ["sensor.export"],
            },
            id="entity_list",
        ),
    ],
)
async def test_reconfigure_defaults_handle_schema_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    config_values: dict[str, Any],
    expected_defaults: dict[str, object],
) -> None:
    """Reconfigure defaults reflect schema values."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    existing_config = _wrap_config(config_values)
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

    result = await flow.async_step_reconfigure(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_defaults("Test Grid", input_fields, dict(existing_subentry.data))
    assert defaults[SECTION_PRICING][CONF_IMPORT_PRICE] == expected_defaults[CONF_IMPORT_PRICE]
    assert defaults[SECTION_PRICING][CONF_EXPORT_PRICE] == expected_defaults[CONF_EXPORT_PRICE]


# --- Tests for _is_valid_choose_value ---
