"""End-to-end tests for element subentry flows."""

from copy import deepcopy
from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.elements import ELEMENT_TYPES, ElementType, battery, connection, grid, node
from custom_components.haeo.flows.element import ElementSubentryFlow, create_subentry_flow_class
from tests.conftest import ElementTestData

ALL_ELEMENT_TYPES: tuple[ElementType, ...] = tuple(ELEMENT_TYPES)


def _create_flow(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
) -> ElementSubentryFlow[Any]:
    """Create a configured subentry flow instance for an element type."""

    registry_entry = ELEMENT_TYPES[element_type]
    flow_class = create_subentry_flow_class(element_type, registry_entry.schema, registry_entry.defaults)
    flow: ElementSubentryFlow[Any] = flow_class()  # type: ignore[call-arg]
    flow.hass = hass
    flow._get_entry = Mock(return_value=hub_entry)  # type: ignore[method-assign]
    return flow


def _add_participant_subentry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    name: str,
    element_type: ElementType = node.ELEMENT_TYPE,
) -> ConfigSubentry:
    """Ensure a participant subentry exists for connection endpoints."""

    for subentry in hub_entry.subentries.values():
        if subentry.data.get("name_value") == name:
            return subentry

    participant_data = MappingProxyType({CONF_ELEMENT_TYPE: element_type, "name_value": name})
    subentry = ConfigSubentry(
        data=participant_data,
        subentry_type=element_type,
        title=name,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _prepare_flow_context(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: str,
    config: dict[str, Any],
) -> None:
    """Populate dependent participants required by connection flows."""

    if element_type == connection.ELEMENT_TYPE:
        for key in ("source_value", "target_value"):
            endpoint = config.get(key)
            if isinstance(endpoint, str) and endpoint:
                inferred_type = grid.ELEMENT_TYPE if "grid" in endpoint.lower() else battery.ELEMENT_TYPE
                _add_participant_subentry(hass, hub_entry, endpoint, inferred_type)


def _make_subentry(element_type: ElementType, config: dict[str, Any]) -> ConfigSubentry:
    """Create an immutable config subentry for the provided element data."""

    data = {CONF_ELEMENT_TYPE: element_type, **deepcopy(config)}
    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=element_type,
        title=data.get("name_value", element_type.title()),
        unique_id=None,
    )


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a configured hub entry for flow testing."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "CBC",
        },
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.parametrize("element_type", ALL_ELEMENT_TYPES)
async def test_element_flow_user_step_success(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
    element_test_data: dict[ElementType, ElementTestData],
) -> None:
    """Validate the happy path for adding each element type."""

    flow = _create_flow(hass, hub_entry, element_type)
    cases = element_test_data[element_type]
    assert cases.valid, f"No valid test data for {element_type}"
    user_input = deepcopy(cases.valid[0].config)

    _prepare_flow_context(hass, hub_entry, element_type, user_input)

    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": user_input.get("name_value", element_type),
            "data": {},
        }
    )  # type: ignore[method-assign]

    result = await flow.async_step_user(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert not result.get("errors")

    result = await flow.async_step_user(user_input=user_input)
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_kwargs = flow.async_create_entry.call_args.kwargs
    assert created_kwargs["data"][CONF_ELEMENT_TYPE] == element_type
    assert created_kwargs["data"]["name_value"] == user_input["name_value"]


@pytest.mark.parametrize("element_type", ALL_ELEMENT_TYPES)
async def test_element_flow_user_step_missing_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
    element_test_data: dict[ElementType, ElementTestData],
) -> None:
    """Ensure missing names are rejected for all element types."""

    flow = _create_flow(hass, hub_entry, element_type)
    base_config = deepcopy(element_test_data[element_type].valid[0].config)
    base_config["name_value"] = ""

    _prepare_flow_context(hass, hub_entry, element_type, base_config)

    result = await flow.async_step_user(user_input=base_config)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"name_value": "missing_name"}


@pytest.mark.parametrize("element_type", ALL_ELEMENT_TYPES)
async def test_element_flow_user_step_duplicate_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
    element_test_data: dict[ElementType, ElementTestData],
) -> None:
    """Ensure duplicate names are detected when creating elements."""

    existing_config = deepcopy(element_test_data[element_type].valid[0].config)

    _prepare_flow_context(hass, hub_entry, element_type, existing_config)

    existing_subentry = _make_subentry(element_type, existing_config)
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = _create_flow(hass, hub_entry, element_type)

    result = await flow.async_step_user(user_input=existing_config)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"name_value": "name_exists"}


@pytest.mark.parametrize("element_type", ALL_ELEMENT_TYPES)
async def test_element_flow_reconfigure_success(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
    element_test_data: dict[ElementType, ElementTestData],
) -> None:
    """Verify reconfigure submissions succeed for unchanged data."""

    existing_config = deepcopy(element_test_data[element_type].valid[0].config)

    _prepare_flow_context(hass, hub_entry, element_type, existing_config)

    existing_subentry = _make_subentry(element_type, existing_config)
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = _create_flow(hass, hub_entry, element_type)
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)  # type: ignore[method-assign]
    flow.async_update_reload_and_abort = Mock(  # type: ignore[method-assign]
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
    )

    result = await flow.async_step_reconfigure(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"

    reconfigure_input = deepcopy(existing_config)
    result = await flow.async_step_reconfigure(user_input=reconfigure_input)
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    update_kwargs = flow.async_update_reload_and_abort.call_args.kwargs
    assert update_kwargs["data"][CONF_ELEMENT_TYPE] == element_type


@pytest.mark.parametrize("element_type", ALL_ELEMENT_TYPES)
async def test_element_flow_reconfigure_rename(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
    element_test_data: dict[ElementType, ElementTestData],
) -> None:
    """Verify reconfigure handles renaming across element types."""

    existing_config = deepcopy(element_test_data[element_type].valid[0].config)

    _prepare_flow_context(hass, hub_entry, element_type, existing_config)

    existing_subentry = _make_subentry(element_type, existing_config)
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = _create_flow(hass, hub_entry, element_type)
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)  # type: ignore[method-assign]
    flow.async_update_reload_and_abort = Mock(  # type: ignore[method-assign]
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
    )

    renamed_input = deepcopy(existing_config)
    original_name = renamed_input["name_value"]
    renamed_input["name_value"] = f"{original_name} Updated"

    result = await flow.async_step_reconfigure(user_input=renamed_input)
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    update_kwargs = flow.async_update_reload_and_abort.call_args.kwargs
    assert update_kwargs["title"] == renamed_input["name_value"]


@pytest.mark.parametrize("element_type", ALL_ELEMENT_TYPES)
async def test_element_flow_reconfigure_missing_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
    element_test_data: dict[ElementType, ElementTestData],
) -> None:
    """Ensure empty names are rejected during reconfigure flows."""

    existing_config = deepcopy(element_test_data[element_type].valid[0].config)

    _prepare_flow_context(hass, hub_entry, element_type, existing_config)

    existing_subentry = _make_subentry(element_type, existing_config)
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = _create_flow(hass, hub_entry, element_type)
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)  # type: ignore[method-assign]

    invalid_input = deepcopy(existing_config)
    invalid_input["name_value"] = ""

    result = await flow.async_step_reconfigure(user_input=invalid_input)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"name_value": "missing_name"}


@pytest.mark.parametrize("element_type", ALL_ELEMENT_TYPES)
async def test_element_flow_reconfigure_duplicate_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
    element_test_data: dict[ElementType, ElementTestData],
) -> None:
    """Ensure reconfigure prevents renaming to an existing element."""

    primary_config = deepcopy(element_test_data[element_type].valid[0].config)
    secondary_source = (
        element_test_data[element_type].valid[1].config
        if len(element_test_data[element_type].valid) > 1
        else primary_config
    )
    secondary_config = deepcopy(secondary_source)
    secondary_config["name_value"] = f"{primary_config['name_value']} Secondary"

    _prepare_flow_context(hass, hub_entry, element_type, primary_config)
    _prepare_flow_context(hass, hub_entry, element_type, secondary_config)

    primary_subentry = _make_subentry(element_type, primary_config)
    hass.config_entries.async_add_subentry(hub_entry, primary_subentry)

    secondary_subentry = _make_subentry(element_type, secondary_config)
    hass.config_entries.async_add_subentry(hub_entry, secondary_subentry)

    flow = _create_flow(hass, hub_entry, element_type)
    flow._get_reconfigure_subentry = Mock(return_value=secondary_subentry)  # type: ignore[method-assign]

    duplicate_input = deepcopy(secondary_config)
    duplicate_input["name_value"] = primary_config["name_value"]

    result = await flow.async_step_reconfigure(user_input=duplicate_input)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"name_value": "name_exists"}


async def test_get_participant_entries_filters_correctly(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Verify participant filtering excludes non-endpoint subentries."""

    battery_subentry = _make_subentry(battery.ELEMENT_TYPE, {"name_value": "Battery 1", "capacity_value": 10.0})
    hass.config_entries.async_add_subentry(hub_entry, battery_subentry)

    network_subentry = ConfigSubentry(
        data=MappingProxyType({"name_value": "Network", CONF_ELEMENT_TYPE: "network"}),
        subentry_type="network",
        title="Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, network_subentry)

    connection_subentry = _make_subentry(
        connection.ELEMENT_TYPE,
        {
            "name_value": "Connection 1",
            "source_value": "Battery 1",
            "target_value": "Grid",
        },
    )
    hass.config_entries.async_add_subentry(hub_entry, connection_subentry)

    grid_subentry = _make_subentry(grid.ELEMENT_TYPE, {"name_value": "Grid"})
    hass.config_entries.async_add_subentry(hub_entry, grid_subentry)

    flow = _create_flow(hass, hub_entry, battery.ELEMENT_TYPE)

    participants = flow._get_participant_entries(hub_entry.entry_id)

    assert set(participants) == {"Battery 1", "Grid"}
    assert "Network" not in participants
    assert "Connection 1" not in participants
