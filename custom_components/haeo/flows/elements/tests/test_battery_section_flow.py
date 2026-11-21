"""Tests for battery_section element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import SchemaValue, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    SECTION_STORAGE,
)
from custom_components.haeo.flows.conftest import create_flow, section_suggested_values


def _section_data(storage: dict[str, SchemaValue]) -> dict[str, object]:
    """Build battery section data with the given storage inputs."""
    return {CONF_NAME: "Test Battery Section", SECTION_STORAGE: storage}


@pytest.mark.parametrize(
    ("storage", "expected_shown"),
    [
        pytest.param(
            {
                CONF_CAPACITY: as_entity_value(["sensor.section_capacity"]),
                CONF_INITIAL_CHARGE: as_entity_value(["sensor.section_charge"]),
            },
            {
                CONF_CAPACITY: as_entity_value(["sensor.section_capacity"]),
                CONF_INITIAL_CHARGE: as_entity_value(["sensor.section_charge"]),
            },
            id="entity_values",
        ),
        pytest.param(
            {CONF_CAPACITY: as_constant_value(10.0), CONF_INITIAL_CHARGE: as_constant_value(5.0)},
            {CONF_CAPACITY: as_constant_value(10.0), CONF_INITIAL_CHARGE: as_constant_value(5.0)},
            id="constant_values",
        ),
        pytest.param(
            {CONF_CAPACITY: as_constant_value(10.0)},
            {CONF_CAPACITY: as_constant_value(10.0), CONF_INITIAL_CHARGE: as_none_value()},
            id="missing_field",
        ),
    ],
)
async def test_reconfigure_form_opens_with_the_stored_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    storage: dict[str, SchemaValue],
    expected_shown: dict[str, SchemaValue],
) -> None:
    """Reopening a battery section shows its stored values, and a field it never stored opens unset."""
    existing_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE, **_section_data(storage)}),
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
    assert section_suggested_values(result, SECTION_STORAGE) == expected_shown


@pytest.mark.parametrize(
    "storage",
    [
        pytest.param(
            {CONF_CAPACITY: as_constant_value(10.0), CONF_INITIAL_CHARGE: as_constant_value(5.0)}, id="constant"
        ),
        pytest.param(
            {
                CONF_CAPACITY: as_entity_value(["sensor.capacity"]),
                CONF_INITIAL_CHARGE: as_entity_value(["sensor.charge"]),
            },
            id="entity",
        ),
    ],
)
async def test_user_step_stores_submitted_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    storage: dict[str, SchemaValue],
) -> None:
    """A new battery section stores its inputs as submitted, and a missing capacity is reported on its section."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery Section", "data": {}}
    )

    invalid_result = await flow.async_step_user(user_input=_section_data({**storage, CONF_CAPACITY: as_none_value()}))
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("errors") == {SECTION_STORAGE: "required"}

    result = await flow.async_step_user(user_input=_section_data(storage))

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert flow.async_create_entry.call_args.kwargs["data"][SECTION_STORAGE] == storage
