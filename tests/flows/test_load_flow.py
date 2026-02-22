"""Tests for load element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.adapters.elements.load import adapter
from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.elements.load import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
)
from custom_components.haeo.sections import CONF_CONNECTION
from tests.conftest import add_participant

from .conftest import create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat load input values into sectioned config."""
    if SECTION_COMMON in flat:
        return dict(flat)
    return {
        SECTION_COMMON: {
            CONF_NAME: flat[CONF_NAME],
            CONF_CONNECTION: flat[CONF_CONNECTION],
        },
        SECTION_FORECAST: {
            CONF_FORECAST: flat[CONF_FORECAST],
        },
        SECTION_PRICING: {key: flat[key] for key in (CONF_PRICE_TARGET_SOURCE,) if key in flat},
        SECTION_CURTAILMENT: {key: flat[key] for key in (CONF_CURTAILMENT,) if key in flat},
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat load config values into sectioned config with element type."""
    if SECTION_COMMON in flat:
        data = {CONF_ELEMENT_TYPE: "load", **flat}
        data.setdefault(SECTION_PRICING, {})
        data.setdefault(SECTION_CURTAILMENT, {})
        return data
    config = _wrap_input(flat)
    common = config.get(SECTION_COMMON, {})
    if CONF_CONNECTION in common and isinstance(common[CONF_CONNECTION], str):
        common[CONF_CONNECTION] = as_connection_target(common[CONF_CONNECTION])
    config.setdefault(SECTION_PRICING, {})
    config.setdefault(SECTION_CURTAILMENT, {})
    return {CONF_ELEMENT_TYPE: "load", **config}


@pytest.mark.parametrize(
    ("config_values", "expected_forecast", "add_node"),
    [
        pytest.param(
            {
                CONF_NAME: "Test Load",
                CONF_CONNECTION: "TestNode",
                CONF_FORECAST: as_entity_value(["sensor.load_forecast"]),
            },
            ["sensor.load_forecast"],
            True,
            id="entity_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Load",
                CONF_CONNECTION: "TestNode",
                CONF_FORECAST: as_constant_value(100.0),
            },
            100.0,
            True,
            id="constant_values",
        ),
        pytest.param(
            {
                SECTION_COMMON: {
                    CONF_NAME: "Test Load",
                    CONF_CONNECTION: as_connection_target("TestNode"),
                },
                SECTION_FORECAST: {},
                SECTION_PRICING: {},
                SECTION_CURTAILMENT: {},
            },
            None,
            True,
            id="missing_field",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Load",
                CONF_CONNECTION: "DeletedNode",
                CONF_FORECAST: as_entity_value(["sensor.power"]),
            },
            ["sensor.power"],
            False,
            id="deleted_connection",
        ),
    ],
)
async def test_reconfigure_defaults_handle_schema_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    config_values: dict[str, Any],
    expected_forecast: object,
    add_node: bool,
) -> None:
    """Reconfigure defaults reflect schema values and missing fields."""
    if add_node:
        add_participant(hass, hub_entry, "TestNode", ElementType.NODE)

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
        subentry_type="load",
        title="Test Load",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ElementType.LOAD)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    participants = flow._get_participant_names()
    assert "Unknown" not in participants

    result = await flow.async_step_reconfigure(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = adapter.inputs(dict(existing_subentry.data))
    defaults = flow._build_defaults("Test Load", input_fields, dict(existing_subentry.data))
    assert defaults.get(SECTION_FORECAST, {}).get(CONF_FORECAST) == expected_forecast


async def test_user_step_with_entity_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with entity selection should create entry with entity ID."""
    add_participant(hass, hub_entry, "TestNode", ElementType.NODE)

    flow = create_flow(hass, hub_entry, ElementType.LOAD)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Load",
            "data": {},
        }
    )

    assert flow._get_subentry() is None

    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: [],
            CONF_CURTAILMENT: False,
        }
    )
    invalid_result = await flow.async_step_user(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert CONF_FORECAST in invalid_result.get("errors", {})

    # Submit with entity selection using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: ["sensor.load_forecast"],
            CONF_CURTAILMENT: False,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity schema value
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_FORECAST][CONF_FORECAST] == as_entity_value(["sensor.load_forecast"])


async def test_user_step_with_constant_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with constant value should create entry with value."""
    add_participant(hass, hub_entry, "TestNode", ElementType.NODE)

    flow = create_flow(hass, hub_entry, ElementType.LOAD)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Load",
            "data": {},
        }
    )

    # Submit with constant value using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: 5.0,
            CONF_CURTAILMENT: False,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant schema value
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_FORECAST][CONF_FORECAST] == as_constant_value(5.0)


# --- Tests for _is_valid_choose_value ---
