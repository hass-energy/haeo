"""Tests for node element config flow."""

from collections.abc import Sequence
from types import MappingProxyType
from typing import TypedDict
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_USER, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements.node import ELEMENT_TYPE
from custom_components.haeo.flows.conftest import create_flow


def _node_config(name: str) -> dict[str, object]:
    """Build stored node config for a name."""
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, CONF_NAME: name}


class ValidFlowCase(TypedDict):
    """Test case for valid flow input."""

    description: str
    config: dict[str, object]


class InvalidFlowCase(TypedDict):
    """Test case for invalid flow input."""

    description: str
    config: dict[str, object]
    error_field: str
    existing_name: str | None


VALID_CASES: Sequence[ValidFlowCase] = [
    {
        "description": "Renamed node",
        "config": {CONF_NAME: "Test Node"},
    },
    {
        "description": "Unchanged name",
        "config": {CONF_NAME: "OldName"},
    },
]

INVALID_CASES: Sequence[InvalidFlowCase] = [
    {
        "description": "Empty name",
        "config": {CONF_NAME: ""},
        "error_field": CONF_NAME,
        "existing_name": None,
    },
    {
        "description": "Duplicate name",
        "config": {CONF_NAME: "ExistingNode"},
        "error_field": CONF_NAME,
        "existing_name": "ExistingNode",
    },
]


@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda c: c["description"])
async def test_user_step_shows_error(hass: HomeAssistant, hub_entry: MockConfigEntry, case: InvalidFlowCase) -> None:
    """Node user step should show error with invalid input."""
    if case["existing_name"]:
        existing = ConfigSubentry(
            data=MappingProxyType(_node_config(case["existing_name"])),
            subentry_type=ELEMENT_TYPE,
            title=case["existing_name"],
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, existing)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    form_result = await flow.async_step_user(user_input=None)
    assert form_result.get("type") == FlowResultType.FORM
    assert form_result.get("step_id") == "user"

    result = await flow.async_step_user(user_input=case["config"])

    assert result.get("type") == FlowResultType.FORM
    assert case["error_field"] in result.get("errors", {})


@pytest.mark.parametrize("case", VALID_CASES, ids=lambda c: c["description"])
async def test_reconfigure_step_updates_entry(
    hass: HomeAssistant, hub_entry: MockConfigEntry, case: ValidFlowCase
) -> None:
    """Node reconfigure step should update entry with valid input."""
    existing = ConfigSubentry(
        data=MappingProxyType(_node_config("OldName")),
        subentry_type=ELEMENT_TYPE,
        title="OldName",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing)

    form_result = await flow.async_step_reconfigure(user_input=None)
    assert form_result.get("type") == FlowResultType.FORM
    assert form_result.get("step_id") == "user"

    result = await flow.async_step_reconfigure(user_input=case["config"])

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"
    assert hub_entry.subentries[existing.subentry_id].data == _node_config(str(case["config"][CONF_NAME]))


async def test_user_step_shows_only_name_field(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Node form should offer no source or sink role, since nodes are always pure junctions."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=None)

    data_schema = result.get("data_schema")
    assert data_schema is not None
    assert [str(key) for key in data_schema.schema] == [CONF_NAME]


async def test_user_step_creates_junction_node(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Node user step should store only the element type and name."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"source": SOURCE_USER}

    result = await flow.async_step_user(user_input={CONF_NAME: "AC Bus"})

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "AC Bus"
    assert result.get("data") == _node_config("AC Bus")
