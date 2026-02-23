"""Tests for battery_section element config flow."""

from types import MappingProxyType
from typing import Any, cast
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    SECTION_STORAGE,
)
from custom_components.haeo.elements import get_input_fields
from tests.flows.conftest import create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat battery section input values into sectioned config."""
    if SECTION_STORAGE in flat:
        return dict(flat)
    return {
        CONF_NAME: flat[CONF_NAME],
        SECTION_STORAGE: {
            CONF_CAPACITY: flat[CONF_CAPACITY],
            CONF_INITIAL_CHARGE: flat.get(CONF_INITIAL_CHARGE),
        },
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat battery section config values into sectioned config with element type."""
    if SECTION_STORAGE in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **_wrap_input(flat)}


@pytest.mark.parametrize(
    ("config_values", "expected_defaults"),
    [
        pytest.param(
            {
                CONF_NAME: "Test Battery Section",
                CONF_CAPACITY: as_entity_value(["sensor.section_capacity"]),
                CONF_INITIAL_CHARGE: as_entity_value(["sensor.section_charge"]),
            },
            {
                CONF_CAPACITY: ["sensor.section_capacity"],
                CONF_INITIAL_CHARGE: ["sensor.section_charge"],
            },
            id="entity_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Battery Section",
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE: as_constant_value(5.0),
            },
            {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE: 5.0,
            },
            id="constant_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Battery Section",
                CONF_CAPACITY: as_constant_value(10.0),
            },
            {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE: None,
            },
            id="missing_field",
        ),
    ],
)
async def test_reconfigure_defaults_handle_schema_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    config_values: dict[str, Any],
    expected_defaults: dict[str, Any],
) -> None:
    """Reconfigure defaults reflect schema values and missing fields."""
    existing_config = _wrap_config(config_values)
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

    result = await flow.async_step_reconfigure(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_defaults("Test Battery Section", input_fields, dict(existing_subentry.data))

    for key, expected in expected_defaults.items():
        assert defaults.get(SECTION_STORAGE, {}).get(key) == expected


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
    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Battery Section",
            CONF_CAPACITY: [],
            CONF_INITIAL_CHARGE: 5.0,
        }
    )
    invalid_result = await flow.async_step_user(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert CONF_CAPACITY in invalid_result.get("errors", {})

    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(10.0)
    assert create_kwargs["data"][SECTION_STORAGE][CONF_INITIAL_CHARGE] == as_constant_value(5.0)


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

    # Verify the config contains the entity schema values (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == as_entity_value(["sensor.capacity"])
    assert create_kwargs["data"][SECTION_STORAGE][CONF_INITIAL_CHARGE] == as_entity_value(["sensor.charge"])


# --- Tests for _is_valid_choose_value ---
