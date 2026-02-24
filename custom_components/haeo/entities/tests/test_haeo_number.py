"""Tests for the HAEO number input entity."""

import logging
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

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
from custom_components.haeo.core.model import OutputType
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.sections import CONF_CONNECTION, SECTION_EFFICIENCY
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.haeo_number import (
    FORECAST_UNRECORDED_ATTRIBUTES,
    ConfigEntityMode,
    HaeoInputNumber,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager

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


async def test_driven_mode_inert_until_update_display(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """DRIVEN entities start with native_value=None and only get values via update_display()."""
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

    # DRIVEN entities are inert after async_added_to_hass - no data loading
    assert entity.native_value is None

    # Values only arrive via update_display()
    entity.update_display([10.0, 20.0], (0.0, 300.0, 600.0))

    assert entity.native_value == 10.0


# --- Tests for update_display ---


async def test_update_display_scalar_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    scalar_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """update_display with a scalar value updates native_value without forecast."""
    subentry = _create_subentry("Test Battery", {"capacity": 5.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=scalar_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    entity.update_display(42.0, (0.0, 300.0, 600.0))

    assert entity.native_value == 42.0
    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert "forecast" not in attrs
    entity.async_write_ha_state.assert_called_once()


async def test_update_display_time_series_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    power_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """update_display with time series values updates native_value and forecast attribute."""
    subentry = _create_subentry("Test Battery", {"power_limit": 5.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    forecast_times = (0.0, 300.0, 600.0)
    entity.update_display([10.0, 20.0], forecast_times)

    assert entity.native_value == 10.0
    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]
    assert len(forecast) == 2
    assert all(isinstance(point["time"], datetime) for point in forecast)
    assert [point["time"].timestamp() for point in forecast] == [0.0, 300.0]
    assert [point["value"] for point in forecast] == [10.0, 20.0]
    entity.async_write_ha_state.assert_called_once()


async def test_update_display_boundary_time_series_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    boundary_field_info: InputFieldInfo[NumberEntityDescription],
    horizon_manager: Mock,
) -> None:
    """update_display with boundaries generates n+1 forecast entries (one per timestamp)."""
    subentry = _create_subentry("Test Battery", {"soc": 50.0})
    config_entry.runtime_data = None

    entity = HaeoInputNumber(
        config_entry=config_entry,
        subentry=subentry,
        field_info=boundary_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    forecast_times = (0.0, 300.0, 600.0)
    entity.update_display([10.0, 20.0, 30.0], forecast_times)

    assert entity.native_value == 10.0
    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]
    # Boundaries: all 3 timestamps get forecast entries (n+1 for n periods)
    assert len(forecast) == 3
    assert [point["time"].timestamp() for point in forecast] == [0.0, 300.0, 600.0]
    assert [point["value"] for point in forecast] == [10.0, 20.0, 30.0]
    entity.async_write_ha_state.assert_called_once()


# --- Tests for entity mode ---


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

    entity = HaeoInputNumber(
        config_entry=entry,
        subentry=subentry,
        field_info=power_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    entity._state_info = {"unrecorded_attributes": frozenset()}
    entity._apply_recorder_attribute_filtering()
    if expect_unrecorded:
        assert entity._state_info["unrecorded_attributes"] == FORECAST_UNRECORDED_ATTRIBUTES
    else:
        assert entity._state_info["unrecorded_attributes"] == frozenset()
