"""Tests for the HAEO number input entity."""

import asyncio
from datetime import timedelta
import logging
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, Mock

from homeassistant.components.number import NumberEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_RECORD_FORECASTS, DOMAIN
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.data.input_store import InputMode, create_input_store
from custom_components.haeo.core.model import OutputType
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements.policy import CONF_RULES
from custom_components.haeo.core.schema.elements.policy import ELEMENT_TYPE as POLICY_ELEMENT_TYPE
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.core.schema.sections import CONF_CONNECTION, SECTION_EFFICIENCY
from custom_components.haeo.elements import find_nested_config_path, get_nested_config_value_by_path
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.haeo_number import FORECAST_UNRECORDED_ATTRIBUTES, HaeoInputNumber
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.util import async_update_subentry_value

# --- Fixtures ---


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry for number entity tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            HUB_SECTION_COMMON: {CONF_NAME: "Test Network"},
            HUB_SECTION_TIERS: {
                "tier_1_count": 2,
                "tier_1_duration": 5,
                "tier_2_count": 0,
                "tier_2_duration": 15,
                "tier_3_count": 0,
                "tier_3_duration": 30,
                "tier_4_count": 0,
                "tier_4_duration": 60,
            },
            HUB_SECTION_ADVANCED: {},
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def device_entry() -> Mock:
    """Return a mock device entry."""
    device = Mock(spec=DeviceEntry)
    device.id = "mock-device-id"
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
def power_field_info() -> InputFieldInfo[NumberEntityDescription]:
    """Return a sample InputFieldInfo for a power field."""
    return InputFieldInfo(
        field_name="power_limit",
        entity_description=NumberEntityDescription(
            key="power_limit",
            translation_key="power_limit",
            native_unit_of_measurement="kW",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER,
        direction="+",
        time_series=True,
    )


@pytest.fixture
def scalar_field_info() -> InputFieldInfo[NumberEntityDescription]:
    """Return a sample InputFieldInfo for a scalar field."""
    return InputFieldInfo(
        field_name="capacity",
        entity_description=NumberEntityDescription(
            key="capacity",
            translation_key="capacity",
            native_unit_of_measurement="kWh",
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=1.0,
        ),
        output_type=OutputType.ENERGY,
        time_series=False,
    )


@pytest.fixture
def scalar_percent_field_info() -> InputFieldInfo[NumberEntityDescription]:
    """Return a sample InputFieldInfo for a scalar percentage field."""
    return InputFieldInfo(
        field_name="soc",
        entity_description=NumberEntityDescription(
            key="soc",
            translation_key="soc",
            native_unit_of_measurement="%",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=False,
    )


@pytest.fixture
def boundary_field_info() -> InputFieldInfo[NumberEntityDescription]:
    """Return a sample InputFieldInfo for a boundary field (energy state at time points)."""
    return InputFieldInfo(
        field_name="soc",
        entity_description=NumberEntityDescription(
            key="soc",
            translation_key="soc",
            native_unit_of_measurement="%",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.ENERGY,
        time_series=True,
        boundaries=True,
    )


@pytest.fixture
def percent_field_info() -> InputFieldInfo[NumberEntityDescription]:
    """Return a sample InputFieldInfo for a percentage-based field."""
    return InputFieldInfo(
        field_name="soc",
        entity_description=NumberEntityDescription(
            key="soc",
            translation_key="soc",
            native_unit_of_measurement="%",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
    )


def _create_subentry(name: str, data: dict[str, Any]) -> ConfigSubentry:
    """Create a ConfigSubentry with the given data."""

    def schema_value(value: Any) -> Any:
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
                "element_type": "battery",
                CONF_NAME: name,
                SECTION_EFFICIENCY: {key: schema_value(value) for key, value in data.items()},
            }
        ),
        subentry_type="battery",
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

    def read(self) -> Any:
        return get_nested_config_value_by_path(self._subentry.data, self._field_path)

    async def write(self, value: Any) -> None:
        await async_update_subentry_value(
            self._hass,
            self._entry,
            self._subentry,
            field_path=self._field_path,
            value=value,
        )


def _make_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    subentry: ConfigSubentry,
    field_info: InputFieldInfo[NumberEntityDescription],
    device_entry: DeviceEntry,
    horizon_manager: Mock,
    field_path: tuple[str, ...] | None = None,
) -> HaeoInputNumber:
    """Build an input store and number entity wrapping it."""
    fp = field_path or find_nested_config_path(subentry.data, field_info.field_name) or (field_info.field_name,)
    storage = _SubentryStorage(hass, config_entry, subentry, fp)
    hint = FieldHint(
        output_type=field_info.output_type,
        direction=field_info.direction,
        time_series=field_info.time_series,
        boundaries=field_info.boundaries,
    )
    store = create_input_store(
        storage=storage,
        hint=hint,
        get_forecast_timestamps=horizon_manager.get_forecast_timestamps,
    )
    return HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
        store=store,
        field_path=field_path,
    )


async def _add_entity_to_hass(hass: HomeAssistant, entity: Entity) -> None:
    """Add entity to Home Assistant via a real EntityPlatform."""
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain="number",
        platform_name=DOMAIN,
        platform=None,
        scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    await platform.async_add_entities([entity])
    await hass.async_block_till_done()


# --- Tests for EDITABLE mode ---


async def test_editable_mode_with_static_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in EDITABLE mode initializes with static config value."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.5})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    assert entity.entity_mode == InputMode.EDITABLE
    assert entity.store.source_entity_ids == []
    assert entity.native_value == 10.5
    assert entity.native_unit_of_measurement == "kW"
    assert entity.native_min_value == 0.0
    assert entity.native_max_value == 100.0
    assert entity.native_step == 0.1

    # Check extra state attributes
    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["config_mode"] == "editable"
    assert attrs["element_name"] == "Test Battery"
    assert attrs["element_type"] == "battery"
    assert attrs["field_name"] == "power_limit"
    assert attrs["source_role"] == "limit"
    assert attrs["direction"] == "+"
    assert attrs["time_series"] is True


async def test_nested_policy_rule_price_sets_rule_name_placeholder(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """List item fields (rules.N.price) include the rule name in translation placeholders."""
    price_field = InputFieldInfo(
        field_name="price",
        entity_description=NumberEntityDescription(
            key="price",
            translation_key="policy_rule_price",
            native_unit_of_measurement="USD/kWh",
            native_min_value=-100.0,
            native_max_value=100.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        time_series=True,
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": POLICY_ELEMENT_TYPE,
                "name": "Policies",
                CONF_RULES: [
                    {"name": "Grid export fee", "price": as_constant_value(0.04)},
                ],
            }
        ),
        subentry_type=POLICY_ELEMENT_TYPE,
        title="Policies",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_entity(
        hass,
        config_entry,
        subentry,
        price_field,
        device_entry,
        horizon_manager,
        field_path=("rules", "0", "price"),
    )

    assert entity._attr_translation_placeholders["rule_name"] == "Grid export fee"


async def test_list_item_sibling_fields_in_extra_state_attributes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """List item fields expose sibling fields from the same list item as extra state attributes."""
    price_field = InputFieldInfo(
        field_name="price",
        entity_description=NumberEntityDescription(
            key="price",
            translation_key="policy_rule_price",
            native_unit_of_measurement="USD/kWh",
            native_min_value=-100.0,
            native_max_value=100.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        time_series=True,
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": POLICY_ELEMENT_TYPE,
                "name": "Policies",
                CONF_RULES: [
                    {
                        "name": "Solar Export",
                        "source": ["Solar"],
                        "target": ["Grid"],
                        "price": as_constant_value(0.02),
                    },
                ],
            }
        ),
        subentry_type=POLICY_ELEMENT_TYPE,
        title="Policies",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_entity(
        hass,
        config_entry,
        subentry,
        price_field,
        device_entry,
        horizon_manager,
        field_path=("rules", "0", "price"),
    )

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["name"] == "Solar Export"
    assert attrs["source"] == ["Solar"]
    assert attrs["target"] == ["Grid"]
    # The entity's own field should NOT be included
    assert "price" not in attrs


async def test_invalid_field_config_raises_runtime_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Unknown schema-shaped config for the field raises RuntimeError when building the store."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "battery",
                CONF_NAME: "Test Battery",
                SECTION_EFFICIENCY: {power_field_info.field_name: {"type": "unknown_kind", "value": 1.0}},
            }
        ),
        subentry_type="battery",
        title="Test Battery",
        unique_id=None,
    )
    config_entry.runtime_data = None

    with pytest.raises(RuntimeError, match="Invalid config value"):
        _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)


async def test_policy_rule_price_omits_rule_name_when_rule_index_invalid(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Non-integer rule indices skip the rule_name placeholder without failing init."""
    price_field = InputFieldInfo(
        field_name="price",
        entity_description=NumberEntityDescription(
            key="price",
            translation_key="policy_rule_price",
            native_unit_of_measurement="USD/kWh",
            native_min_value=-100.0,
            native_max_value=100.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        time_series=True,
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": POLICY_ELEMENT_TYPE,
                "name": "Policies",
                CONF_RULES: [
                    {"name": "Grid export fee", "price": as_constant_value(0.04)},
                ],
            }
        ),
        subentry_type=POLICY_ELEMENT_TYPE,
        title="Policies",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_entity(
        hass,
        config_entry,
        subentry,
        price_field,
        device_entry,
        horizon_manager,
        field_path=("rules", "not_an_index", "price"),
    )

    assert "rule_name" not in entity._attr_translation_placeholders


async def test_editable_mode_set_native_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in EDITABLE mode updates value on user set."""
    subentry = _create_subentry("Test Battery", {"power_limit": 5.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    # Mock async_write_ha_state and config entry update
    entity.async_write_ha_state = Mock()
    hass.config_entries.async_update_subentry = Mock()
    await _add_entity_to_hass(hass, entity)
    entity.async_write_ha_state.reset_mock()

    await entity.async_set_native_value(15.0)

    assert entity.native_value == 15.0
    entity.async_write_ha_state.assert_called_once()
    # Value should be persisted to config entry
    hass.config_entries.async_update_subentry.assert_called_once()


async def test_editable_set_value_updates_config_before_state_change(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Subentry config already reflects the new value when async_write_ha_state fires.

    async_write_ha_state fires a state change event that the coordinator
    handles synchronously. The coordinator reads the element's config from
    the subentry to build element data for optimization. If the config
    still contains the old value at that point, the first optimization
    runs with stale data.
    """
    subentry = _create_subentry("Test Battery", {"power_limit": 5.0})
    hass.config_entries.async_add_subentry(config_entry, subentry)
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    # When async_write_ha_state fires, capture what the subentry data says
    captured_config_value: list[Any] = []

    def _capture_config_on_state_write() -> None:
        live_subentry = config_entry.subentries[subentry.subentry_id]
        captured_config_value.append(live_subentry.data[SECTION_EFFICIENCY]["power_limit"])

    entity.async_write_ha_state = Mock(side_effect=_capture_config_on_state_write)
    await _add_entity_to_hass(hass, entity)
    entity.async_write_ha_state.reset_mock()
    captured_config_value.clear()

    await entity.async_set_native_value(15.0)

    # The config must already show the new constant value when state fires
    assert captured_config_value == [as_constant_value(15.0)]


async def test_editable_mode_set_native_value_with_runtime_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in EDITABLE mode sets value_update_in_progress flag when runtime_data exists."""
    subentry = _create_subentry("Test Battery", {"power_limit": 5.0})

    # Create mock runtime_data with value_update_in_progress attribute
    mock_runtime_data = Mock()
    mock_runtime_data.value_update_in_progress = False
    config_entry.runtime_data = mock_runtime_data

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    # Mock async_write_ha_state and config entry update
    entity.async_write_ha_state = Mock()
    hass.config_entries.async_update_subentry = Mock()
    await _add_entity_to_hass(hass, entity)
    entity.async_write_ha_state.reset_mock()

    await entity.async_set_native_value(15.0)

    assert entity.native_value == 15.0
    entity.async_write_ha_state.assert_called_once()
    hass.config_entries.async_update_subentry.assert_called_once()
    # Flag stays set — the update listener is responsible for clearing it
    assert mock_runtime_data.value_update_in_progress is True


# --- Tests for DRIVEN mode ---


async def test_driven_mode_with_single_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in DRIVEN mode tracks single source entity."""
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power_limit"]})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    assert entity.entity_mode == InputMode.DRIVEN
    assert entity.store.source_entity_ids == ["sensor.power_limit"]
    assert entity.native_value is None  # Not loaded yet

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["config_mode"] == "driven"
    assert attrs["source_entities"] == ["sensor.power_limit"]


async def test_driven_mode_with_multiple_entities(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in DRIVEN mode tracks multiple source entities."""
    subentry = _create_subentry(
        "Test Battery",
        {"power_limit": ["sensor.power1", "sensor.power2"]},
    )
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    assert entity.entity_mode == InputMode.DRIVEN
    assert entity.store.source_entity_ids == ["sensor.power1", "sensor.power2"]


async def test_driven_mode_ignores_user_set_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in DRIVEN mode ignores user value changes."""
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    entity._attr_native_value = 10.0  # Simulate loaded value
    entity.async_write_ha_state = Mock()

    await entity.async_set_native_value(999.0)

    # Value should NOT change in driven mode
    assert entity.native_value == 10.0
    entity.async_write_ha_state.assert_called_once()


# --- Tests for unique ID generation ---


async def test_unique_id_includes_all_components(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Unique ID includes entry_id, subentry_id, and field_name."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    expected_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{power_field_info.field_name}"
    assert entity.unique_id == expected_unique_id


async def test_unique_id_disambiguates_reused_section_field_names(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Section fields with repeated leaf names use a collision-proof key."""
    partition_field_info = InputFieldInfo(
        field_name="partition_percentage",
        entity_description=NumberEntityDescription(
            key="partition_percentage",
            translation_key="partition_percentage",
            native_unit_of_measurement="%",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
        boundaries=True,
        device_type="undercharge_partition",
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "battery",
                CONF_NAME: "Test Battery",
                "undercharge": {"partition_percentage": as_constant_value(5.0)},
                "overcharge": {"partition_percentage": as_constant_value(95.0)},
            }
        ),
        subentry_type="battery",
        title="Test Battery",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_entity(
        hass,
        config_entry,
        subentry,
        partition_field_info,
        device_entry,
        horizon_manager,
        field_path=("undercharge", "partition_percentage"),
    )

    expected_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_undercharge_partition.partition_percentage"
    assert entity.unique_id == expected_unique_id


# --- Tests for translation placeholders ---


async def test_translation_placeholders_from_subentry_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Translation placeholders are derived from subentry data."""
    subentry = _create_subentry("My Battery", {"power_limit": 10.0, "extra_key": "extra_value"})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    placeholders = entity._attr_translation_placeholders
    assert placeholders is not None
    assert placeholders["name"] == "My Battery"
    assert placeholders["power_limit"] == "10.0"
    assert placeholders["extra_key"] == "extra_value"


async def test_translation_placeholders_include_connection_and_none_values(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Translation placeholders include connection targets and none values."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "battery",
                CONF_NAME: "My Battery",
                CONF_CONNECTION: as_connection_target("Bus"),
                SECTION_EFFICIENCY: {power_field_info.field_name: as_none_value()},
            }
        ),
        subentry_type="battery",
        title="My Battery",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    placeholders = entity._attr_translation_placeholders
    assert placeholders is not None
    assert placeholders["connection"] == "Bus"
    assert placeholders[power_field_info.field_name] == ""


# --- Tests for entity attributes ---


async def test_entity_has_correct_category(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Entity should be CONFIG category."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    assert entity.entity_category == EntityCategory.CONFIG


async def test_entity_does_not_poll(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Entity should not poll."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    assert entity.should_poll is False


# --- Tests for store-backed value behavior ---


async def test_scalar_percent_native_value_in_display_units(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_percent_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Scalar percentage fields expose the display (0-100) value as native_value."""
    subentry = _create_subentry("Test Battery", {"soc": 50.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, scalar_percent_field_info, device_entry, horizon_manager)

    assert entity.native_value == 50.0


async def test_scalar_editable_forecast_omitted(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Editable scalar fields do not add forecast attributes."""
    subentry = _create_subentry("Test Battery", {"capacity": 7.5})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, scalar_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    assert entity.native_value == 7.5
    attributes = entity.extra_state_attributes or {}
    assert "forecast" not in attributes


async def test_editable_none_value_has_no_native_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """An optional scalar field set to none resolves to EDITABLE with no value."""
    subentry = _create_subentry("Test Battery", {"capacity": None})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, scalar_field_info, device_entry, horizon_manager)

    assert entity.entity_mode == InputMode.EDITABLE
    assert entity.native_value is None


# --- Tests for forecast attribute building ---


async def test_editable_time_series_builds_forecast_attribute(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Editable interval fields build a forecast attribute aligned to interval starts."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]
    # Interval field: one value per interval (boundaries - 1)
    assert len(forecast) == 2
    assert [point["time"].timestamp() for point in forecast] == [0.0, 300.0]
    assert all(point["value"] == 10.0 for point in forecast)


async def test_editable_boundaries_builds_forecast_attribute(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    boundary_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Editable boundary fields build a forecast attribute with one value per boundary."""
    subentry = _create_subentry("Test Battery", {"soc": 50.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, boundary_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]
    assert len(forecast) == 3
    assert [point["time"].timestamp() for point in forecast] == [0.0, 300.0, 600.0]


async def test_horizon_change_updates_forecast_timestamps_editable(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Horizon change re-resolves the editable forecast against the new timestamps."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    # Track state writes by wrapping async_write_ha_state
    state_writes: list[dict[str, Any]] = []
    original_write = entity.async_write_ha_state

    def capturing_write() -> None:
        attrs = entity.extra_state_attributes
        state_writes.append({"forecast": attrs.get("forecast") if attrs else None})
        original_write()

    entity.async_write_ha_state = capturing_write  # type: ignore[method-assign]

    # Change horizon and trigger update
    horizon_manager.get_forecast_timestamps.return_value = (100.0, 400.0, 700.0)
    entity._handle_horizon_change()

    assert len(state_writes) == 1, "Horizon change should trigger state write"
    written_forecast = state_writes[0]["forecast"]
    assert written_forecast is not None
    assert len(written_forecast) == 2
    assert [point["time"].timestamp() for point in written_forecast] == [100.0, 400.0]


# --- Tests for mode and forecast metadata properties ---


async def test_entity_mode_property(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """entity_mode property returns the entity's mode."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    assert entity.entity_mode == InputMode.EDITABLE

    subentry_driven = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    entity_driven = _make_entity(hass, config_entry, subentry_driven, power_field_info, device_entry, horizon_manager)
    assert entity_driven.entity_mode == InputMode.DRIVEN


async def test_uses_forecast_reflects_field_info(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """uses_forecast is True for time-series fields, False for scalar fields."""
    config_entry.runtime_data = None

    forecast_entity = _make_entity(
        hass,
        config_entry,
        _create_subentry("Test Battery", {"power_limit": 10.0}),
        power_field_info,
        device_entry,
        horizon_manager,
    )
    assert forecast_entity.uses_forecast is True

    scalar_entity = _make_entity(
        hass,
        config_entry,
        _create_subentry("Test Battery", {"capacity": 13.5}),
        scalar_field_info,
        device_entry,
        horizon_manager,
    )
    assert scalar_entity.uses_forecast is False


# --- Tests for lifecycle methods ---


async def test_async_added_to_hass_editable_uses_config_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_added_to_hass uses config value in EDITABLE mode (no restore needed)."""
    subentry = _create_subentry("Test Battery", {"power_limit": 15.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    # Should use config value directly
    assert entity.native_value == 15.0


async def test_async_added_to_hass_driven_subscribes_to_source(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_added_to_hass subscribes to and loads from source entity in DRIVEN mode."""
    hass.states.async_set("sensor.power", "10.0")
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    # Entity should have loaded data from source
    assert entity.native_value == 10.0


async def test_driven_scalar_loads_current_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Scalar driven fields load current values without forecasting."""
    hass.states.async_set("sensor.capacity", "12.0")
    subentry = _create_subentry("Test Battery", {"capacity": ["sensor.capacity"]})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, scalar_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    assert entity.native_value == 12.0
    attributes = entity.extra_state_attributes or {}
    assert "forecast" not in attributes


async def test_driven_missing_source_keeps_value_none(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """A driven entity whose source entity is missing has no value."""
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    await _add_entity_to_hass(hass, entity)

    assert entity.native_value is None
    assert entity.is_ready() is False


# --- Tests for horizon and source state change handlers ---


@pytest.mark.parametrize(
    ("handler", "event"),
    [
        pytest.param("horizon", None, id="horizon_change"),
        pytest.param("source_state", Mock(), id="source_state_change"),
    ],
)
async def test_driven_mode_triggers_reload_task(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
    handler: str,
    event: Mock | None,
) -> None:
    """Driven-mode handlers schedule data reload tasks."""
    hass.states.async_set("sensor.power", "10.0")
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)
    entity._async_load_sync_and_update = AsyncMock()
    await _add_entity_to_hass(hass, entity)

    if handler == "horizon":
        entity._handle_horizon_change()
    else:
        mock_event = event or Mock()
        mock_event.data = {"new_state": Mock(state="20.0")}
        entity._handle_source_state_change(mock_event)

    await hass.async_block_till_done()

    entity._async_load_sync_and_update.assert_awaited_once()


async def test_scalar_horizon_change_noop(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Horizon changes do not trigger reloads for scalar fields."""
    subentry = _create_subentry("Test Battery", {"capacity": ["sensor.capacity"]})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, scalar_field_info, device_entry, horizon_manager)
    entity._async_load_sync_and_update = AsyncMock()

    entity._handle_horizon_change()
    await hass.async_block_till_done()

    entity._async_load_sync_and_update.assert_not_awaited()


# --- Tests for readiness ---


async def test_is_ready_after_added_to_hass(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """is_ready() becomes True once the editable entity is added and refreshed."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    # Before adding to hass, not ready
    assert entity.is_ready() is False

    await _add_entity_to_hass(hass, entity)

    # Now ready
    assert entity.is_ready() is True


async def test_wait_ready_blocks_until_data_loaded(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """wait_ready() blocks until the store is marked ready."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = _make_entity(hass, config_entry, subentry, power_field_info, device_entry, horizon_manager)

    # Before data is loaded, is_ready is False
    assert entity.is_ready() is False

    # Start wait_ready in background
    wait_task = asyncio.create_task(entity.wait_ready())

    # Give task a chance to start
    await asyncio.sleep(0)

    # Task should not complete yet
    assert not wait_task.done()

    # Mark the store ready
    entity.store.mark_ready()

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
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
    record_forecasts: bool,
    expect_unrecorded: bool,
) -> None:
    """Number entity applies recorder filtering based on record_forecasts config."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            "name": "Test Network",
            CONF_RECORD_FORECASTS: record_forecasts,
            "tier_1_count": 2,
            "tier_1_duration": 5,
            "tier_2_count": 0,
            "tier_2_duration": 15,
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    subentry = _create_subentry("Test Battery", {"power_limit": 10.5})
    entry.runtime_data = None

    entity = _make_entity(hass, entry, subentry, power_field_info, device_entry, horizon_manager)

    entity._state_info = {"unrecorded_attributes": frozenset()}
    entity._apply_recorder_attribute_filtering()
    if expect_unrecorded:
        assert entity._state_info["unrecorded_attributes"] == FORECAST_UNRECORDED_ATTRIBUTES
    else:
        assert entity._state_info["unrecorded_attributes"] == frozenset()
