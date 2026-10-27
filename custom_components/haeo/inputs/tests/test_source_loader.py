"""Tests for the loader that keeps entity-driven and constant input stores loaded."""

from collections.abc import Callable
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.inputs.source_loader import SourceInputLoader


class _Storage:
    """Storage double that keeps written values."""

    async def write(self, value: object) -> None:
        """Ignore writes."""


def _horizon(timestamps: tuple[float, ...] = (0.0, 300.0, 600.0)) -> Mock:
    """Return a horizon manager whose subscribers can be called."""
    manager = Mock(spec=HorizonManager)
    manager.get_forecast_timestamps.return_value = timestamps
    return manager


def _horizon_callback(manager: Mock) -> Callable[[], None]:
    """Return the callback the loader subscribed to the horizon."""
    ((callback,), _kwargs) = manager.subscribe.call_args
    return callback


def _store(value: object, manager: Mock, *, time_series: bool = False) -> InputStore:
    """Return a power store reading the given value over the manager's horizon."""
    return create_input_store(
        value=value,
        storage=_Storage(),
        hint=FieldHint(output_type=OutputType.POWER, time_series=time_series),
        get_forecast_timestamps=manager.get_forecast_timestamps,
    )


async def test_start_loads_every_store_without_any_entity(hass: HomeAssistant) -> None:
    """Driven and editable stores load at start, so an input loads even when its entity is disabled."""
    hass.states.async_set("sensor.power", "2.5")
    manager = _horizon()
    driven = _store(as_entity_value(["sensor.power"]), manager)
    editable = _store(as_constant_value(4.0), manager)

    SourceInputLoader(hass, {("A", ("driven",)): driven, ("A", ("editable",)): editable}, manager).start()

    assert driven.is_ready()
    assert driven.value == pytest.approx(2.5)
    assert editable.is_ready()
    assert editable.value == pytest.approx(4.0)


async def test_calendar_stores_are_left_to_the_calendar_loader(hass: HomeAssistant) -> None:
    """A store with a calendar source is not loaded from the calendar's plain state."""
    hass.states.async_set("calendar.trips", "on")
    manager = _horizon()
    store = _store(as_entity_value(["calendar.trips"]), manager)

    SourceInputLoader(hass, {("EV", ("away",)): store}, manager).start()

    assert not store.is_ready()


async def test_source_changes_in_one_pass_share_one_reload(hass: HomeAssistant) -> None:
    """Sources written together reload their store once, seeing all of their values."""
    hass.states.async_set("sensor.a", "1.0")
    hass.states.async_set("sensor.b", "2.0")
    manager = _horizon()
    store = _store(as_entity_value(["sensor.a", "sensor.b"]), manager)
    SourceInputLoader(hass, {("A", ("power",)): store}, manager).start()
    listener = Mock()
    store.add_listener(listener)

    hass.states.async_set("sensor.a", "3.0")
    hass.states.async_set("sensor.b", "4.0")
    await hass.async_block_till_done()

    listener.assert_called_once()
    assert store.value == pytest.approx(7.0)


async def test_unchanged_reload_does_not_notify(hass: HomeAssistant) -> None:
    """A source update that leaves the value unchanged does not wake the optimizer."""
    hass.states.async_set("sensor.power", "10.0")
    manager = _horizon()
    store = _store(as_entity_value(["sensor.power"]), manager)
    SourceInputLoader(hass, {("A", ("power",)): store}, manager).start()
    listener = Mock()
    store.add_listener(listener)

    hass.states.async_set("sensor.power", "10.0", {"friendly_name": "Power"})
    await hass.async_block_till_done()

    listener.assert_not_called()


async def test_horizon_change_reloads_every_store_before_returning(hass: HomeAssistant) -> None:
    """A horizon move reloads at once, so no store lags the horizon an optimization reads."""
    hass.states.async_set("sensor.power", "1.0")
    manager = _horizon()
    driven = _store(as_entity_value(["sensor.power"]), manager, time_series=True)
    editable = _store(as_constant_value(2.0), manager, time_series=True)
    loader = SourceInputLoader(hass, {("A", ("driven",)): driven, ("A", ("editable",)): editable}, manager)
    loader.start()

    manager.get_forecast_timestamps.return_value = (300.0, 600.0, 900.0)
    _horizon_callback(manager)()

    assert driven.forecast_timestamps == (300.0, 600.0, 900.0)
    assert editable.forecast_timestamps == (300.0, 600.0, 900.0)
    assert editable.display_values == (2.0, 2.0)


async def test_cleanup_stops_following_sources(hass: HomeAssistant) -> None:
    """After cleanup, neither a queued reload nor a later source change loads the store."""
    hass.states.async_set("sensor.power", "1.0")
    manager = _horizon()
    store = _store(as_entity_value(["sensor.power"]), manager)
    loader = SourceInputLoader(hass, {("A", ("power",)): store}, manager)
    loader.start()

    hass.states.async_set("sensor.power", "2.0")
    assert loader._pending_reload is not None
    loader.cleanup()
    await hass.async_block_till_done()
    hass.states.async_set("sensor.power", "3.0")
    await hass.async_block_till_done()

    assert store.value == pytest.approx(1.0)
    manager.subscribe.return_value.assert_called_once()
