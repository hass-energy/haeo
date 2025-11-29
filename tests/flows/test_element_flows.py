"""End-to-end tests for element subentry flows."""

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, TypedDict, cast
from unittest.mock import MagicMock, Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import (
    ELEMENT_TYPES,
    ElementRegistryEntry,
    ElementType,
    battery,
    connection,
    grid,
    node,
)
from custom_components.haeo.flows.element import ElementSubentryFlow, create_subentry_flow_class
from custom_components.haeo.schema.fields import NameFieldData, NameFieldSchema
from tests.conftest import ElementTestData

ALL_ELEMENT_TYPES: tuple[ElementType, ...] = tuple(ELEMENT_TYPES)

TEST_ELEMENT_TYPE = "flow_test_element"


class FlowTestElementConfigSchema(TypedDict):
    """Schema representation for synthetic flow test elements."""

    element_type: Literal["flow_test_element"]
    name: NameFieldSchema


class FlowTestElementConfigData(TypedDict):
    """Data representation for synthetic flow test elements."""

    element_type: Literal["flow_test_element"]
    name: NameFieldData


def _create_flow(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_type: ElementType,
) -> ElementSubentryFlow:
    """Create a configured subentry flow instance for an element type."""

    registry_entry = ELEMENT_TYPES[element_type]
    flow_class = create_subentry_flow_class(element_type, registry_entry.schema, registry_entry.defaults)
    flow = flow_class()  # type: ignore[call-arg]
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, element_type)
    return flow


def _add_participant_subentry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    name: str,
    element_type: ElementType = node.ELEMENT_TYPE,
) -> ConfigSubentry:
    """Ensure a participant subentry exists for connection endpoints."""

    for subentry in hub_entry.subentries.values():
        if subentry.data.get(CONF_NAME) == name:
            return subentry

    participant_data = MappingProxyType({CONF_ELEMENT_TYPE: element_type, CONF_NAME: name})
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
    element_type: ElementType,
    config: dict[str, Any],
) -> None:
    """Populate dependent participants required by connection flows."""

    if element_type == connection.ELEMENT_TYPE:
        for key in (connection.CONF_SOURCE, connection.CONF_TARGET):
            endpoint = config.get(key)
            if isinstance(endpoint, str) and endpoint:
                inferred_type: ElementType = grid.ELEMENT_TYPE if "grid" in endpoint.lower() else battery.ELEMENT_TYPE
                _add_participant_subentry(hass, hub_entry, endpoint, inferred_type)


def _make_subentry(element_type: ElementType, config: dict[str, Any]) -> ConfigSubentry:
    """Create an immutable config subentry for the provided element data."""

    data = {CONF_ELEMENT_TYPE: element_type, **deepcopy(config)}
    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=element_type,
        title=data.get(CONF_NAME, element_type.title()),
        unique_id=None,
    )


@dataclass(slots=True)
class FlowTestElementFactory:
    """Factory generating synthetic element configurations for flow tests."""

    element_type: str = TEST_ELEMENT_TYPE

    def create_config(self, *, name: str) -> dict[str, Any]:
        """Return a minimal configuration for a synthetic element."""

        return {CONF_NAME: name}

    def create_subentry(self, *, name: str) -> ConfigSubentry:
        """Return a config subentry for the synthetic element."""
        return _make_subentry(cast("ElementType", self.element_type), self.create_config(name=name))

    def element_type_for_flow(self) -> ElementType:
        """Return the synthetic element type cast for flow construction."""

        return cast("ElementType", self.element_type)


@pytest.fixture
def flow_test_element_factory(monkeypatch: pytest.MonkeyPatch) -> FlowTestElementFactory:
    """Register and return a synthetic element factory for flow testing."""

    entry = ElementRegistryEntry(
        schema=FlowTestElementConfigSchema,
        data=FlowTestElementConfigData,
        defaults={},
        translation_key=cast("ElementType", TEST_ELEMENT_TYPE),
    )
    monkeypatch.setitem(ELEMENT_TYPES, cast("ElementType", TEST_ELEMENT_TYPE), entry)
    return FlowTestElementFactory()


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a configured hub entry for flow testing."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture(autouse=True)
def connectivity_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch connectivity evaluation during flow tests."""

    mock = MagicMock()
    monkeypatch.setattr(
        "custom_components.haeo.flows.element.evaluate_network_connectivity",
        mock,
    )
    return mock


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
            "title": user_input.get(CONF_NAME, element_type),
            "data": {},
        }
    )

    result = await flow.async_step_user(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert not result.get("errors")

    result = await flow.async_step_user(user_input=user_input)
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_kwargs = flow.async_create_entry.call_args.kwargs
    assert created_kwargs["data"][CONF_ELEMENT_TYPE] == element_type
    assert created_kwargs["data"][CONF_NAME] == user_input[CONF_NAME]


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
    base_config[CONF_NAME] = ""

    _prepare_flow_context(hass, hub_entry, element_type, base_config)

    result = await flow.async_step_user(user_input=base_config)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_NAME: "missing_name"}


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
    assert result.get("errors") == {CONF_NAME: "name_exists"}


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
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_reload_and_abort = Mock(
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
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_reload_and_abort = Mock(
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
    )

    renamed_input = deepcopy(existing_config)
    original_name = renamed_input[CONF_NAME]
    renamed_input[CONF_NAME] = f"{original_name} Updated"

    result = await flow.async_step_reconfigure(user_input=renamed_input)
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    update_kwargs = flow.async_update_reload_and_abort.call_args.kwargs
    assert update_kwargs["title"] == renamed_input[CONF_NAME]


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
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    invalid_input = deepcopy(existing_config)
    invalid_input[CONF_NAME] = ""

    result = await flow.async_step_reconfigure(user_input=invalid_input)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_NAME: "missing_name"}


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
    secondary_config[CONF_NAME] = f"{primary_config[CONF_NAME]} Secondary"

    _prepare_flow_context(hass, hub_entry, element_type, primary_config)
    _prepare_flow_context(hass, hub_entry, element_type, secondary_config)

    primary_subentry = _make_subentry(element_type, primary_config)
    hass.config_entries.async_add_subentry(hub_entry, primary_subentry)

    secondary_subentry = _make_subentry(element_type, secondary_config)
    hass.config_entries.async_add_subentry(hub_entry, secondary_subentry)

    flow = _create_flow(hass, hub_entry, element_type)
    flow._get_reconfigure_subentry = Mock(return_value=secondary_subentry)

    duplicate_input = deepcopy(secondary_config)
    duplicate_input[CONF_NAME] = primary_config[CONF_NAME]

    result = await flow.async_step_reconfigure(user_input=duplicate_input)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_NAME: "name_exists"}


async def test_element_flow_user_step_invokes_connectivity_validation(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_test_data: dict[ElementType, ElementTestData],
    connectivity_mock: MagicMock,
) -> None:
    """Ensure user step validates connectivity with updated participants."""

    element_type: ElementType = node.ELEMENT_TYPE
    flow = _create_flow(hass, hub_entry, element_type)
    user_input = deepcopy(element_test_data[element_type].valid[0].config)

    _prepare_flow_context(hass, hub_entry, element_type, user_input)

    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": user_input.get(CONF_NAME, element_type),
            "data": {},
        }
    )

    await flow.async_step_user(user_input=user_input)

    connectivity_mock.assert_called_once()
    args, kwargs = connectivity_mock.call_args
    assert args[0] is hass
    assert args[1] is hub_entry
    participant_configs = kwargs["participant_configs"]
    assert user_input[CONF_NAME] in participant_configs


async def test_element_flow_reconfigure_invokes_connectivity_validation(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    element_test_data: dict[ElementType, ElementTestData],
    connectivity_mock: MagicMock,
) -> None:
    """Ensure reconfigure step validates connectivity with updated participants."""

    element_type: ElementType = node.ELEMENT_TYPE
    existing_config = deepcopy(element_test_data[element_type].valid[0].config)

    _prepare_flow_context(hass, hub_entry, element_type, existing_config)

    subentry = _make_subentry(element_type, existing_config)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry, element_type)
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_reload_and_abort = Mock(
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
    )

    await flow.async_step_reconfigure(user_input=existing_config)

    connectivity_mock.assert_called_once()
    args, kwargs = connectivity_mock.call_args
    assert args[0] is hass
    assert args[1] is hub_entry
    participant_configs = kwargs["participant_configs"]
    assert existing_config[CONF_NAME] in participant_configs


async def test_get_other_element_entries_filters_correctly(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    flow_test_element_factory: FlowTestElementFactory,
) -> None:
    """Verify participant filtering excludes non-endpoint subentries."""

    endpoint_one = flow_test_element_factory.create_subentry(name="Endpoint One")
    endpoint_two = flow_test_element_factory.create_subentry(name="Endpoint Two")
    hass.config_entries.async_add_subentry(hub_entry, endpoint_one)
    hass.config_entries.async_add_subentry(hub_entry, endpoint_two)

    network_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_NAME: "Network", CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK}),
        subentry_type=ELEMENT_TYPE_NETWORK,
        title="Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, network_subentry)

    connection_subentry = _make_subentry(
        connection.ELEMENT_TYPE,
        {
            CONF_NAME: "Connection 1",
            connection.CONF_SOURCE: "Endpoint One",
            connection.CONF_TARGET: "Endpoint Two",
        },
    )
    hass.config_entries.async_add_subentry(hub_entry, connection_subentry)

    flow = _create_flow(hass, hub_entry, flow_test_element_factory.element_type_for_flow())

    participants = flow._get_non_connection_element_names()

    assert set(participants) == {"Endpoint One", "Endpoint Two"}
    assert "Network" not in participants
    assert "Connection 1" not in participants
