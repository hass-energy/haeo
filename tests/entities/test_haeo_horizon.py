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
from custom_components.haeo.horizon import HorizonManager

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
def horizon_manager(hass: HomeAssistant, config_entry: MockConfigEntry) -> HorizonManager:
    """Return a HorizonManager for tests."""
    return HorizonManager(hass, config_entry)


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
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Horizon entity initializes with correct attributes."""
    entity = HaeoHorizonEntity(
        hass=hass,
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
        hass=hass,
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

    # Should have same number of fence posts
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
        hass=hass,
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
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
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
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Native value is the start timestamp in ISO format."""
    entity = HaeoHorizonEntity(
        hass=hass,
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
        hass=hass,
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
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Subscription should be None before added to hass
    assert entity._unsub_horizon is None

    # After adding to hass, subscription should be set
    await entity.async_added_to_hass()
    assert entity._unsub_horizon is not None


async def test_async_will_remove_from_hass_unsubscribes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: HorizonManager,
    device_entry: Mock,
) -> None:
    """Removing entity from hass unsubscribes from manager."""
    entity = HaeoHorizonEntity(
        hass=hass,
        config_entry=config_entry,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await entity.async_added_to_hass()
    assert entity._unsub_horizon is not None

    await entity.async_will_remove_from_hass()
    assert entity._unsub_horizon is None
