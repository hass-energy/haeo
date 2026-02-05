"""Tests for the HAEO horizon entity."""

from datetime import datetime, timedelta
import logging
from unittest.mock import Mock

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_NAME, DOMAIN
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity
from custom_components.haeo.horizon import HorizonManager

# --- Fixtures ---


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry for horizon entity tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            "basic": {CONF_NAME: "Test Network"},
            "tiers": {
                "tier_1_count": 2,
                "tier_1_duration": 5,  # 5 minutes
                "tier_2_count": 1,
                "tier_2_duration": 15,  # 15 minutes
                "tier_3_count": 0,
                "tier_3_duration": 30,
                "tier_4_count": 0,
                "tier_4_duration": 60,
            },
            "advanced": {},
        },
        entry_id="test_horizon_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def horizon_manager(hass: HomeAssistant, config_entry: MockConfigEntry) -> HorizonManager:
    """Return a HorizonManager for tests."""
    return HorizonManager(hass, config_entry)


@pytest.fixture
def device_entry() -> Mock:
    """Return a mock device entry."""
    device = Mock(spec=DeviceEntry)
    device.id = "mock-horizon-device-id"
    return device


async def _add_entity_to_hass(hass: HomeAssistant, entity: Entity) -> None:
    """Add entity to Home Assistant via a real EntityPlatform."""
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain="sensor",
        platform_name=DOMAIN,
        platform=None,
        scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    await platform.async_add_entities([entity])
    await hass.async_block_till_done()


# --- Tests for initialization ---


def test_horizon_entity_initialization(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Horizon entity initializes with correct attributes."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Check basic attributes
    assert entity.unique_id == f"{config_entry.entry_id}_horizon"
    assert entity._attr_translation_key == "horizon"
    assert entity.should_poll is False


# --- Tests for forecast timestamps ---


def test_entity_reflects_horizon_manager_timestamps(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Entity reflects timestamps from horizon manager."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Get timestamps from manager
    manager_timestamps = horizon_manager.get_forecast_timestamps()

    # Get forecast from entity attributes
    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]

    # Should have same number of boundaries
    assert len(forecast) == len(manager_timestamps)

    # Timestamps should match
    for i, entry in enumerate(forecast):
        expected_time = datetime.fromtimestamp(manager_timestamps[i], tz=dt_util.get_default_time_zone())
        assert entry["time"] == expected_time


# --- Tests for state attributes ---


def test_extra_state_attributes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Entity has expected extra state attributes."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    attrs = entity.extra_state_attributes
    assert attrs is not None

    assert "forecast" in attrs
    assert "period_count" in attrs
    assert "smallest_period_seconds" in attrs
    assert attrs["period_count"] == 3
    assert attrs["smallest_period_seconds"] == 300


def test_forecast_attribute_contains_timestamps(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Forecast attribute contains list of timestamp dicts."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]

    assert isinstance(forecast, list)
    assert len(forecast) == 4  # 4 boundaries

    # Each entry should have time and value keys
    for entry in forecast:
        assert "time" in entry
        assert "value" in entry
        assert isinstance(entry["time"], datetime)
        assert entry["value"] is None  # Horizon doesn't have values


def test_native_value_is_start_time_iso(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Native value is the start timestamp in ISO format."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Native value should be a string (ISO format)
    assert entity.native_value is not None
    assert isinstance(entity.native_value, str)


# --- Tests for entity category ---


def test_entity_category_is_diagnostic(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Entity should be DIAGNOSTIC category."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.entity_category == EntityCategory.DIAGNOSTIC


# --- Tests for lifecycle ---


async def test_async_added_to_hass_subscribes_to_manager(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Adding entity to hass subscribes to horizon manager."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await _add_entity_to_hass(hass, entity)

    # Entity should have state attributes after being added
    assert entity.extra_state_attributes is not None


async def test_horizon_entity_updates_on_manager_change(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Entity updates state when horizon manager changes."""
    entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Mock async_write_ha_state
    entity.async_write_ha_state = Mock()  # type: ignore[method-assign]

    await _add_entity_to_hass(hass, entity)
    entity.async_write_ha_state.reset_mock()

    # Call the horizon change handler directly
    entity._async_horizon_changed()

    # Should have written state
    entity.async_write_ha_state.assert_called_once()


# --- Tests for HorizonManager ---


def test_horizon_manager_current_start_time(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager current_start_time returns datetime from timestamps."""
    manager = HorizonManager(hass, config_entry)
    manager.start()

    # current_start_time should return a datetime
    start_time = manager.current_start_time
    assert start_time is not None
    assert isinstance(start_time, datetime)

    manager.stop()


def test_horizon_manager_current_start_time_none_when_no_timestamps(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager current_start_time returns None when no timestamps."""
    manager = HorizonManager(hass, config_entry)
    # Don't start - so _forecast_timestamps should be empty
    # Actually, __init__ calls _update_timestamps, so manually clear
    manager._forecast_timestamps = ()

    assert manager.current_start_time is None


async def test_horizon_manager_scheduled_update_notifies_subscribers(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager scheduled update notifies all subscribers."""
    manager = HorizonManager(hass, config_entry)

    # Track callback calls
    callback_count = 0

    def test_callback() -> None:
        nonlocal callback_count
        callback_count += 1

    manager.subscribe(test_callback)

    # Manually call the scheduled update handler
    manager._async_scheduled_update(dt_util.now())

    # Callback should have been called
    assert callback_count == 1

    manager.stop()


async def test_horizon_manager_scheduled_update_reschedules(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager scheduled update schedules next update."""
    manager = HorizonManager(hass, config_entry)
    manager.start()

    # Clear the timer
    if manager._unsub_timer is not None:
        manager._unsub_timer()
        manager._unsub_timer = None

    # Call scheduled update - should schedule next update
    manager._async_scheduled_update(dt_util.now())

    # Timer should be rescheduled
    assert manager._unsub_timer is not None

    manager.stop()


# --- Tests for pause/resume ---


async def test_horizon_manager_pause_cancels_timer(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager pause cancels the update timer."""
    manager = HorizonManager(hass, config_entry)
    manager.start()

    # Verify timer is running
    assert manager._unsub_timer is not None

    # Pause should cancel the timer
    manager.pause()

    assert manager._unsub_timer is None

    # Clean up
    manager.stop()


async def test_horizon_manager_pause_preserves_subscribers(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager pause preserves subscribers unlike stop."""
    manager = HorizonManager(hass, config_entry)
    manager.start()

    callback_count = 0

    def test_callback() -> None:
        nonlocal callback_count
        callback_count += 1

    manager.subscribe(test_callback)

    # Pause should preserve subscribers
    manager.pause()

    # Subscribers should still be registered
    assert len(manager._subscribers) == 1

    # Clean up
    manager.stop()


async def test_horizon_manager_resume_updates_timestamps(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager resume updates timestamps to current time."""
    manager = HorizonManager(hass, config_entry)
    manager.start()

    # Get initial timestamps
    initial_timestamps = manager.get_forecast_timestamps()

    # Pause
    manager.pause()

    # Resume should update timestamps
    manager.resume()

    resumed_timestamps = manager.get_forecast_timestamps()

    # Timestamps may have changed if time passed, or be the same if within same period
    # But they should be valid (not empty)
    assert len(resumed_timestamps) > 0
    assert len(resumed_timestamps) == len(initial_timestamps)

    # Clean up
    manager.stop()


async def test_horizon_manager_resume_notifies_subscribers(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager resume notifies all subscribers."""
    manager = HorizonManager(hass, config_entry)
    manager.start()

    callback_count = 0

    def test_callback() -> None:
        nonlocal callback_count
        callback_count += 1

    manager.subscribe(test_callback)

    # Pause
    manager.pause()

    # Resume should notify subscribers
    manager.resume()

    assert callback_count == 1

    # Clean up
    manager.stop()


async def test_horizon_manager_resume_restarts_timer(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """HorizonManager resume restarts the update timer."""
    manager = HorizonManager(hass, config_entry)
    manager.start()

    # Pause cancels timer
    manager.pause()
    assert manager._unsub_timer is None

    # Resume should restart timer
    manager.resume()

    assert manager._unsub_timer is not None

    # Clean up
    manager.stop()
