"""Tests for connection element config flow."""

from types import MappingProxyType
from typing import (
    Any,  # noqa: TID251  # element flows are created from the registry, which a static flow type cannot express
)
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import SchemaValue, as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import battery, grid, node
from custom_components.haeo.core.schema.elements.connection import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_EFFICIENCY,
    SECTION_ENDPOINTS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.flows.conftest import create_flow, section_suggested_values


def _connection_input(
    source: str, target: str, *, name: str = "Test Connection", limits: dict[str, SchemaValue] | None = None
) -> dict[str, object]:
    """Build the connection form's submitted values."""
    return {
        CONF_NAME: name,
        SECTION_ENDPOINTS: {CONF_SOURCE: source, CONF_TARGET: target},
        SECTION_POWER_LIMITS: limits or {},
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }


def _add_connection(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    source: str,
    target: str,
    limits: dict[str, SchemaValue] | None = None,
) -> ConfigSubentry:
    """Add a stored connection between two elements."""
    data = _connection_input(source, target, name="Existing Connection", limits=limits)
    data[SECTION_ENDPOINTS] = {CONF_SOURCE: as_connection_target(source), CONF_TARGET: as_connection_target(target)}
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE, **data}),
        subentry_type=ELEMENT_TYPE,
        title="Existing Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _reconfigure_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, subentry: ConfigSubentry) -> Any:
    """Create a flow reconfiguring the given connection."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    return flow


async def test_flow_source_equals_target_error(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Connection flow should error when source equals target."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    result = await flow.async_step_user(user_input=_connection_input("Node1", "Node1"))

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {SECTION_ENDPOINTS: "cannot_connect_to_self"}


async def test_reconfigure_source_equals_target_error(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Connection reconfigure should error when source equals target."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node2", node.ELEMENT_TYPE)
    subentry = _add_connection(hass, hub_entry, "Node1", "Node2")

    result = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(
        user_input=_connection_input("Node1", "Node1", name="Existing Connection")
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {SECTION_ENDPOINTS: "cannot_connect_to_self"}


async def test_reconfigure_rejects_saved_never_endpoint(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """A saved connection to a grid is still shown, but submitting it is rejected."""
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    subentry = _add_connection(hass, hub_entry, "Grid1", "Node1")

    result = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(
        user_input=_connection_input("Grid1", "Node1", name="Existing Connection")
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {SECTION_ENDPOINTS: "invalid_endpoint"}


@pytest.mark.parametrize(
    ("source", "add_source", "limit"),
    [
        pytest.param("Battery1", True, as_entity_value(["sensor.max_power_st"]), id="entity_values"),
        pytest.param("DeletedBattery", False, as_constant_value(10.0), id="constant_values_deleted_source"),
    ],
)
async def test_reconfigure_form_opens_with_the_stored_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    source: str,
    add_source: bool,
    limit: SchemaValue,
) -> None:
    """Reopening a connection shows its stored values, even when an endpoint was deleted."""
    if add_source:
        add_participant(hass, hub_entry, source, battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)
    subentry = _add_connection(hass, hub_entry, source, "Grid1", {CONF_MAX_POWER_SOURCE_TARGET: limit})

    result = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert section_suggested_values(result, SECTION_POWER_LIMITS)[CONF_MAX_POWER_SOURCE_TARGET] == limit


@pytest.mark.parametrize(
    "limit",
    [
        pytest.param(as_constant_value(10.0), id="constant"),
        pytest.param(as_entity_value(["sensor.power_st"]), id="entity"),
    ],
)
async def test_user_step_stores_submitted_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    limit: SchemaValue,
) -> None:
    """A new connection stores its endpoints as connection targets and its inputs as submitted."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node2", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Connection", "data": {}}
    )

    result = await flow.async_step_user(
        user_input=_connection_input("Node1", "Node2", limits={CONF_MAX_POWER_SOURCE_TARGET: limit})
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_ENDPOINTS] == {
        CONF_SOURCE: as_connection_target("Node1"),
        CONF_TARGET: as_connection_target("Node2"),
    }
    assert data[SECTION_POWER_LIMITS] == {CONF_MAX_POWER_SOURCE_TARGET: limit}
