"""Tests for load element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    SchemaValue,
    as_connection_target,
    as_constant_value,
    as_entity_value,
    as_none_value,
)
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.load import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    ELEMENT_TYPE,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows.conftest import create_flow, section_suggested_values


def _load_input(forecast: SchemaValue) -> dict[str, object]:
    """Build the load form's submitted values."""
    return {
        CONF_NAME: "Test Load",
        CONF_CONNECTION: "TestNode",
        SECTION_FORECAST: {CONF_FORECAST: forecast},
        SECTION_CURTAILMENT: {CONF_CURTAILMENT: as_constant_value(value=False)},
    }


@pytest.mark.parametrize(
    ("forecast", "expected_forecast", "add_node"),
    [
        pytest.param(
            {CONF_FORECAST: as_entity_value(["sensor.forecast"])},
            as_entity_value(["sensor.forecast"]),
            True,
            id="entity_values",
        ),
        pytest.param({CONF_FORECAST: as_constant_value(100.0)}, as_constant_value(100.0), True, id="constant_values"),
        pytest.param({}, as_none_value(), True, id="missing_field"),
        pytest.param(
            {CONF_FORECAST: as_entity_value(["sensor.forecast"])},
            as_entity_value(["sensor.forecast"]),
            False,
            id="deleted_connection",
        ),
    ],
)
async def test_reconfigure_form_opens_with_the_stored_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    forecast: dict[str, SchemaValue],
    expected_forecast: SchemaValue,
    add_node: bool,
) -> None:
    """Reopening a load shows its stored forecast, or none when it stored none, ignoring unknown subentries."""
    if add_node:
        add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    unknown_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"}),
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    existing_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: "Test Load",
                CONF_CONNECTION: as_connection_target("TestNode"),
                SECTION_FORECAST: forecast,
                SECTION_CURTAILMENT: {},
            }
        ),
        subentry_type=ELEMENT_TYPE,
        title="Test Load",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    assert "Unknown" not in flow._get_participant_names()

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert section_suggested_values(result, SECTION_FORECAST)[CONF_FORECAST] == expected_forecast


@pytest.mark.parametrize(
    "forecast",
    [
        pytest.param(as_entity_value(["sensor.forecast1", "sensor.forecast2"]), id="entity"),
        pytest.param(as_constant_value(5.0), id="constant"),
    ],
)
async def test_user_step_stores_submitted_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    forecast: SchemaValue,
) -> None:
    """A new load stores its forecast as submitted, and a missing forecast is reported on its section."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Load", "data": {}})

    assert flow._get_subentry() is None

    invalid_result = await flow.async_step_user(user_input=_load_input(as_none_value()))
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("errors") == {SECTION_FORECAST: "required"}

    result = await flow.async_step_user(user_input=_load_input(forecast))

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_FORECAST] == {CONF_FORECAST: forecast}
    assert data[SECTION_CURTAILMENT] == {CONF_CURTAILMENT: as_constant_value(value=False)}
