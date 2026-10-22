"""Tests for the HAEO horizon entity."""

from collections.abc import Iterator
from datetime import datetime, timedelta
import logging
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from freezegun import freeze_time
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import (
    CONF_HORIZON,
    CONF_NAME,
    HORIZON_PRESET_2_DAYS,
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
)
from custom_components.haeo.core.schema.entity_value import as_entity_value
from custom_components.haeo.core.schema.horizon_value import HorizonValue, as_horizon_preset_value
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity
from custom_components.haeo.horizon import HorizonManager

ADELAIDE = ZoneInfo("Australia/Adelaide")
T4_PERIOD_SECONDS = 3600
HORIZON_ENTITY_ID = "sensor.horizon_source"

# Boundaries of two 5 minute periods followed by one 15 minute period
HORIZON_START = 1735732800.0  # 2025-01-01 12:00:00 UTC
HORIZON_BOUNDARIES = (HORIZON_START, HORIZON_START + 300, HORIZON_START + 600, HORIZON_START + 1500)

# --- Fixtures ---


def _set_horizon_entity(hass: HomeAssistant, boundaries: tuple[float, ...], state: str = "0") -> None:
    """Set the horizon entity to a forecast whose times are the given boundaries."""
    hass.states.async_set(
        HORIZON_ENTITY_ID,
        state,
        {
            "unit_of_measurement": "kW",
            "forecast": [
                {"time": datetime.fromtimestamp(boundary, tz=dt_util.UTC).isoformat(), "value": 0}
                for boundary in boundaries
            ],
        },
    )


def _hub_entry(hass: HomeAssistant, horizon: HorizonValue) -> MockConfigEntry:
    """Add a hub config entry with the given horizon."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            HUB_SECTION_COMMON: {CONF_NAME: "Test Network", CONF_HORIZON: horizon},
            HUB_SECTION_ADVANCED: {},
        },
        entry_id="test_horizon_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry whose horizon comes from a forecast entity."""
    _set_horizon_entity(hass, HORIZON_BOUNDARIES)
    return _hub_entry(hass, as_entity_value([HORIZON_ENTITY_ID]))


@pytest.fixture
def preset_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry using a horizon preset."""
    return _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_2_DAYS))


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

    for entry in forecast:
        assert "time" in entry
        assert "value" not in entry
        assert isinstance(entry["time"], datetime)


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


def _horizon_t4_boundary_local_minutes(
    periods_seconds: list[int],
    timestamps: tuple[float, ...],
) -> list[int]:
    """Return local minutes-of-hour for each T4 period end boundary."""
    minutes: list[int] = []
    for index, period in enumerate(periods_seconds):
        if period == T4_PERIOD_SECONDS:
            local_dt = datetime.fromtimestamp(timestamps[index + 1], tz=ADELAIDE)
            minutes.append(local_dt.minute)
    return minutes


@pytest.fixture
def adelaide_timezone(hass: HomeAssistant) -> Iterator[None]:
    """Set Home Assistant default timezone to Adelaide for the test."""
    original = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(ADELAIDE)
    yield
    dt_util.set_default_time_zone(original)


def test_horizon_manager_reads_entity_horizon(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """An entity horizon takes its boundaries and periods from the entity's forecast times."""
    manager = HorizonManager(hass, config_entry)

    assert manager.get_forecast_timestamps() == HORIZON_BOUNDARIES
    assert manager.periods_seconds == [300, 300, 900]
    assert manager.smallest_period == 300


async def test_horizon_manager_entity_change_updates_horizon(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """A change to the horizon entity updates the horizon and notifies subscribers."""
    manager = HorizonManager(hass, config_entry)
    manager.start()
    subscriber = Mock()
    manager.subscribe(subscriber)

    new_boundaries = (HORIZON_START + 60, HORIZON_START + 120, HORIZON_START + 1920)
    _set_horizon_entity(hass, new_boundaries)
    await hass.async_block_till_done()

    assert manager.get_forecast_timestamps() == new_boundaries
    assert manager.periods_seconds == [60, 1800]
    assert manager.smallest_period == 60
    subscriber.assert_called_once()

    manager.stop()


@pytest.mark.parametrize(
    "attributes",
    [
        pytest.param(None, id="removed"),
        pytest.param({}, id="no_forecast"),
        pytest.param(
            {"unit_of_measurement": "kW", "forecast": [{"time": "2025-01-01T12:00:00+00:00", "value": 0}]},
            id="single_time",
        ),
    ],
)
async def test_horizon_manager_invalid_entity_update_keeps_horizon(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    attributes: dict[str, object] | None,
) -> None:
    """An entity update without a usable forecast keeps the previous horizon without notifying subscribers."""
    manager = HorizonManager(hass, config_entry)
    manager.start()
    subscriber = Mock()
    manager.subscribe(subscriber)

    if attributes is None:
        hass.states.async_remove(HORIZON_ENTITY_ID)
    else:
        hass.states.async_set(HORIZON_ENTITY_ID, "unavailable", attributes)
    await hass.async_block_till_done()

    assert manager.get_forecast_timestamps() == HORIZON_BOUNDARIES
    assert manager.periods_seconds == [300, 300, 900]
    subscriber.assert_not_called()

    manager.stop()


async def test_horizon_manager_entity_change_with_same_boundaries_does_not_notify(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """An entity change that leaves the forecast times unchanged does not notify subscribers."""
    manager = HorizonManager(hass, config_entry)
    manager.start()
    subscriber = Mock()
    manager.subscribe(subscriber)

    _set_horizon_entity(hass, HORIZON_BOUNDARIES, state="1")
    await hass.async_block_till_done()

    subscriber.assert_not_called()

    manager.stop()


async def test_horizon_manager_resume_after_start_keeps_one_listener(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Resuming a started manager replaces its entity listener, so changes notify once and stop ends them."""
    manager = HorizonManager(hass, config_entry)
    manager.start()
    manager.resume()
    subscriber = Mock()
    manager.subscribe(subscriber)

    _set_horizon_entity(hass, (HORIZON_START + 60, HORIZON_START + 120))
    await hass.async_block_till_done()
    subscriber.assert_called_once()

    manager.stop()
    _set_horizon_entity(hass, (HORIZON_START + 120, HORIZON_START + 180))
    await hass.async_block_till_done()
    assert manager.get_forecast_timestamps() == (HORIZON_START + 60, HORIZON_START + 120)


@pytest.mark.parametrize("entity_attributes", [None, {}], ids=["missing", "no_forecast"])
async def test_horizon_manager_unready_entity_raises(
    hass: HomeAssistant,
    entity_attributes: dict[str, object] | None,
) -> None:
    """Without a usable horizon entity at setup the config entry is not ready."""
    if entity_attributes is not None:
        hass.states.async_set(HORIZON_ENTITY_ID, "unavailable", entity_attributes)
    entry = _hub_entry(hass, as_entity_value([HORIZON_ENTITY_ID]))

    with pytest.raises(ConfigEntryNotReady) as exc_info:
        HorizonManager(hass, entry)

    assert exc_info.value.translation_key == "horizon_entity_not_ready"
    assert exc_info.value.translation_placeholders == {"entity_id": HORIZON_ENTITY_ID}


@freeze_time(datetime(2025, 6, 2, 12, 0, 0, tzinfo=ADELAIDE))
def test_horizon_manager_adelaide_preset_aligns_t4_to_local_hour(
    hass: HomeAssistant,
    adelaide_timezone: None,
) -> None:
    """HorizonManager preset horizons align T4 boundaries to local :00 in Adelaide."""
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))

    manager = HorizonManager(hass, entry)
    t4_minutes = _horizon_t4_boundary_local_minutes(
        manager.periods_seconds,
        manager.get_forecast_timestamps(),
    )

    assert t4_minutes, "expected at least one T4 boundary"
    assert t4_minutes[0] == 0, "first T4 boundary should align to local hour (:00)"
    assert all(minute == 0 for minute in t4_minutes), "all T4 boundaries should fall on local hour"


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
    preset_config_entry: MockConfigEntry,
) -> None:
    """HorizonManager scheduled update notifies all subscribers."""
    manager = HorizonManager(hass, preset_config_entry)

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
    preset_config_entry: MockConfigEntry,
) -> None:
    """HorizonManager scheduled update schedules next update."""
    manager = HorizonManager(hass, preset_config_entry)
    manager.start()

    # Clear the timer
    if manager._unsub_update is not None:
        manager._unsub_update()
        manager._unsub_update = None

    # Call scheduled update - should schedule next update
    manager._async_scheduled_update(dt_util.now())

    # Timer should be rescheduled
    assert manager._unsub_update is not None

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
    assert manager._unsub_update is not None

    # Pause should cancel the timer
    manager.pause()

    assert manager._unsub_update is None

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
    assert manager._unsub_update is None

    # Resume should restart timer
    manager.resume()

    assert manager._unsub_update is not None

    # Clean up
    manager.stop()
