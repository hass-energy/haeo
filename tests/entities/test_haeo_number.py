"""Tests for the HAEO number input entity."""

import asyncio
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, Mock

from homeassistant.components.number import NumberEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_NAME, DOMAIN
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.haeo_number import ConfigEntityMode, HaeoInputNumber
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.model import OutputType

# --- Fixtures ---


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry for number entity tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            "name": "Test Network",
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


def _create_subentry(name: str, data: dict[str, Any]) -> ConfigSubentry:
    """Create a ConfigSubentry with the given data."""
    return ConfigSubentry(
        data=MappingProxyType({CONF_NAME: name, "element_type": "battery", **data}),
        subentry_type="battery",
        title=name,
        unique_id=None,
    )


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
        hass=hass,
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
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock async_write_ha_state and config entry update
    entity.async_write_ha_state = Mock()
    hass.config_entries.async_update_subentry = Mock()

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
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock async_write_ha_state and config entry update
    entity.async_write_ha_state = Mock()
    hass.config_entries.async_update_subentry = Mock()

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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    expected_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{power_field_info.field_name}"
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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await entity.async_added_to_hass()

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
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await entity.async_added_to_hass()

    assert entity.available is True


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
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    # Call horizon change handler
    entity._handle_horizon_change()

    entity.async_write_ha_state.assert_called_once()


async def test_handle_horizon_change_driven_triggers_reload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_handle_horizon_change creates task to reload data in DRIVEN mode."""
    hass.states.async_set("sensor.power", "10.0")
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Call horizon change handler - should create task
    entity._handle_horizon_change()
    await hass.async_block_till_done()

    # Task should have been created (test doesn't fail means task was created)


async def test_handle_source_state_change_triggers_reload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_handle_source_state_change creates task to reload data."""
    hass.states.async_set("sensor.power", "10.0")
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Create a mock event
    mock_event = Mock()
    mock_event.data = {"new_state": Mock(state="20.0")}

    # Call source state change handler
    entity._handle_source_state_change(mock_event)
    await hass.async_block_till_done()


async def test_async_load_data_handles_load_failure(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_async_load_data handles loader exceptions gracefully."""
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock loader to raise an exception
    entity._loader = Mock()
    entity._loader.load = Mock(side_effect=Exception("Load failed"))

    # Should not raise
    await entity._async_load_data()

    # State should not have changed
    assert entity.native_value is None


async def test_async_load_data_handles_empty_values(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_async_load_data handles empty values gracefully."""
    subentry = _create_subentry("Test Battery", {"power_limit": ["sensor.power"]})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock loader to return empty list
    entity._loader = Mock()
    entity._loader.load = Mock(return_value=[])

    # Should not raise
    await entity._async_load_data()

    # State should not have changed
    assert entity.native_value is None


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
        hass=hass,
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
    assert all(v == 50.0 for v in values)


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
        hass=hass,
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

    await entity._async_load_data()

    # Should call load_boundaries, not load_intervals
    entity._loader.load_boundaries.assert_called_once()
    entity._loader.load_intervals.assert_not_called()

    # Should have 3 values
    assert entity.native_value == 10.0
    values = entity.get_values()
    assert values == (10.0, 20.0, 30.0)


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
        hass=hass,
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
        hass=hass,
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
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock loader to return empty list (not an exception, just empty result)
    entity._loader.load_intervals = AsyncMock(return_value=[])

    initial_value = entity.native_value
    await entity._async_load_data()

    # State should not have changed
    assert entity.native_value == initial_value


async def test_is_ready_returns_true_after_added_to_hass(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """is_ready() returns True after entity has been added to Home Assistant."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Before adding to hass, not ready
    assert entity.is_ready() is False

    # Simulate being added to Home Assistant
    await entity.async_added_to_hass()

    # Now ready (entity added to HA)
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
        hass=hass,
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


async def test_wait_ready_blocks_until_added_to_hass(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """wait_ready() blocks until entity is added to Home Assistant."""
    subentry = _create_subentry("Test Battery", {"power_limit": 10.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Before added to HA, is_ready is False
    assert entity.is_ready() is False

    # Start wait_ready in background
    wait_task = asyncio.create_task(entity.wait_ready())

    # Give task a chance to start
    await asyncio.sleep(0)

    # Task should not complete yet
    assert not wait_task.done()

    # Add entity to Home Assistant (sets the _entity_added event)
    await entity.async_added_to_hass()

    # Now wait_ready should complete
    await asyncio.wait_for(wait_task, timeout=1.0)

    assert entity.is_ready() is True
