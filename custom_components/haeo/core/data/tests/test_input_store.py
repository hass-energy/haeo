"""Unit tests for the InputStore data container.

These tests exercise the store in isolation from Home Assistant. They use the
shared ``FakeStateMachine``/``FakeEntityState`` doubles from the root conftest
and a tiny in-memory storage double so values resolve identically to the config
loader (``resolve_field``/``resolve_constant``).
"""

import asyncio
import logging
import time
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import numpy as np
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.input_store import InputMode, InputStore, _same_value, create_input_store
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.field_hints import FieldHint, calendar_input

FORECAST_TIMESTAMPS: tuple[float, ...] = (0.0, 300.0, 600.0)


def _timestamps() -> tuple[float, ...]:
    """Return a fixed set of forecast timestamps for tests."""
    return FORECAST_TIMESTAMPS


class _MemStorage:
    """In-memory storage double implementing the Storage protocol."""

    def __init__(self, value: object = None) -> None:
        self.value = value
        self.written: list[object] = []

    async def write(self, value: object) -> None:
        self.written.append(value)
        self.value = value


def _make_store(
    *,
    storage_value: object = None,
    output_type: OutputType = OutputType.ENERGY,
    time_series: bool = False,
    boundaries: bool = False,
    negate: bool = False,
) -> InputStore:
    """Build an InputStore from an in-memory storage value and field hint."""
    storage = _MemStorage(storage_value)
    hint = FieldHint(output_type=output_type, time_series=time_series, boundaries=boundaries)
    return create_input_store(
        value=storage.value, storage=storage, hint=hint, get_forecast_timestamps=_timestamps, negate=negate
    )


# --- Editable constant resolution ---


def test_editable_constant_scalar() -> None:
    """Editable scalar constant resolves to the value and is ready once loaded."""
    store = _make_store(storage_value=42.0, output_type=OutputType.ENERGY, time_series=False)

    assert store.mode == InputMode.EDITABLE
    assert store.source_entity_ids == []
    assert store.value == 42.0
    assert store.native_value == 42.0
    assert store.display_values == (42.0,)
    assert store.available is True

    # Resolved at construction but not ready until loaded.
    assert store.is_ready() is False
    store.load(FakeStateMachine({}))
    assert store.is_ready() is True


def test_editable_constant_time_series_intervals() -> None:
    """Editable time-series interval constant expands to len(ts)-1 values."""
    store = _make_store(
        storage_value=as_constant_value(2.5),
        output_type=OutputType.POWER,
        time_series=True,
        boundaries=False,
    )

    assert isinstance(store.value, np.ndarray)
    assert len(store.value) == len(FORECAST_TIMESTAMPS) - 1
    np.testing.assert_array_equal(store.value, [2.5, 2.5])

    display = store.display_values
    assert display is not None
    assert len(display) == 2


def test_editable_constant_time_series_boundaries() -> None:
    """Editable boundary constant expands to len(ts) values."""
    store = _make_store(
        storage_value=10.0,
        output_type=OutputType.ENERGY,
        time_series=True,
        boundaries=True,
    )

    assert isinstance(store.value, np.ndarray)
    assert len(store.value) == len(FORECAST_TIMESTAMPS)
    np.testing.assert_array_equal(store.value, [10.0, 10.0, 10.0])


def test_editable_percent_field_divides_by_100() -> None:
    """Percent fields store the optimization value as a ratio but display as percent."""
    store = _make_store(storage_value=50.0, output_type=OutputType.STATE_OF_CHARGE, time_series=False)

    assert store.is_percent is True
    assert store.value == pytest.approx(0.5)
    assert store.native_value == pytest.approx(50.0)
    assert store.display_values == pytest.approx((50.0,))


def test_editable_bool_constant() -> None:
    """Boolean editable constants pass through unchanged."""
    store = _make_store(storage_value=as_constant_value(value=True), output_type=OutputType.ENERGY)

    assert store.mode == InputMode.EDITABLE
    assert store.value is True
    assert store.native_value is True
    assert store.display_values == (True,)


def test_hint_property_returns_field_hint() -> None:
    """The hint property exposes the store's field metadata."""
    store = _make_store(storage_value=1.0, output_type=OutputType.PRICE, time_series=True)

    assert store.hint.output_type == OutputType.PRICE
    assert store.hint.time_series is True


def test_display_values_none_when_not_loaded() -> None:
    """display_values is None before any value is resolved."""
    store = _make_store(output_type=OutputType.ENERGY, time_series=False)

    assert store.display_values is None


# --- Mutation: set_value / listeners / persist ---


def test_set_value_marks_ready_and_notifies() -> None:
    """set_value updates the value, marks ready, notifies listeners, and is available."""
    store = _make_store(output_type=OutputType.ENERGY, time_series=False)

    calls: list[int] = []
    store.add_listener(lambda: calls.append(1))

    assert store.is_ready() is False
    store.set_value(7.0)

    assert store.value == 7.0
    assert store.available is True
    assert store.is_ready() is True
    assert calls == [1]


def test_set_value_percent_divides() -> None:
    """set_value on a percent field divides the display value by 100."""
    store = _make_store(output_type=OutputType.STATE_OF_CHARGE, time_series=False)

    store.set_value(80.0)

    assert store.value == pytest.approx(0.8)
    assert store.native_value == pytest.approx(80.0)


def test_add_listener_unsub_removes_listener() -> None:
    """The unsubscribe callable removes the listener so it is no longer notified."""
    store = _make_store(output_type=OutputType.ENERGY, time_series=False)

    calls: list[int] = []
    unsub = store.add_listener(lambda: calls.append(1))

    store.set_value(1.0)
    assert calls == [1]

    unsub()
    store.set_value(2.0)
    assert calls == [1]


async def test_persist_writes_through_storage() -> None:
    """Persist forwards the schema value to the bound storage."""
    storage = _MemStorage()
    hint = FieldHint(output_type=OutputType.ENERGY)
    store = create_input_store(value=storage.value, storage=storage, hint=hint, get_forecast_timestamps=_timestamps)

    await store.persist(as_constant_value(5.0))

    assert storage.written == [as_constant_value(5.0)]


# --- Driven load ---


async def test_driven_load_success() -> None:
    """Driven scalar load resolves from the source entity and becomes ready."""
    store = _make_store(
        storage_value=as_entity_value(["sensor.x"]),
        output_type=OutputType.ENERGY,
        time_series=False,
    )

    assert store.mode == InputMode.DRIVEN

    sm = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "12.0", {})})
    store.load(sm)
    assert store.available

    assert store.value == 12.0
    assert store.available is True
    assert "sensor.x" in store.captured_source_states
    assert store.is_ready() is True


async def test_driven_load_negates_resolved_value() -> None:
    """A negated driven store flips the sign of values resolved from sources."""
    store = _make_store(
        storage_value=as_entity_value(["sensor.x"]),
        output_type=OutputType.PRICE,
        time_series=False,
        negate=True,
    )

    sm = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "0.15", {})})
    store.load(sm)
    assert store.available

    assert store.value == pytest.approx(-0.15)
    assert store.native_value == pytest.approx(-0.15)


async def test_driven_load_negates_time_series() -> None:
    """Negation applies element-wise to time-series source values."""
    store = _make_store(
        storage_value=as_entity_value(["sensor.x"]),
        output_type=OutputType.PRICE,
        time_series=True,
        negate=True,
    )

    sm = FakeStateMachine(
        {"sensor.x": FakeEntityState("sensor.x", "0.2", {"forecast": [0.2, 0.3, 0.4]})},
    )
    store.load(sm)
    assert store.available

    assert isinstance(store.value, np.ndarray)
    assert np.all(store.value < 0)


def test_negate_does_not_affect_editable_constant() -> None:
    """Constants are negated at the storage layer, so the store leaves them as-is."""
    store = _make_store(storage_value=as_constant_value(-0.15), output_type=OutputType.PRICE, negate=True)

    assert store.value == pytest.approx(-0.15)


def test_editable_none_storage_stays_unavailable() -> None:
    """An editable store with no configured value has no resolved data."""
    store = _make_store(storage_value={"type": "none"})

    store.load(FakeStateMachine({}))

    assert store.value is None
    assert store.available is False
    assert store.display_values is None


async def test_driven_load_resolve_failure(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unexpected resolution exception leaves the store unavailable and is logged as a warning with its cause."""
    # HAEO's loggers write to the console only, so let this one reach caplog
    monkeypatch.setattr(logging.getLogger("custom_components.haeo"), "propagate", True)
    store = _make_store(
        storage_value=as_entity_value(["sensor.x"]),
        output_type=OutputType.PRICE,
        time_series=False,
    )
    sm = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "1.0", {})})

    with patch(
        "custom_components.haeo.core.data.input_store.resolve_field",
        side_effect=RuntimeError("boom"),
    ):
        store.load(sm)
        assert not store.available

    assert store.available is False
    [record] = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert record.exc_info is not None
    assert str(record.exc_info[1]) == "boom"


async def test_unexpected_load_error_is_logged_once_until_it_changes_or_the_store_recovers(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repeating unexpected error is logged once, again when it changes, and again after a successful load."""
    # HAEO's loggers write to the console only, so let this one reach caplog
    monkeypatch.setattr(logging.getLogger("custom_components.haeo"), "propagate", True)
    store = _make_store(storage_value=as_entity_value(["sensor.x"]), output_type=OutputType.PRICE, time_series=False)
    sm = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "1.0", {})})
    outcomes: list[Exception | float] = [
        RuntimeError("boom"),
        RuntimeError("boom"),
        KeyError("other"),
        KeyError("other"),
        1.0,
        RuntimeError("boom"),
    ]

    with patch("custom_components.haeo.core.data.input_store.resolve_field", side_effect=outcomes):
        for _ in outcomes:
            if store.load(sm):
                store.notify_listeners()

    warned = [record.exc_info[1] for record in caplog.records if record.levelno == logging.WARNING and record.exc_info]
    assert [repr(error) for error in warned] == ["RuntimeError('boom')", "KeyError('other')", "RuntimeError('boom')"]


async def test_driven_load_rejects_empty_time_series() -> None:
    """An empty time-series result is treated as a failed load."""
    store = _make_store(
        storage_value=as_entity_value(["sensor.x"]),
        output_type=OutputType.PRICE,
        time_series=True,
    )
    sm = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "1.0", {})})

    with patch(
        "custom_components.haeo.core.data.input_store.resolve_field",
        return_value=np.array([]),
    ):
        store.load(sm)
        assert not store.available

    assert store.available is False


async def test_driven_load_without_source_entities() -> None:
    """A driven store with no source entity IDs cannot load."""
    storage = _MemStorage({"type": "entity", "value": []})
    hint = FieldHint(output_type=OutputType.PRICE, time_series=False)
    store = create_input_store(value=storage.value, storage=storage, hint=hint, get_forecast_timestamps=_timestamps)

    sm = FakeStateMachine({})
    store.load(sm)
    assert not store.available
    assert store.available is False


async def test_driven_load_failure_keeps_unavailable() -> None:
    """A missing source entity leaves the store unavailable and not ready."""
    store = _make_store(
        storage_value=as_entity_value(["sensor.x"]),
        output_type=OutputType.ENERGY,
        time_series=False,
    )

    sm = FakeStateMachine({})
    store.load(sm)
    assert not store.available

    assert store.available is False
    assert store.is_ready() is False
    assert store.value is None


@pytest.mark.parametrize(
    ("states", "expected_unavailable"),
    [
        pytest.param({"sensor.a": "1.0", "sensor.b": "unavailable"}, ("sensor.b",), id="unavailable"),
        pytest.param({"sensor.a": "1.0", "sensor.b": "unknown"}, ("sensor.b",), id="unknown"),
        pytest.param({"sensor.a": "1.0"}, ("sensor.b",), id="missing"),
        pytest.param({"sensor.a": "unavailable", "sensor.b": "unknown"}, ("sensor.a", "sensor.b"), id="both"),
        pytest.param({"sensor.a": "1.0", "sensor.b": "not a number"}, (), id="unreadable_state"),
    ],
)
async def test_driven_load_names_sources_without_a_reading(
    states: dict[str, str], expected_unavailable: tuple[str, ...]
) -> None:
    """A failed load names the sources with no reading, and the next good load clears them."""
    store = _make_store(storage_value=as_entity_value(["sensor.a", "sensor.b"]), output_type=OutputType.PRICE)

    sm = FakeStateMachine({eid: FakeEntityState(eid, state, {}) for eid, state in states.items()})
    store.load(sm)
    assert not store.available
    assert store.unavailable_sources == expected_unavailable

    recovered = FakeStateMachine({eid: FakeEntityState(eid, "1.0", {}) for eid in ("sensor.a", "sensor.b")})
    store.load(recovered)
    assert store.available
    assert store.unavailable_sources == ()


async def test_driven_load_records_input_error() -> None:
    """A rejected source value is recorded, reported as a change, and cleared by the next good load."""
    storage = _MemStorage(as_entity_value(["sensor.x"]))
    hint = FieldHint(output_type=OutputType.POWER_LIMIT, time_series=True, min_value=0.0)
    store = create_input_store(value=storage.value, storage=storage, hint=hint, get_forecast_timestamps=_timestamps)

    bad = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "-3.0", {})})
    assert store.load(bad) is True

    assert store.available is False
    assert store.error is not None
    assert store.error.translation_key == "negative_input_value"
    assert store.is_ready() is False
    await asyncio.wait_for(store.wait_settled(), timeout=1)
    assert store.error.translation_placeholders == {"value": "-3"}

    good = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "3.0", {})})
    assert store.load(good) is True
    assert store.available
    assert store.error is None


def _sensor(state: str, **attributes: object) -> FakeStateMachine:
    """Return a state machine holding one sensor.x state."""
    return FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", state, attributes)})


@pytest.mark.parametrize(
    ("time_series", "loads", "expected_notifications"),
    [
        pytest.param(True, [(_sensor("12.0"), FORECAST_TIMESTAMPS)] * 2, 1, id="identical_reload"),
        pytest.param(
            True,
            [(_sensor("12.0"), FORECAST_TIMESTAMPS), (_sensor("12.0", friendly_name="X"), FORECAST_TIMESTAMPS)],
            1,
            id="attribute_only_change",
        ),
        pytest.param(
            True, [(_sensor("12.0"), FORECAST_TIMESTAMPS), (_sensor("13.0"), FORECAST_TIMESTAMPS)], 2, id="changed"
        ),
        pytest.param(
            True,
            [(_sensor("12.0"), FORECAST_TIMESTAMPS), (_sensor("12.0"), (300.0, 600.0, 900.0))],
            2,
            id="new_horizon",
        ),
        pytest.param(
            True,
            [
                (_sensor("12.0"), FORECAST_TIMESTAMPS),
                (FakeStateMachine({}), FORECAST_TIMESTAMPS),
                (FakeStateMachine({}), FORECAST_TIMESTAMPS),
                (_sensor("12.0"), FORECAST_TIMESTAMPS),
            ],
            3,
            id="unavailable_and_back",
        ),
        pytest.param(False, [(_sensor("12.0"), FORECAST_TIMESTAMPS)] * 2, 1, id="identical_scalar_reload"),
        pytest.param(
            False,
            [(_sensor("12.0"), FORECAST_TIMESTAMPS), (_sensor("13.0"), FORECAST_TIMESTAMPS)],
            2,
            id="changed_scalar",
        ),
        pytest.param(True, [(_sensor("-3.0"), FORECAST_TIMESTAMPS)] * 2, 1, id="repeated_rejection"),
        pytest.param(
            True,
            [(_sensor("-3.0"), FORECAST_TIMESTAMPS), (_sensor("-4.0"), FORECAST_TIMESTAMPS)],
            2,
            id="different_rejection",
        ),
        pytest.param(
            True,
            [
                (_sensor("12.0"), FORECAST_TIMESTAMPS),
                (_sensor("-3.0"), FORECAST_TIMESTAMPS),
                (FakeStateMachine({}), FORECAST_TIMESTAMPS),
                (FakeStateMachine({}), FORECAST_TIMESTAMPS),
            ],
            3,
            id="rejection_then_unavailable",
        ),
        pytest.param(
            True,
            [(_sensor("-3.0"), FORECAST_TIMESTAMPS), (_sensor("3.0"), FORECAST_TIMESTAMPS)],
            2,
            id="rejection_then_valid",
        ),
    ],
)
async def test_driven_load_notifies_only_on_change(
    time_series: bool,
    loads: list[tuple[FakeStateMachine, tuple[float, ...]]],
    expected_notifications: int,
) -> None:
    """Reloading an identical value does not notify, so it does not trigger optimization."""
    horizon = [FORECAST_TIMESTAMPS]
    storage = _MemStorage(as_entity_value(["sensor.x"]))
    hint = FieldHint(output_type=OutputType.POWER_LIMIT, time_series=time_series, min_value=0.0)
    store = create_input_store(
        value=storage.value, storage=storage, hint=hint, get_forecast_timestamps=lambda: horizon[0]
    )
    notifications: list[None] = []
    store.add_listener(lambda: notifications.append(None))

    for sm, timestamps in loads:
        horizon[0] = timestamps
        if store.load(sm):
            store.notify_listeners()

    assert len(notifications) == expected_notifications


@pytest.mark.parametrize(
    ("time_series", "constant", "timestamps", "expected_notifications"),
    [
        pytest.param(False, 5.0, FORECAST_TIMESTAMPS, 0, id="same_constant"),
        pytest.param(False, 6.0, FORECAST_TIMESTAMPS, 1, id="new_constant"),
        pytest.param(False, 5.0, (300.0, 600.0, 900.0), 0, id="scalar_new_horizon"),
        pytest.param(True, 5.0, FORECAST_TIMESTAMPS, 0, id="time_series_same_horizon"),
        pytest.param(True, 5.0, (300.0, 600.0, 900.0), 1, id="time_series_new_horizon"),
    ],
)
def test_editable_notifies_only_on_change(
    time_series: bool,
    constant: float,
    timestamps: tuple[float, ...],
    expected_notifications: int,
) -> None:
    """Editable stores follow the same rule as driven ones: only a changed value or horizon notifies."""
    horizon = [FORECAST_TIMESTAMPS]
    storage = _MemStorage(as_constant_value(5.0))
    hint = FieldHint(output_type=OutputType.POWER, time_series=time_series)
    store = create_input_store(
        value=storage.value, storage=storage, hint=hint, get_forecast_timestamps=lambda: horizon[0]
    )
    store.load(FakeStateMachine({}))
    notifications: list[None] = []
    store.add_listener(lambda: notifications.append(None))

    horizon[0] = timestamps
    store.set_value(constant)

    assert store.is_ready()
    assert len(notifications) == expected_notifications


def test_same_value_treats_nan_as_equal() -> None:
    """An unchanged forecast containing NaN does not count as a change."""
    previous = np.array([1.0, np.nan])

    assert _same_value(previous, previous.copy())
    assert _same_value(float("nan"), float("nan"))
    assert not _same_value(previous, np.array([1.0, 2.0]))
    assert not _same_value(1.0, True)


# --- Construction errors ---


@pytest.mark.parametrize(
    ("storage_value", "expected"),
    [
        pytest.param(as_constant_value(2), 2.0, id="int_constant"),
        pytest.param({"type": "constant", "value": np.int64(2)}, 2.0, id="numpy_int_constant"),
        pytest.param(np.int64(2), 2.0, id="bare_numpy_int"),
        pytest.param(as_constant_value(True), True, id="bool_constant"),
    ],
)
def test_create_input_store_reads_any_real_constant(storage_value: object, expected: float | bool) -> None:
    """Any real number counts as a constant, as is_constant_value accepts, and booleans stay booleans."""
    store = _make_store(storage_value=storage_value)

    store.load(FakeStateMachine({}))

    assert store.value == expected
    assert type(store.value) is type(expected)


def test_create_input_store_invalid_config_raises() -> None:
    """An unrecognized schema dict raises a RuntimeError."""
    storage = _MemStorage({"type": "unknown_kind", "value": 1.0})
    hint = FieldHint(output_type=OutputType.ENERGY)

    with pytest.raises(RuntimeError, match="Invalid config value"):
        create_input_store(value=storage.value, storage=storage, hint=hint, get_forecast_timestamps=_timestamps)


# --- horizon_start ---


def test_horizon_start_time_series_returns_first_timestamp() -> None:
    """Time-series editable stores expose the first forecast timestamp."""
    store = _make_store(storage_value=1.0, output_type=OutputType.POWER, time_series=True)

    store.load(FakeStateMachine({}))

    assert store.horizon_start == FORECAST_TIMESTAMPS[0]


def test_horizon_start_scalar_returns_none() -> None:
    """Scalar stores have no loaded timestamps so horizon_start is None."""
    store = _make_store(storage_value=1.0, output_type=OutputType.ENERGY, time_series=False)

    store.load(FakeStateMachine({}))

    assert store.horizon_start is None


# --- Calendar inputs ---


def _make_calendar_store() -> InputStore:
    """Build a store for a calendar input, reading an ordinary entity value."""
    storage = _MemStorage({"type": "entity", "value": ["calendar.trips"]})
    return create_input_store(
        value=storage.value,
        storage=storage,
        hint=calendar_input(OutputType.AVAILABILITY, "window_active"),
        get_forecast_timestamps=_timestamps,
    )


async def test_calendar_store_resolves_injected_events_like_a_sensor() -> None:
    """A calendar input is an ordinary driven store whose source state carries injected events."""
    store = _make_calendar_store()
    event = {
        "start": "1970-01-01T00:00:00+00:00",
        "end": "1970-01-01T00:05:00+00:00",
        "summary": "Trip",
        "location": None,
        "description": None,
    }
    sm = FakeStateMachine(
        {"calendar.trips": FakeEntityState("calendar.trips", "on", {CALENDAR_EVENTS_ATTRIBUTE: [event]})}
    )

    assert store.mode == InputMode.DRIVEN
    store.load(sm)
    assert store.available
    assert store.available
    assert store.display_values == (1.0, 0.0)
    assert store.forecast_timestamps == FORECAST_TIMESTAMPS


@pytest.mark.parametrize(
    "states",
    [
        pytest.param({}, id="missing_state"),
        pytest.param({"calendar.trips": FakeEntityState("calendar.trips", "on", {})}, id="no_injected_events"),
    ],
)
async def test_calendar_store_without_injected_events_is_unavailable(states: dict[str, FakeEntityState]) -> None:
    """A calendar input whose state is missing or carries no events fails to load."""
    store = _make_calendar_store()

    store.load(FakeStateMachine(states))

    assert not store.available
    assert not store.available


async def test_driven_store_reads_listed_states_as_on_and_off() -> None:
    """A store whose entity value lists the states meaning off reads its entity's words as on or off."""
    store = _make_store(
        storage_value=as_entity_value(["sensor.charger"], off_states=["Idle"]),
        output_type=OutputType.AVAILABILITY,
        time_series=True,
    )

    store.load(FakeStateMachine({"sensor.charger": FakeEntityState("sensor.charger", "Charging", {})}))
    np.testing.assert_allclose(np.asarray(store.value), [1.0, 1.0])

    store.load(FakeStateMachine({"sensor.charger": FakeEntityState("sensor.charger", "Idle", {})}))
    np.testing.assert_allclose(np.asarray(store.value), [0.0, 0.0])
    assert store.captured_source_states["sensor.charger"].state == "Idle"


def _held_store(hold_seconds: float, *, time_series: bool = False) -> InputStore:
    """Build a store summing two price sensors that holds a missing sensor's reading for ``hold_seconds``."""
    storage = _MemStorage(as_entity_value(["sensor.a", "sensor.b"]))
    hint = FieldHint(output_type=OutputType.PRICE, time_series=time_series)
    return create_input_store(
        value=storage.value,
        storage=storage,
        hint=hint,
        get_forecast_timestamps=_timestamps,
        hold_seconds=hold_seconds,
    )


def _prices(a: str, b: str) -> FakeStateMachine:
    """Return a state machine where the two price sensors read ``a`` and ``b``."""
    return FakeStateMachine(
        {"sensor.a": FakeEntityState("sensor.a", a, {}), "sensor.b": FakeEntityState("sensor.b", b, {})}
    )


def test_held_reading_keeps_the_store_available_and_follows_live_sources(freezer: FrozenDateTimeFactory) -> None:
    """A source without a reading resolves from its last reading, while the other sources stay live."""
    store = _held_store(60)
    store.load(_prices("1.0", "2.0"))

    freezer.tick(5)
    lost_at = time.time()
    assert store.load(_prices("1.0", "unavailable")) is True

    assert store.available
    assert store.value == pytest.approx(3.0)
    assert store.unavailable_sources == ()
    assert store.held_sources == {"sensor.b": lost_at}
    assert store.oldest_held_source == ("sensor.b", lost_at)
    assert store.hold_expires_at == lost_at + 60
    assert store.captured_source_states["sensor.b"].state == "2.0"

    freezer.tick(30)
    assert store.load(_prices("4.0", "unknown")) is True
    assert store.available
    assert store.value == pytest.approx(6.0)
    assert store.held_sources == {"sensor.b": lost_at}


def test_held_reading_resolves_over_the_current_horizon(freezer: FrozenDateTimeFactory) -> None:
    """A held reading of a forecast input is resolved over the horizon the store loads for."""
    horizon = [FORECAST_TIMESTAMPS]
    storage = _MemStorage(as_entity_value(["sensor.a", "sensor.b"]))
    store = create_input_store(
        value=storage.value,
        storage=storage,
        hint=FieldHint(output_type=OutputType.PRICE, time_series=True),
        get_forecast_timestamps=lambda: horizon[0],
        hold_seconds=60,
    )
    store.load(_prices("1.0", "2.0"))

    freezer.tick(5)
    horizon[0] = (300.0, 600.0, 900.0)
    store.load(_prices("1.0", "unavailable"))

    assert store.available
    assert store.forecast_timestamps == (300.0, 600.0, 900.0)
    assert isinstance(store.value, np.ndarray)
    np.testing.assert_allclose(store.value, [3.0, 3.0])


@pytest.mark.parametrize("hold_seconds", [0, 60], ids=["strict", "held"])
def test_reading_older_than_the_hold_makes_the_store_unavailable(
    freezer: FrozenDateTimeFactory, hold_seconds: float
) -> None:
    """A source without a reading for the hold or longer makes the store unavailable, keeping its value."""
    store = _held_store(hold_seconds)
    store.load(_prices("1.0", "2.0"))

    store.load(_prices("1.0", "unavailable"))
    assert store.available is (hold_seconds > 0)
    freezer.tick(hold_seconds)
    store.load(_prices("1.0", "unavailable"))

    assert not store.available
    assert store.value == pytest.approx(3.0)
    assert store.unavailable_sources == ("sensor.b",)
    assert store.held_sources == {}
    assert store.hold_expires_at is None


def test_source_without_a_previous_reading_is_not_held() -> None:
    """A source that has never had a reading leaves the store unavailable, whatever the hold."""
    store = _held_store(60)

    store.load(_prices("1.0", "unavailable"))

    assert not store.available
    assert store.unavailable_sources == ("sensor.b",)
    assert store.held_sources == {}


def test_expire_holds_marks_the_store_unavailable_once_the_hold_passes(freezer: FrozenDateTimeFactory) -> None:
    """Expiring a hold with no reload makes the store unavailable, naming every source without a reading."""
    store = _held_store(60)
    store.load(_prices("1.0", "2.0"))
    store.load(_prices("unavailable", "unavailable"))

    freezer.tick(59)
    assert store.expire_holds() is False
    assert store.available

    freezer.tick(1)
    assert store.expire_holds() is True
    assert not store.available
    assert store.unavailable_sources == ("sensor.a", "sensor.b")
    assert store.expire_holds() is False


def test_oldest_held_source_is_the_one_without_a_reading_longest(freezer: FrozenDateTimeFactory) -> None:
    """With several sources held, the hold expires with the one that lost its reading first."""
    store = _held_store(60)
    store.load(_prices("1.0", "2.0"))
    store.load(_prices("1.0", "unavailable"))
    b_lost_at = time.time()

    freezer.tick(10)
    store.load(_prices("unavailable", "unavailable"))

    assert store.oldest_held_source == ("sensor.b", b_lost_at)
    assert store.hold_expires_at == b_lost_at + 60


@pytest.mark.parametrize("expired", [False, True], ids=["while_held", "after_expiry"])
def test_reading_returning_clears_the_hold(freezer: FrozenDateTimeFactory, expired: bool) -> None:
    """A source that reads again is live, and a later gap starts a new hold."""
    store = _held_store(60)
    store.load(_prices("1.0", "2.0"))
    store.load(_prices("1.0", "unavailable"))
    freezer.tick(61 if expired else 5)
    store.expire_holds()

    assert store.load(_prices("1.0", "5.0")) is True
    assert store.available
    assert store.value == pytest.approx(6.0)
    assert store.held_sources == {}
    assert store.unavailable_sources == ()

    freezer.tick(1)
    store.load(_prices("1.0", "unavailable"))
    assert store.available
    assert store.held_sources == {"sensor.b": time.time()}
