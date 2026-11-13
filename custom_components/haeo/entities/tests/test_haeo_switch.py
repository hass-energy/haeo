"""Tests for the HAEO switch input entity."""

import asyncio
from datetime import timedelta
import logging
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import STATE_OFF, STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.const import CONF_RECORD_FORECASTS, DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_HORIZON, CONF_NAME, HORIZON_PRESET_2_DAYS
from custom_components.haeo.core.data.input_store import InputMode, create_input_store
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import (
    SchemaValue,
    as_connection_target,
    as_constant_value,
    as_entity_value,
    as_none_value,
)
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_RULES
from custom_components.haeo.core.schema.elements.solar import CONF_FORECAST, SECTION_CURTAILMENT, SECTION_FORECAST
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.core.schema.util import get_nested_config_value_by_path
from custom_components.haeo.elements import find_nested_config_path, get_input_fields, iter_input_field_paths
from custom_components.haeo.elements.input_fields import InputFieldInfo, is_switch_field_info
from custom_components.haeo.entities.haeo_switch import FORECAST_UNRECORDED_ATTRIBUTES, HaeoInputSwitch
from custom_components.haeo.entities.tests.entity_helpers import mock_state_writes
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.inputs.source_loader import SourceInputLoader
from custom_components.haeo.util import async_update_subentry_value

# --- Fixtures ---


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry for switch entity tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Network",
                CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS),
            },
            HUB_SECTION_ADVANCED: {},
        },
        entry_id="test_switch_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def device_entry() -> Mock:
    """Return a mock device entry."""
    device = Mock(spec=DeviceEntry)
    device.id = "mock-switch-device-id"
    return device


@pytest.fixture
def horizon_manager() -> Mock:
    """Return a mock horizon manager."""
    manager = Mock(spec=HorizonManager)
    # Return timestamps for 2 periods starting now
    manager.get_forecast_timestamps.return_value = (0.0, 300.0, 600.0)
    # Subscribe returns an unsubscribe function
    manager.subscribe.return_value = Mock()
    return manager


@pytest.fixture
def curtailment_field_info() -> InputFieldInfo[SwitchEntityDescription]:
    """Return a sample InputFieldInfo for a boolean curtailment field."""
    return InputFieldInfo(
        field_name="allow_curtailment",
        entity_description=SwitchEntityDescription(
            key="allow_curtailment",
            translation_key="solar_curtailment",
        ),
        output_type=OutputType.STATUS,
    )


def _create_subentry(name: str, data: dict[str, object]) -> ConfigSubentry:
    """Create a ConfigSubentry with the given data."""

    def schema_value(value: object) -> SchemaValue:
        if value is None:
            return as_none_value()
        if isinstance(value, bool):
            return as_constant_value(value)
        if isinstance(value, (int, float)):
            return as_constant_value(float(value))
        if isinstance(value, str):
            return as_entity_value([value])
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return as_entity_value(value)
        msg = f"Unsupported schema value {value!r}"
        raise TypeError(msg)

    return ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "solar",
                CONF_NAME: name,
                CONF_CONNECTION: as_connection_target("Switchboard"),
                SECTION_FORECAST: {
                    CONF_FORECAST: as_entity_value(["sensor.solar_forecast"]),
                },
                SECTION_CURTAILMENT: {key: schema_value(value) for key, value in data.items()},
            }
        ),
        subentry_type="solar",
        title=name,
        unique_id=None,
    )


class _SubentryStorage:
    """Storage double backing an input store with a live config subentry field."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: MockConfigEntry,
        subentry: ConfigSubentry,
        field_path: tuple[str, ...],
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._subentry = subentry
        self._field_path = field_path

    async def write(self, value: object) -> None:
        await async_update_subentry_value(
            self._hass,
            self._entry,
            self._subentry,
            field_path=self._field_path,
            value=value,
        )


def _make_switch_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    subentry: ConfigSubentry,
    field_info: InputFieldInfo[SwitchEntityDescription],
    device_entry: DeviceEntry,
    horizon_manager: Mock,
    field_path: tuple[str, ...] | None = None,
) -> HaeoInputSwitch:
    """Build an input store and switch entity wrapping it."""
    fp = field_path or find_nested_config_path(subentry.data, field_info.field_name) or (field_info.field_name,)
    storage = _SubentryStorage(hass, config_entry, subentry, fp)
    hint = FieldHint(
        output_type=field_info.output_type,
        direction=field_info.direction,
        time_series=field_info.time_series,
        boundaries=field_info.boundaries,
        calendar=field_info.calendar,
    )
    store = create_input_store(
        value=get_nested_config_value_by_path(subentry.data, fp),
        storage=storage,
        hint=hint,
        get_forecast_timestamps=horizon_manager.get_forecast_timestamps,
    )
    return HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
        store=store,
        field_path=field_path,
    )


async def _add_entity_to_hass(hass: HomeAssistant, entity: HaeoInputSwitch) -> None:
    """Load the entity's store as setup does, then add the entity via a real EntityPlatform."""
    SourceInputLoader(hass, {("Element", ("field",)): entity._store}, Mock(spec=HorizonManager)).start()
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain="switch",
        platform_name=DOMAIN,
        platform=None,
        scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    await platform.async_add_entities([entity])
    await hass.async_block_till_done()


def _forecast_values(entity: HaeoInputSwitch) -> list[bool | None]:
    """Return the forecast attribute's per-point values."""
    attrs = entity.extra_state_attributes
    assert attrs is not None
    return [point["value"] for point in attrs["forecast"]]


def _forecast_points(entity: HaeoInputSwitch) -> list[tuple[float, bool | None]]:
    """Return the forecast attribute's (timestamp, value) points."""
    attrs = entity.extra_state_attributes
    assert attrs is not None
    return [(point["time"].timestamp(), point["value"]) for point in attrs["forecast"]]


# --- Tests for EDITABLE mode ---


@pytest.mark.parametrize("value", [True, False, None], ids=["true", "false", "none"])
async def test_editable_mode_initializes_from_config_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    value: bool | None,
) -> None:
    """Switch entity in EDITABLE mode initializes from its config value, which may be unset."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": value})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    assert entity._store.mode == InputMode.EDITABLE
    assert entity._store.source_entity_ids == []
    assert entity.is_on is value

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["config_mode"] == "editable"
    assert attrs["element_name"] == "Test Solar"
    assert attrs["element_type"] == "solar"
    assert attrs["field_name"] == "allow_curtailment"


async def test_editable_mode_with_raw_boolean(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity handles raw boolean config values."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "solar",
                CONF_NAME: "Raw Bool",
                CONF_CONNECTION: as_connection_target("Switchboard"),
                SECTION_FORECAST: {CONF_FORECAST: as_entity_value(["sensor.solar_forecast"])},
                SECTION_CURTAILMENT: {curtailment_field_info.field_name: True},
            }
        ),
        subentry_type="solar",
        title="Raw Bool",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    assert entity._store.mode == InputMode.EDITABLE
    assert entity.is_on is True


@pytest.mark.parametrize("turn_on", [True, False], ids=["turn_on", "turn_off"])
async def test_editable_mode_turn_on_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    *,
    turn_on: bool,
) -> None:
    """Switch entity in EDITABLE mode turns on or off when the user requests, and persists the value."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": not turn_on})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)
    hass.config_entries.async_update_subentry = Mock()

    await (entity.async_turn_on() if turn_on else entity.async_turn_off())

    assert entity.is_on is turn_on
    assert all(value is turn_on for value in _forecast_values(entity))
    hass.config_entries.async_update_subentry.assert_called_once()


async def test_editable_turn_on_updates_config_before_state_change(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Subentry config already reflects the new value when async_write_ha_state fires.

    async_write_ha_state fires a state change event that the coordinator
    handles synchronously. The coordinator reads the element's config from
    the subentry to build element data for optimization. If the config
    still contains the old value at that point, the first optimization
    runs with stale data.
    """
    subentry = _create_subentry("Test Solar", {"allow_curtailment": False})
    hass.config_entries.async_add_subentry(config_entry, subentry)
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    # When async_write_ha_state fires, capture what the subentry data says
    captured_config_value: list[SchemaValue] = []

    def _capture_config_on_state_write() -> None:
        live_subentry = config_entry.subentries[subentry.subentry_id]
        captured_config_value.append(live_subentry.data[SECTION_CURTAILMENT]["allow_curtailment"])

    write_state = mock_state_writes(entity, _capture_config_on_state_write)
    await _add_entity_to_hass(hass, entity)
    write_state.reset_mock()
    captured_config_value.clear()

    await entity.async_turn_on()

    # The config must already show the new constant value when state fires
    assert captured_config_value == [as_constant_value(value=True)]


# --- Tests for DRIVEN mode ---


async def test_driven_mode_with_entity_id(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in DRIVEN mode tracks source entity."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.allow_curtailment"})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    assert entity._store.mode == InputMode.DRIVEN
    assert entity._store.source_entity_ids == ["input_boolean.allow_curtailment"]
    assert entity.is_on is None  # Not loaded yet

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["config_mode"] == "driven"
    assert attrs["source_entity"] == "input_boolean.allow_curtailment"


@pytest.mark.parametrize("turn_on", [True, False], ids=["turn_on", "turn_off"])
async def test_driven_mode_ignores_turn_on_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    *,
    turn_on: bool,
) -> None:
    """Switch entity in DRIVEN mode keeps its source's value when the user turns it on or off."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)
    entity._attr_is_on = not turn_on  # Simulate loaded state
    write_state = mock_state_writes(entity)

    await (entity.async_turn_on() if turn_on else entity.async_turn_off())

    assert entity.is_on is (not turn_on)
    write_state.assert_called_once()


@pytest.mark.parametrize(("source_state", "expected"), [(STATE_ON, True), (STATE_OFF, False)])
async def test_driven_mode_loads_source_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    source_state: str,
    expected: bool,
) -> None:
    """Switch entity in DRIVEN mode loads its initial state from the source entity."""
    hass.states.async_set("input_boolean.curtail", source_state)

    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    await _add_entity_to_hass(hass, entity)

    assert entity.is_on is expected


# --- Tests for unique ID generation ---


async def test_unique_id_includes_all_components(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Unique ID includes entry_id, subentry_id, and field_name."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    expected_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{curtailment_field_info.field_name}"
    assert entity.unique_id == expected_unique_id


async def test_unique_id_disambiguates_reused_section_field_names(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Section switch fields whose name repeats in another section key on the section path."""
    field_info = InputFieldInfo(
        field_name="enabled",
        entity_description=SwitchEntityDescription(
            key="enabled",
            translation_key="enabled",
        ),
        output_type=OutputType.STATUS,
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "battery",
                CONF_NAME: "Test Battery",
                "first": {"enabled": as_constant_value(True)},
                "second": {"enabled": as_constant_value(False)},
            }
        ),
        subentry_type="battery",
        title="Test Battery",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_switch_entity(
        hass,
        config_entry,
        subentry,
        field_info,
        device_entry,
        horizon_manager,
        field_path=("first", "enabled"),
    )

    expected_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_first.enabled"
    assert entity.unique_id == expected_unique_id


# --- Tests for entity attributes ---


async def test_entity_has_correct_category(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Entity should be CONFIG category."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    assert entity.entity_category == EntityCategory.CONFIG


async def test_entity_does_not_poll(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Entity should not poll."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    assert entity.should_poll is False


async def test_translation_key_from_field_info(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Translation key is derived from field info."""
    field_info: InputFieldInfo[SwitchEntityDescription] = InputFieldInfo(
        field_name="enable_export",
        entity_description=SwitchEntityDescription(
            key="enable_export",
            translation_key="custom_translation",
        ),
        output_type=OutputType.STATUS,
    )
    subentry = _create_subentry("Test", {"enable_export": True})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, field_info, device_entry, horizon_manager)

    assert entity.entity_description.translation_key == "custom_translation"


async def test_translation_placeholders_include_rule_name_for_list_field(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """List-based switch fields expose rule_name for translation placeholders."""
    field_info = InputFieldInfo(
        field_name=CONF_ENABLED,
        entity_description=SwitchEntityDescription(
            key=CONF_ENABLED,
            translation_key="policy_enabled",
        ),
        output_type=OutputType.STATUS,
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.POLICY,
                CONF_NAME: "Policies",
                CONF_RULES: [
                    {"name": "Export", CONF_ENABLED: True},
                ],
            }
        ),
        subentry_type=ElementType.POLICY,
        title="Policies",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_switch_entity(
        hass,
        config_entry,
        subentry,
        field_info,
        device_entry,
        horizon_manager,
        field_path=(CONF_RULES, "0", CONF_ENABLED),
    )

    placeholders = entity._attr_translation_placeholders
    assert placeholders is not None
    assert placeholders.get("rule_name") == "Export"


async def test_translation_placeholders_skip_invalid_list_index(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Invalid list index in field_path does not raise and omits rule_name."""
    field_info = InputFieldInfo(
        field_name=CONF_ENABLED,
        entity_description=SwitchEntityDescription(
            key=CONF_ENABLED,
            translation_key="policy_enabled",
        ),
        output_type=OutputType.STATUS,
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.POLICY,
                CONF_NAME: "Policies",
                CONF_RULES: [
                    {"name": "Export", CONF_ENABLED: True},
                ],
            }
        ),
        subentry_type=ElementType.POLICY,
        title="Policies",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_switch_entity(
        hass,
        config_entry,
        subentry,
        field_info,
        device_entry,
        horizon_manager,
        field_path=(CONF_RULES, "not-an-index", CONF_ENABLED),
    )

    placeholders = entity._attr_translation_placeholders
    assert placeholders is not None
    assert "rule_name" not in placeholders


async def test_invalid_config_value_raises_runtime_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Unknown switch config value types fail loudly when building the store."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    # Inject an invalid nested value shape for this field
    invalid_data = dict(subentry.data)
    invalid_data[SECTION_CURTAILMENT] = {curtailment_field_info.field_name: {"type": "invalid"}}
    invalid_subentry = ConfigSubentry(
        data=MappingProxyType(invalid_data),
        subentry_type=subentry.subentry_type,
        title=subentry.title,
        unique_id=subentry.unique_id,
    )
    config_entry.runtime_data = None

    with pytest.raises(RuntimeError, match="Invalid config value"):
        _make_switch_entity(hass, config_entry, invalid_subentry, curtailment_field_info, device_entry, horizon_manager)


# --- Tests for forecast attribute building ---


async def test_editable_forecast_built_from_horizon_timestamps(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Editable switch builds a forecast attribute with one point per horizon timestamp."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    values = _forecast_values(entity)
    assert len(values) == 3
    assert all(v is True for v in values)


# --- Tests for horizon and source state change handlers ---


@pytest.mark.parametrize(
    ("config_value", "expected"),
    [
        pytest.param(True, True, id="editable"),
        pytest.param("input_boolean.curtail", True, id="driven"),
    ],
)
async def test_horizon_change_updates_forecast_timestamps(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    config_value: bool | str,
    expected: bool,
) -> None:
    """A horizon change writes the switch's value as a forecast on the new timestamps."""
    hass.states.async_set("input_boolean.curtail", STATE_ON)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": config_value})
    config_entry.runtime_data = None
    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)
    written_forecasts: list[list[tuple[float, bool | None]]] = []

    def capture_write() -> None:
        written_forecasts.append(_forecast_points(entity))

    mock_state_writes(entity, capture_write)

    horizon_manager.get_forecast_timestamps.return_value = (100.0, 400.0, 700.0)
    (on_horizon_change,) = [call.args[0] for call in horizon_manager.subscribe.call_args_list]
    on_horizon_change()

    (written_forecast,) = written_forecasts
    assert written_forecast == [(100.0, expected), (400.0, expected), (700.0, expected)]


@pytest.mark.parametrize(
    ("source_state", "is_on", "available"),
    [
        pytest.param(STATE_ON, True, True, id="on"),
        pytest.param("unavailable", False, False, id="unavailable"),
    ],
)
async def test_source_change_updates_switch(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    source_state: str,
    is_on: bool,
    available: bool,
) -> None:
    """A source change shows on the switch, which goes unavailable while its source has no reading."""
    hass.states.async_set("input_boolean.curtail", STATE_OFF)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None
    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)
    write_state = mock_state_writes(entity)

    hass.states.async_set("input_boolean.curtail", source_state)
    await hass.async_block_till_done()

    assert entity.is_on is is_on
    assert entity.available is available
    write_state.assert_called_once()


# --- Tests for readiness ---


async def test_is_ready_returns_true_after_data_loaded(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """is_ready() returns True after data has been loaded."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)
    assert entity.is_ready() is False

    await _add_entity_to_hass(hass, entity)

    assert entity.is_ready() is True


async def test_async_added_to_hass_editable_uses_config_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_added_to_hass uses config value in EDITABLE mode (no restore needed)."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    await _add_entity_to_hass(hass, entity)

    # Should use config value directly
    assert entity.is_on is True


async def test_driven_switch_shows_source_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """A driven switch shows the state its store loaded from the source entity."""
    hass.states.async_set("input_boolean.curtail", STATE_ON)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    await _add_entity_to_hass(hass, entity)

    # Entity should have loaded state from source
    assert entity.is_on is True


async def test_wait_ready_blocks_until_data_loaded(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """wait_ready() blocks until data is loaded."""
    # Use DRIVEN mode so data isn't loaded until source state is available
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = _make_switch_entity(hass, config_entry, subentry, curtailment_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    # Before data is loaded, is_ready is False (no source state yet)
    assert entity.is_ready() is False

    # Start wait_ready in background
    wait_task = asyncio.create_task(entity.wait_ready())

    # Give task a chance to start
    await asyncio.sleep(0)

    # Task should not complete yet
    assert not wait_task.done()

    # The source reports a state, which the loader loads
    hass.states.async_set("input_boolean.curtail", STATE_ON)
    await hass.async_block_till_done()

    # Now wait_ready should complete
    await asyncio.wait_for(wait_task, timeout=1.0)

    assert entity.is_ready() is True


# --- Recorder Filtering Tests ---


@pytest.mark.parametrize(
    ("record_forecasts", "expect_unrecorded"),
    [
        (False, True),  # Default: forecasts are excluded from recorder
        (True, False),  # When enabled: forecasts are recorded
    ],
)
async def test_unrecorded_attributes_based_on_config(
    hass: HomeAssistant,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    record_forecasts: bool,
    expect_unrecorded: bool,
) -> None:
    """Switch entity applies recorder filtering based on record_forecasts config."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            "name": "Test Network",
            CONF_RECORD_FORECASTS: record_forecasts,
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    entry.runtime_data = None

    entity = _make_switch_entity(hass, entry, subentry, curtailment_field_info, device_entry, horizon_manager)

    entity._state_info = {"unrecorded_attributes": frozenset()}
    entity._apply_recorder_attribute_filtering()
    if expect_unrecorded:
        assert entity._state_info["unrecorded_attributes"] == FORECAST_UNRECORDED_ATTRIBUTES
    else:
        assert entity._state_info["unrecorded_attributes"] == frozenset()


async def test_calendar_availability_switch_shows_each_period(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """An availability input read from a calendar is a switch on for now, with each period's value as its forecast."""
    field_info = next(
        info
        for _path, info in iter_input_field_paths(get_input_fields(ElementType.EV))
        if info.output_type is OutputType.AVAILABILITY and info.calendar is not None
    )
    assert is_switch_field_info(field_info)
    assert field_info.source_field is not None
    assert field_info.calendar is not None
    timestamps = horizon_manager.get_forecast_timestamps()
    subentry = _create_subentry("Test EV", {field_info.source_field: "calendar.trips"})
    config_entry.runtime_data = None
    entity = _make_switch_entity(
        hass,
        config_entry,
        subentry,
        field_info,
        device_entry,
        horizon_manager,
        field_path=(SECTION_CURTAILMENT, field_info.source_field),
    )
    await _add_entity_to_hass(hass, entity)

    # A trip covering the second period only
    event = {
        "start": dt_util.utc_from_timestamp(timestamps[1]).isoformat(),
        "end": dt_util.utc_from_timestamp(timestamps[2]).isoformat(),
        "summary": "Trip",
        "location": None,
        "description": None,
    }
    calendar = FakeEntityState("calendar.trips", "off", {CALENDAR_EVENTS_ATTRIBUTE: [event]})
    assert entity._store.resolve_from_sources(FakeStateMachine({"calendar.trips": calendar}))
    entity._store.notify_listeners()

    assert entity.is_on is False
    assert _forecast_points(entity) == [(timestamps[0], False), (timestamps[1], True)]
    assert entity.extra_state_attributes is not None
    assert entity.extra_state_attributes["calendar_projection"] == field_info.calendar.projection
