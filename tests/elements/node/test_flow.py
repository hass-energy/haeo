"""Tests for node element config flow."""

from collections.abc import Sequence
from types import MappingProxyType
from typing import Any, TypedDict
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements.node import (
    CONF_IS_SINK,
    CONF_IS_SOURCE,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_COMMON,
)

from ..conftest import create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat node input values into sectioned config."""
    if SECTION_COMMON in flat:
        return dict(flat)
    return {
        SECTION_COMMON: {CONF_NAME: flat[CONF_NAME]},
        SECTION_ADVANCED: {key: flat[key] for key in (CONF_IS_SOURCE, CONF_IS_SINK) if key in flat},
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat node config values into sectioned config with element type."""
    if SECTION_COMMON in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **_wrap_input(flat)}


class ValidFlowCase(TypedDict):
    """Test case for valid flow input."""

    description: str
    config: dict[str, Any]


class InvalidFlowCase(TypedDict):
    """Test case for invalid flow input."""

    description: str
    config: dict[str, Any]
    error_field: str


VALID_CASES: Sequence[ValidFlowCase] = [
    {
        "description": "Node with defaults",
        "config": _wrap_input({CONF_NAME: "Test Node"}),
    },
    {
        "description": "Node as source",
        "config": _wrap_input({CONF_NAME: "Source Node", CONF_IS_SOURCE: True, CONF_IS_SINK: False}),
    },
    {
        "description": "Node as sink",
        "config": _wrap_input({CONF_NAME: "Sink Node", CONF_IS_SOURCE: False, CONF_IS_SINK: True}),
    },
]

INVALID_CASES: Sequence[InvalidFlowCase] = [
    {
        "description": "Empty name",
        "config": _wrap_input({CONF_NAME: ""}),
        "error_field": CONF_NAME,
    },
]


@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda c: c["description"])
async def test_user_step_shows_error(hass: HomeAssistant, hub_entry: MockConfigEntry, case: InvalidFlowCase) -> None:
    """Node user step should show error with invalid input."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=case["config"])

    assert result.get("type") == FlowResultType.FORM
    assert case["error_field"] in result.get("errors", {})


async def test_user_step_shows_form_initially(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Node user step should show form when no input provided."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_user_step_rejects_duplicate_name(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Node user step should reject duplicate names."""
    # Add existing node
    existing = ConfigSubentry(
        data=MappingProxyType(_wrap_config({CONF_NAME: "ExistingNode"})),
        subentry_type=ELEMENT_TYPE,
        title="ExistingNode",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=_wrap_input({CONF_NAME: "ExistingNode"}))

    assert result.get("type") == FlowResultType.FORM
    assert CONF_NAME in result.get("errors", {})


@pytest.mark.parametrize("case", VALID_CASES, ids=lambda c: c["description"])
async def test_reconfigure_step_updates_entry(hass: HomeAssistant, hub_entry: MockConfigEntry, case: ValidFlowCase) -> None:
    """Node reconfigure step should update entry with valid input."""
    existing = ConfigSubentry(
        data=MappingProxyType(_wrap_config({CONF_NAME: "OldName"})),
        subentry_type=ELEMENT_TYPE,
        title="OldName",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing)

    result = await flow.async_step_reconfigure(user_input=case["config"])

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"


async def test_reconfigure_step_shows_form_initially(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Node reconfigure step should show form with current values."""
    existing = ConfigSubentry(
        data=MappingProxyType(_wrap_config({CONF_NAME: "TestNode", CONF_IS_SOURCE: True, CONF_IS_SINK: False})),
        subentry_type=ELEMENT_TYPE,
        title="TestNode",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing)

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
