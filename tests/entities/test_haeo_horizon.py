"""Tests for the HAEO horizon entity."""

from datetime import datetime
from unittest.mock import Mock

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity

# --- Fixtures ---


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry for horizon entity tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            "name": "Test Network",
            "tier_1_count": 2,
            "tier_1_duration": 5,  # 5 minutes
            "tier_2_count": 1,
            "tier_2_duration": 15,  # 15 minutes
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        entry_id="test_horizon_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def device_entry() -> Mock:
    """Return a mock device entry."""
    device = Mock(spec=DeviceEntry)
    device.id = "mock-horizon-device-id"
    return device


# --- Tests for initialization ---


def test_horizon_entity_initialization(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """Horizon entity initializes with correct attributes."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    # Check basic attributes
    assert entity.unique_id == f"{config_entry.entry_id}_horizon"
    assert entity._attr_translation_key == "horizon"
    assert entity.should_poll is False

    # Check computed period durations (5min, 5min, 15min)
    assert entity._periods_seconds == [300, 300, 900]
    assert entity._smallest_period == 300  # 5 minutes


def test_horizon_entity_with_empty_tiers(
    hass: HomeAssistant,
    device_entry: Mock,
) -> None:
    """Horizon entity raises error with config with all zero counts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Empty Network",
        data={
            "name": "Empty Network",
            "tier_1_count": 0,
            "tier_1_duration": 5,
            "tier_2_count": 0,
            "tier_2_duration": 15,
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        entry_id="empty_entry",
    )

    # Empty tiers is an invalid configuration - should raise ValueError
    with pytest.raises(ValueError, match="min\\(\\) iterable argument is empty"):
        HaeoHorizonEntity(
            hass=hass,
            config_entry=entry,
            device_entry=device_entry,
        )


# --- Tests for forecast timestamps ---


def test_get_forecast_timestamps_returns_tuple(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """get_forecast_timestamps returns a tuple of floats."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    timestamps = entity.get_forecast_timestamps()

    assert isinstance(timestamps, tuple)
    assert len(timestamps) == 4  # 3 periods + 1 end = 4 fence posts
    assert all(isinstance(ts, float) for ts in timestamps)


def test_get_forecast_timestamps_has_correct_intervals(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """get_forecast_timestamps returns timestamps with correct intervals."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    timestamps = entity.get_forecast_timestamps()

    # Check intervals between fence posts
    # periods are: 5min (300s), 5min (300s), 15min (900s)
    assert timestamps[1] - timestamps[0] == 300.0
    assert timestamps[2] - timestamps[1] == 300.0
    assert timestamps[3] - timestamps[2] == 900.0


def test_scheduled_update_writes_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """Scheduled update triggers state write for HA state tracking."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )
    entity.async_write_ha_state = Mock()

    # Trigger the scheduled update callback
    entity._async_scheduled_update(dt_util.utcnow())

    entity.async_write_ha_state.assert_called_once()


# --- Tests for state attributes ---


def test_extra_state_attributes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """Entity has expected extra state attributes."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
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
    device_entry: Mock,
) -> None:
    """Forecast attribute contains list of timestamp dicts."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]

    assert isinstance(forecast, list)
    assert len(forecast) == 4  # 4 fence posts

    # Each entry should have time and value keys
    for entry in forecast:
        assert "time" in entry
        assert "value" in entry
        assert isinstance(entry["time"], datetime)
        assert entry["value"] is None  # Horizon doesn't have values


def test_native_value_is_start_time_iso(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """Native value is the start timestamp in ISO format."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    # Native value should be a string (ISO format)
    assert entity.native_value is not None
    assert isinstance(entity.native_value, str)


# --- Tests for entity category ---


def test_entity_category_is_diagnostic(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """Entity should be DIAGNOSTIC category."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    assert entity.entity_category == EntityCategory.DIAGNOSTIC


# --- Tests for lifecycle ---


async def test_async_added_to_hass_schedules_timer(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """Adding entity to hass schedules the update timer."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    # Timer should be scheduled after init
    assert entity._unsub_timer is None

    # After adding to hass, timer should be set
    await entity.async_added_to_hass()
    assert entity._unsub_timer is not None


async def test_async_will_remove_from_hass_cancels_timer(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
) -> None:
    """Removing entity from hass cancels the timer."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
    )

    await entity.async_added_to_hass()
    assert entity._unsub_timer is not None

    await entity.async_will_remove_from_hass()
    assert entity._unsub_timer is None
