"""Tests for connection element config flow."""

from types import MappingProxyType
from typing import (
    Any,  # noqa: TID251  # element flows are created from the registry, which a static flow type cannot express
)
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry, SubentryFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import battery, grid, node
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY,
    CONF_MAX_POWER,
    CONF_PRICE,
    CONF_SEGMENT_TYPE,
    CONF_SEGMENTS,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
)
from custom_components.haeo.flows.conftest import create_flow
from custom_components.haeo.flows.connection_path_selector import ConnectionPathSelector
from custom_components.haeo.flows.elements.connection import CONF_PATH

LIMIT: dict[str, object] = {CONF_SEGMENT_TYPE: "power_limit", CONF_MAX_POWER: as_constant_value(10.0)}
PRICE: dict[str, object] = {CONF_SEGMENT_TYPE: "pricing", CONF_PRICE: as_entity_value(["sensor.price"])}
LOSSES: dict[str, object] = {CONF_SEGMENT_TYPE: "efficiency", CONF_EFFICIENCY: as_constant_value(95.0)}


def _connection_input(
    source: str, target: str, *, name: str = "Test Connection", segments: list[dict[str, object]] | None = None
) -> dict[str, object]:
    """Build the connection form's submitted values."""
    return {
        CONF_NAME: name,
        CONF_PATH: {CONF_SOURCE: source, CONF_TARGET: target, CONF_SEGMENTS: segments or []},
    }


def _add_connection(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    source: str,
    target: str,
    segments: list[dict[str, object]] | None = None,
) -> ConfigSubentry:
    """Add a stored connection between two elements."""
    data = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Existing Connection",
        SECTION_ENDPOINTS: {CONF_SOURCE: as_connection_target(source), CONF_TARGET: as_connection_target(target)},
        CONF_SEGMENTS: segments or [],
    }
    subentry = ConfigSubentry(
        data=MappingProxyType(data), subentry_type=ELEMENT_TYPE, title="Existing Connection", unique_id=None
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _reconfigure_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, subentry: ConfigSubentry) -> Any:
    """Create a flow reconfiguring the given connection."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    return flow


def _path_field(form: SubentryFlowResult) -> tuple[object, ConnectionPathSelector]:
    """Return the value the path field opens with, and its selector."""
    data_schema = form.get("data_schema")
    assert data_schema is not None
    marker, selector = next(
        (marker, selector) for marker, selector in data_schema.schema.items() if marker == CONF_PATH
    )
    assert isinstance(marker, vol.Marker)
    assert isinstance(selector, ConnectionPathSelector)
    return (marker.description or {}).get("suggested_value"), selector


@pytest.mark.parametrize("reconfigure", [False, True], ids=["user", "reconfigure"])
async def test_flow_rejects_a_connection_from_an_element_to_itself(
    hass: HomeAssistant, hub_entry: MockConfigEntry, *, reconfigure: bool
) -> None:
    """A connection whose source is its target is rejected on the path."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node2", node.ELEMENT_TYPE)
    user_input = _connection_input("Node1", "Node1", name="Existing Connection")

    if reconfigure:
        flow = _reconfigure_flow(hass, hub_entry, _add_connection(hass, hub_entry, "Node1", "Node2"))
        result = await flow.async_step_reconfigure(user_input=user_input)
    else:
        result = await create_flow(hass, hub_entry, ELEMENT_TYPE).async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_PATH: "cannot_connect_to_self"}


async def test_reconfigure_rejects_saved_never_endpoint(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """A saved connection to a grid is still shown, but submitting it is rejected."""
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    subentry = _add_connection(hass, hub_entry, "Grid1", "Node1")

    result = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(
        user_input=_connection_input("Grid1", "Node1", name="Existing Connection")
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_PATH: "invalid_endpoint"}


@pytest.mark.parametrize(
    ("source", "add_source"),
    [
        pytest.param("Battery1", True, id="existing_source"),
        pytest.param("DeletedBattery", False, id="deleted_source"),
    ],
)
async def test_reconfigure_form_opens_with_the_stored_path(
    hass: HomeAssistant, hub_entry: MockConfigEntry, source: str, *, add_source: bool
) -> None:
    """Reopening a connection shows its endpoints and segments in order, and offers a deleted endpoint."""
    if add_source:
        add_participant(hass, hub_entry, source, battery.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)
    subentry = _add_connection(hass, hub_entry, source, "Grid1", [PRICE, LIMIT])

    result = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    value, selector = _path_field(result)
    assert value == {CONF_SOURCE: source, CONF_TARGET: "Grid1", CONF_SEGMENTS: [PRICE, LIMIT]}
    assert source in [participant["name"] for participant in selector.config["participants"]]


async def test_user_step_stores_the_endpoints_and_the_segments_in_order(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """A new connection stores its endpoints as connection targets and its segments in the order submitted."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node2", node.ELEMENT_TYPE)
    hass.states.async_set("sensor.price", "0.3", {"unit_of_measurement": "$/kWh"})

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Connection", "data": {}}
    )

    result = await flow.async_step_user(user_input=_connection_input("Node1", "Node2", segments=[LOSSES, LIMIT, PRICE]))

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_ENDPOINTS] == {
        CONF_SOURCE: as_connection_target("Node1"),
        CONF_TARGET: as_connection_target("Node2"),
    }
    assert data[CONF_SEGMENTS] == [LOSSES, LIMIT, PRICE]
    assert CONF_PATH not in data


async def test_user_step_requires_a_value_for_every_segment(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """A segment left without a value is reported on the path."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node2", node.ELEMENT_TYPE)
    empty_limit: dict[str, object] = {CONF_SEGMENT_TYPE: "power_limit", CONF_MAX_POWER: as_none_value()}

    result = await create_flow(hass, hub_entry, ELEMENT_TYPE).async_step_user(
        user_input=_connection_input("Node1", "Node2", segments=[LOSSES, empty_limit])
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_PATH: "segment_value_required"}


async def test_new_connection_opens_on_the_first_elements_with_no_segments(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """A new connection's path starts at the first two elements it can join, with power passing straight through."""
    add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "Node2", node.ELEMENT_TYPE)

    result = await create_flow(hass, hub_entry, ELEMENT_TYPE).async_step_user(user_input=None)

    value, selector = _path_field(result)
    assert value == {CONF_SOURCE: "Node1", CONF_TARGET: "Node2", CONF_SEGMENTS: []}
    assert {kind: config["field"] for kind, config in selector.config["segment_types"].items()} == {
        "power_limit": CONF_MAX_POWER,
        "pricing": CONF_PRICE,
        "efficiency": CONF_EFFICIENCY,
    }
