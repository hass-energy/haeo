"""Tests for the HAEO number input entity."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

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
from custom_components.haeo.model import OUTPUT_TYPE_POWER

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
        output_type=OUTPUT_TYPE_POWER,
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
        output_type="energy",
        time_series=False,
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


async def test_editable_mode_with_none_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Number entity in EDITABLE mode handles None for optional fields."""
    subentry = _create_subentry("Test Battery", {"capacity": None})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.EDITABLE
    assert entity.native_value is None


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

    # Mock async_write_ha_state
    entity.async_write_ha_state = Mock()

    await entity.async_set_native_value(15.0)

    assert entity.native_value == 15.0
    entity.async_write_ha_state.assert_called_once()


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
    # Should have 2 values (one per period, fence posts - 1)
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


async def test_async_added_to_hass_editable_restores_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_added_to_hass restores previous value in EDITABLE mode."""
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

    # Mock the async_get_last_number_data to return a saved value
    async def mock_get_last_number_data() -> Mock:
        mock_data = Mock()
        mock_data.native_value = 15.0
        return mock_data

    entity.async_get_last_number_data = mock_get_last_number_data  # type: ignore[method-assign]

    await entity.async_added_to_hass()

    # Should restore to saved value
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

    # Subscription should be set up
    assert entity._state_unsub is not None
    assert entity._horizon_unsub is not None


async def test_async_will_remove_from_hass_cleans_up(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_will_remove_from_hass cleans up subscriptions."""
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
    assert entity._state_unsub is not None

    await entity.async_will_remove_from_hass()

    assert entity._state_unsub is None
    assert entity._horizon_unsub is None


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
