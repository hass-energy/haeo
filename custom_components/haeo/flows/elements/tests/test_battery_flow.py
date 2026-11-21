"""Tests for battery element config flow."""

from collections.abc import Mapping
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_LIMIT_COST,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_EFFICIENCY,
    SECTION_LIMITS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows.conftest import create_flow, section_suggested_values


def _battery_data(values: Mapping[str, object], *, connection: object = "main_bus") -> dict[str, object]:
    """Nest battery values into their form sections, with the salvage value and charge limit cost defaulted."""
    sections = {
        SECTION_STORAGE: (CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE),
        SECTION_LIMITS: (CONF_MIN_CHARGE_PERCENTAGE, CONF_MAX_CHARGE_PERCENTAGE),
        SECTION_POWER_LIMITS: (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE),
        SECTION_PRICING: (CONF_SALVAGE_VALUE,),
        SECTION_EFFICIENCY: (CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE),
        SECTION_ADVANCED: (CONF_CHARGE_LIMIT_COST,),
    }
    defaults = {CONF_SALVAGE_VALUE: as_constant_value(0.0), CONF_CHARGE_LIMIT_COST: as_constant_value(100.0)}
    merged = {**defaults, **values}
    return {
        CONF_NAME: merged.get(CONF_NAME, "Test Battery"),
        CONF_CONNECTION: connection,
        **{section: {key: merged[key] for key in keys if key in merged} for section, keys in sections.items()},
    }


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
                CONF_MIN_CHARGE_PERCENTAGE: as_none_value(),
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
                CONF_CHARGE_LIMIT_COST: as_constant_value(50.0),
            },
            id="constant_values",
        ),
        pytest.param(
            {
                CONF_CAPACITY: as_entity_value(["sensor.capacity"]),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
                CONF_EFFICIENCY_SOURCE_TARGET: as_none_value(),
                CONF_MAX_POWER_TARGET_SOURCE: as_entity_value(["sensor.max_charge"]),
                CONF_MAX_POWER_SOURCE_TARGET: as_entity_value(["sensor.max_discharge"]),
                CONF_CHARGE_LIMIT_COST: as_entity_value(["sensor.charge_limit_cost"]),
            },
            id="entity_values",
        ),
    ],
)
async def test_user_step_stores_submitted_values(
    hass: HomeAssistant, hub_entry: MockConfigEntry, values: dict[str, object]
) -> None:
    """A new battery stores its inputs as submitted, and a missing capacity is reported on the storage section."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}}
    )

    result = await flow.async_step_user(user_input=_battery_data({**values, CONF_CAPACITY: as_none_value()}))
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {SECTION_STORAGE: "required"}

    result = await flow.async_step_user(user_input=_battery_data(values))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    expected = _battery_data(values, connection=as_connection_target("main_bus"))
    assert created_data == {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **expected}


@pytest.mark.parametrize(
    ("connection", "add_connection", "values"),
    [
        pytest.param(
            "main_bus",
            True,
            {
                CONF_CAPACITY: as_entity_value(["sensor.battery_capacity"]),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
                CONF_MAX_POWER_TARGET_SOURCE: as_entity_value(["sensor.charge_power"]),
                CONF_MAX_POWER_SOURCE_TARGET: as_entity_value(["sensor.discharge_power"]),
            },
            id="entity_values",
        ),
        pytest.param(
            "DeletedNode",
            False,
            {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
            id="constant_values_deleted_connection",
        ),
    ],
)
async def test_reconfigure_form_opens_with_the_stored_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    connection: str,
    add_connection: bool,
    values: dict[str, object],
) -> None:
    """Reopening a battery shows its stored values, even when its connection was deleted."""
    if add_connection:
        add_participant(hass, hub_entry, connection, node.ELEMENT_TYPE)

    stored = _battery_data(values, connection=as_connection_target(connection))
    existing_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE, **stored}),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    shown = {
        key: value
        for section in (SECTION_STORAGE, SECTION_POWER_LIMITS, SECTION_EFFICIENCY)
        for key, value in section_suggested_values(result, section).items()
    }
    assert {key: shown[key] for key in values} == values


async def test_reconfigure_updates_existing_battery(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure flow completes and updates existing battery."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    stored = _battery_data(
        {
            CONF_CAPACITY: as_constant_value(10.0),
            CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
            CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
            CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
        },
        connection=as_connection_target("main_bus"),
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE, **stored}),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    result = await flow.async_step_reconfigure(
        user_input=_battery_data(
            {
                CONF_NAME: "Test Battery Updated",
                CONF_CAPACITY: as_constant_value(15.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(7.5),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(7.5),
            }
        )
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["title"] == "Test Battery Updated"
    assert update_kwargs["data"][CONF_CONNECTION] == as_connection_target("main_bus")
    assert update_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(15.0)
    assert update_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(7.5)
