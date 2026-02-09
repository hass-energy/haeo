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

from custom_components.haeo.const import CONF_NAME, CONF_RECORD_FORECASTS, DOMAIN
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.haeo_number import (
    FORECAST_UNRECORDED_ATTRIBUTES,
    ConfigEntityMode,
    HaeoInputNumber,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.model import OutputType
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.sections import CONF_CONNECTION, SECTION_COMMON, SECTION_EFFICIENCY

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
                SECTION_COMMON: {CONF_NAME: name},
                SECTION_EFFICIENCY: {key: schema_value(value) for key, value in data.items()},
            }
        ),
        subentry_type="battery",
        title=name,
        unique_id=None,
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
    config_entry.runtime_data = None  # No runtime data yet

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.EDITABLE
    assert entity._source_entity_ids == []
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
    assert attrs["direction"] == "+"
    assert attrs["time_series"] is True


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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock async_write_ha_state and config entry update
    entity.async_write_ha_state = Mock()
    hass.config_entries.async_update_subentry = Mock()
    await _add_entity_to_hass(hass, entity)
    entity.async_write_ha_state.reset_mock()

    await entity.async_set_native_value(15.0)

    assert entity.native_value == 15.0
    entity.async_write_ha_state.assert_called_once()
    hass.config_entries.async_update_subentry.assert_called_once()
    # Flag should be cleared after update
    assert mock_runtime_data.value_update_in_progress is False


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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.DRIVEN
    assert entity._source_entity_ids == ["sensor.power_limit"]
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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.DRIVEN
    assert entity._source_entity_ids == ["sensor.power1", "sensor.power2"]


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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    expected_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_efficiency.{power_field_info.field_name}"
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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

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
                SECTION_COMMON: {CONF_NAME: "My Battery", CONF_CONNECTION: as_connection_target("Bus")},
                SECTION_EFFICIENCY: {power_field_info.field_name: as_none_value()},
            }
        ),
        subentry_type="battery",
        title="My Battery",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.should_poll is False


# --- Tests for horizon_start and get_values properties ---


async def test_horizon_start_returns_first_timestamp(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """horizon_start returns the first forecast timestamp."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Update forecast manually to simulate loaded state
    entity._update_editable_forecast()

    # horizon_start should return the first timestamp
    assert entity.horizon_start == 0.0


async def test_horizon_start_returns_none_without_forecast(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """horizon_start returns None when forecast is not set."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Clear forecast
    entity._attr_extra_state_attributes = {}

    assert entity.horizon_start is None


async def test_get_values_returns_forecast_values(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """get_values returns tuple of forecast values."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.5})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Update forecast
    entity._update_editable_forecast()

    values = entity.get_values()
    assert values is not None
    # All values should be 10.5
    assert all(v == 10.5 for v in values)
    # Should have 2 values (one per period, boundaries - 1)
    assert len(values) == 2


async def test_get_values_scales_percentage_fields(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    percent_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Percentage-based fields should be normalized to ratios."""
    subentry = _create_subentry("Test Battery", {"soc": 50.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=percent_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    entity._update_editable_forecast()

    values = entity.get_values()
    assert values == (0.5, 0.5)


async def test_get_values_returns_none_without_forecast(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """get_values returns None when forecast is not set."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Clear forecast
    entity._attr_extra_state_attributes = {}

    assert entity.get_values() is None


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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
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
    """async_added_to_hass subscribes to source entity in DRIVEN mode."""
    hass.states.async_set("sensor.power", "10.0")
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    await _add_entity_to_hass(hass, entity)

    # Entity should have loaded data from source
    assert entity.native_value == 10.0


# --- Tests for horizon and source state change handlers ---


async def test_handle_horizon_change_editable_updates_forecast(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_handle_horizon_change updates forecast in EDITABLE mode."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    await _add_entity_to_hass(hass, entity)

    # Call horizon change handler
    entity._handle_horizon_change()

    assert entity.horizon_start == 0.0
    values = entity.get_values()
    assert values is not None
    assert len(values) == 2


async def test_horizon_change_updates_forecast_timestamps_editable(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Horizon change updates forecast timestamps in EDITABLE mode.

    This test verifies that when the horizon changes, EDITABLE mode entities
    write their updated state to Home Assistant (not just update internal attributes).
    """
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    await _add_entity_to_hass(hass, entity)

    # Build initial forecast
    entity._update_editable_forecast()
    assert entity.horizon_start == 0.0

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

    # Verify state was written with new forecast timestamps
    assert len(state_writes) == 1, "Horizon change should trigger state write"
    written_forecast = state_writes[0]["forecast"]
    assert written_forecast is not None
    assert len(written_forecast) == 2
    assert [point["time"].timestamp() for point in written_forecast] == [100.0, 400.0]


async def test_horizon_change_updates_forecast_timestamps_driven(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Horizon change updates forecast timestamps in DRIVEN mode.

    This test verifies that when the horizon changes, DRIVEN mode entities
    write their updated state to Home Assistant (not just update internal attributes).
    The regression being tested: calling _async_load_data() instead of
    _async_load_data_and_update() would update internal state but NOT write to HA.
    """
    hass.states.async_set("sensor.power", "10.0")
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity._loader.load_intervals = AsyncMock(return_value=[1.0, 2.0])
    await _add_entity_to_hass(hass, entity)
    entity._loader.load_intervals.reset_mock()

    # Load initial data
    entity._loader.load_intervals = AsyncMock(return_value=[1.0, 2.0])
    await entity._async_load_data()
    assert entity.horizon_start == 0.0

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
    entity._loader.load_intervals = AsyncMock(return_value=[3.0, 4.0])
    entity._handle_horizon_change()
    await hass.async_block_till_done()

    # Verify state was written with new forecast timestamps
    assert len(state_writes) == 1, "Horizon change should trigger state write"
    written_forecast = state_writes[0]["forecast"]
    assert written_forecast is not None
    assert len(written_forecast) == 2
    assert [point["time"].timestamp() for point in written_forecast] == [100.0, 400.0]


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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity._async_load_data_and_update = AsyncMock()
    entity._loader.load_intervals = AsyncMock(return_value=[1.0, 2.0])
    await _add_entity_to_hass(hass, entity)

    if handler == "horizon":
        entity._handle_horizon_change()
    else:
        mock_event = event or Mock()
        mock_event.data = {"new_state": Mock(state="20.0")}
        entity._handle_source_state_change(mock_event)

    await hass.async_block_till_done()

    entity._async_load_data_and_update.assert_awaited_once()


@pytest.mark.parametrize(
    ("load_result", "load_error"),
    [
        pytest.param([], None, id="empty_values"),
        pytest.param(None, Exception("Load failed"), id="load_failure"),
    ],
)
async def test_async_load_data_handles_empty_or_failure(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
    load_result: list[float] | None,
    load_error: Exception | None,
) -> None:
    """_async_load_data handles empty values or loader failures gracefully."""
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    entity._loader = Mock()
    if load_error is not None:
        entity._loader.load_intervals = AsyncMock(side_effect=load_error)
    else:
        entity._loader.load_intervals = AsyncMock(return_value=load_result)
    await _add_entity_to_hass(hass, entity)

    await entity._async_load_data()

    assert entity.native_value is None


# --- Tests for scalar mode ---


async def test_scalar_driven_loads_current_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Scalar fields load current values without forecasting."""
    subentry = _create_subentry("Test Battery", {"capacity": ["sensor.capacity"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    entity._scalar_loader.load = AsyncMock(return_value=12.0)
    await _add_entity_to_hass(hass, entity)
    entity._scalar_loader.load.reset_mock()

    await entity._async_load_data()

    assert entity.native_value == 12.0
    assert entity.get_values() == (12.0,)
    attributes = entity.extra_state_attributes or {}
    assert "forecast" not in attributes
    entity._scalar_loader.load.assert_awaited_once()


async def test_scalar_load_data_returns_without_sources(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Scalar load returns early when no source entities are configured."""
    subentry = _create_subentry("Test Battery", {"capacity": None})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await entity._async_load_data()

    assert entity.is_ready() is False
    assert entity.native_value is None
    assert entity.get_values() is None


async def test_scalar_load_data_handles_loader_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Scalar load errors do not update entity state."""
    subentry = _create_subentry("Test Battery", {"capacity": ["sensor.capacity"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity._scalar_loader.load = AsyncMock(side_effect=RuntimeError("Load failed"))

    await _add_entity_to_hass(hass, entity)

    assert entity.is_ready() is False
    assert entity.native_value is None


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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity._async_load_data_and_update = AsyncMock()

    entity._handle_horizon_change()
    await hass.async_block_till_done()

    entity._async_load_data_and_update.assert_not_awaited()


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

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    entity._update_editable_forecast()

    assert entity.get_values() == (7.5,)
    attributes = entity.extra_state_attributes or {}
    assert "forecast" not in attributes


async def test_scalar_get_values_percent(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_percent_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Scalar percentage values are returned as ratios."""
    subentry = _create_subentry("Test Battery", {"soc": 50.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_percent_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.get_values() == (0.5,)
    attributes = entity.extra_state_attributes or {}
    assert "forecast" not in attributes


# --- Tests for boundaries mode ---


async def test_editable_mode_with_boundaries_field(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    boundary_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity with boundaries=True field builds correct forecast."""
    subentry = _create_subentry("Test Battery", {"soc": 50.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=boundary_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Update forecast
    entity._update_editable_forecast()

    # With boundaries=True and 3 timestamps, should have 3 values (n+1 values for n+1 boundaries)
    values = entity.get_values()
    assert values is not None
    assert len(values) == 3  # All 3 boundary timestamps
    assert all(v == 0.5 for v in values)


async def test_async_load_data_with_boundaries_field(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    boundary_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_async_load_data uses load_boundaries for boundaries=True fields."""
    subentry = _create_subentry("Test Battery", {"soc": ["sensor.soc"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=boundary_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock loader to return boundary values (n+1 values)
    # Use AsyncMock to properly mock the async method
    entity._loader.load_boundaries = AsyncMock(return_value=[10.0, 20.0, 30.0])
    entity._loader.load_intervals = AsyncMock()
    await _add_entity_to_hass(hass, entity)
    entity._loader.load_boundaries.reset_mock()
    entity._loader.load_intervals.reset_mock()

    await entity._async_load_data()

    # Should call load_boundaries, not load_intervals
    entity._loader.load_boundaries.assert_called_once()
    entity._loader.load_intervals.assert_not_called()

    # Should have 3 values
    assert entity.native_value == 10.0
    values = entity.get_values()
    assert values == (0.1, 0.2, 0.3)


async def test_entity_mode_property(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """entity_mode property returns the entity's mode."""
    # Test EDITABLE mode
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.entity_mode == ConfigEntityMode.EDITABLE

    # Test DRIVEN mode
    subentry_driven = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    entity_driven = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry_driven,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity_driven.entity_mode == ConfigEntityMode.DRIVEN


async def test_async_load_data_with_empty_values_list(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_async_load_data returns early when loader returns empty list."""
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock loader to return empty list (not an exception, just empty result)
    entity._loader.load_intervals = AsyncMock(return_value=[])
    await _add_entity_to_hass(hass, entity)

    initial_value = entity.native_value
    await entity._async_load_data()

    # State should not have changed
    assert entity.native_value == initial_value


async def test_is_ready_returns_true_after_data_loaded(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """is_ready() returns True after data has been loaded."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Before adding to hass, not ready
    assert entity.is_ready() is False

    # Update forecast to simulate loaded state
    entity._update_editable_forecast()

    # Now ready
    assert entity.is_ready() is True


async def test_driven_mode_with_v01_single_entity_string(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in DRIVEN mode handles v0.1 single entity ID string format."""
    # v0.1 format stored entity ID as plain string, not list
    subentry = _create_subentry("Test Battery", {"power_limit": "sensor.power_limit"})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.DRIVEN
    assert entity._source_entity_ids == ["sensor.power_limit"]
    assert entity.native_value is None  # Not loaded yet

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["config_mode"] == "driven"
    assert attrs["source_entities"] == ["sensor.power_limit"]


async def test_wait_ready_blocks_until_data_loaded(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """wait_ready() blocks until data is loaded."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Before data is loaded, is_ready is False
    assert entity.is_ready() is False

    # Start wait_ready in background
    wait_task = asyncio.create_task(entity.wait_ready())

    # Give task a chance to start
    await asyncio.sleep(0)

    # Task should not complete yet
    assert not wait_task.done()

    # Load data (sets the event)
    entity._update_editable_forecast()

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
    """Number entity sets _unrecorded_attributes based on record_forecasts config."""
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

    entity = HaeoInputNumber(
        config_entry=entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    if expect_unrecorded:
        assert entity._unrecorded_attributes == FORECAST_UNRECORDED_ATTRIBUTES
    else:
        assert not hasattr(entity, "_unrecorded_attributes") or entity._unrecorded_attributes == frozenset()
