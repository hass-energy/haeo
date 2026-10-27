"""Input data store for HAEO configuration fields.

Holds the live value for a single input field and feeds it to the optimization.
Fully decoupled from Home Assistant: it depends only on the StateMachine
protocol, the shared field resolver, and a Storage binding for persistence.

An ``InputStore`` is the single source of truth for one field's value:

- It is built from configuration (via :func:`create_input_store`) and bound to
  a ``Storage`` that backs it to persistent config.
- DRIVEN stores resolve from source entities through ``async_load``. A source
  that loses its reading has its last reading held for up to ``hold_seconds``,
  so a short gap in one sensor does not make the input unavailable.
- EDITABLE stores hold a constant that is persisted through the storage on
  ``set_value``.
- Consumers (the coordinator) read the resolved ``value`` and subscribe to
  changes via ``add_listener``.
"""

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import tzinfo
from enum import Enum
import logging
from numbers import Real
import time

import numpy as np

from custom_components.haeo.core.data.loader.config_loader import is_percent_field, resolve_constant, resolve_field
from custom_components.haeo.core.data.storage import Storage
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.schema import EntityValue, is_entity_value
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.core.state import NO_READING_STATES, EntityState, StateMachine

type InputValue = bool | float | np.ndarray

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _LostReading:
    """When a source lost its reading, on the monotonic clock for its age and the wall clock for display."""

    monotonic: float
    wall: float


class InputMode(Enum):
    """Operating mode for an input store."""

    EDITABLE = "editable"
    DRIVEN = "driven"


class InputStore:
    """Holds the resolved value for a single input field.

    Pure data container with no Home Assistant dependencies. Loading is
    triggered externally by passing a StateMachine instance (DRIVEN) or by
    setting a value (EDITABLE).

    Parameters
    ----------
        mode: Whether this store is user-editable or driven by entities.
        sources: The entity value that drives this store (None for editable).
        hint: Field hint describing output type, time-series shape, etc.
        get_forecast_timestamps: Callable returning current forecast timestamps.
        storage: Persistence binding backing this store.
        initial_value: Initial constant value (display units) for editable mode.
        negate: When True, values resolved from source entities are negated.
        hold_seconds: How long a source's last reading is held once the source
            has no reading. 0 makes the store unavailable as soon as one does.

    """

    def __init__(
        self,
        *,
        mode: InputMode,
        sources: EntityValue | None,
        hint: FieldHint,
        get_forecast_timestamps: Callable[[], tuple[float, ...]],
        storage: Storage,
        initial_value: float | bool | None = None,
        negate: bool = False,
        hold_seconds: float = 0.0,
    ) -> None:
        """Initialize the input store."""
        self._mode = mode
        self._sources = sources
        self._source_entity_ids = list(sources["value"]) if sources is not None else []
        self._hint = hint
        self._get_forecast_timestamps = get_forecast_timestamps
        self._storage = storage

        # When True, values resolved from source entities are negated so the
        # optimization sees the running cost's negative. Constant (editable)
        # values are negated at the storage layer instead, so this only affects
        # the driven path; see ``async_load``.
        self._negate = negate
        self._hold_seconds = hold_seconds

        self._constant: float | bool | None = initial_value
        self._value: InputValue | None = None
        self._available = False
        self._error: InputError | None = None
        # The last unexpected load error logged, so a repeating one is logged once
        self._logged_failure: str | None = None
        self._unavailable_sources: tuple[str, ...] = ()
        self._loaded_timestamps: tuple[float, ...] = ()
        self._captured_source_states: dict[str, EntityState] = {}
        # The last state with a reading from each source, and when each source without a reading lost it
        self._last_readings: dict[str, EntityState] = {}
        self._missing_since: dict[str, _LostReading] = {}
        # When each source whose last reading the current value holds lost its reading
        self._held_sources: dict[str, _LostReading] = {}
        self._data_ready = asyncio.Event()
        # Set once the store has data or has rejected its source's value
        self._settled = asyncio.Event()
        self._listeners: list[Callable[[], None]] = []

        if mode == InputMode.EDITABLE and initial_value is not None:
            self._resolve_value_from_constant()

    # --- Identity / metadata ---

    @property
    def mode(self) -> InputMode:
        """Return the operating mode."""
        return self._mode

    @property
    def source_entity_ids(self) -> list[str]:
        """Return source entity IDs for driven mode."""
        return self._source_entity_ids

    @property
    def hint(self) -> FieldHint:
        """Return the field hint describing this store's shape."""
        return self._hint

    @property
    def time_series(self) -> bool:
        """Return whether this store produces time-series data."""
        return self._hint.time_series

    @property
    def is_percent(self) -> bool:
        """Return whether values are stored as percentages (display is value x100)."""
        return is_percent_field(self._hint)

    # --- Values ---

    @property
    def value(self) -> InputValue | None:
        """Return the resolved value in optimization units.

        For time-series numeric fields this is a numpy array; for scalar fields
        a float; for boolean fields a bool. ``None`` when not loaded.
        """
        return self._value

    @property
    def available(self) -> bool:
        """Return True when the store currently holds a usable value.

        Editable stores are available once a value is set. Driven stores become
        unavailable when a load fails (their previous value is retained but the
        optimization should be skipped).
        """
        return self._available

    @property
    def error(self) -> InputError | None:
        """Return why the source's last value was rejected, if it was."""
        return self._error

    @property
    def unavailable_sources(self) -> tuple[str, ...]:
        """Return the source entities that had no reading when the store last failed to load.

        Empty while the store is available, and when a load failed for another
        reason, such as sources whose readings could not be combined.
        """
        return self._unavailable_sources

    @property
    def held_sources(self) -> Mapping[str, float]:
        """Return when each source whose last reading the current value holds lost its reading.

        Maps each source with no reading to the time, in seconds since the
        epoch, at which it was first seen without one. Empty while every source
        has a reading, and while the store is unavailable.
        """
        return {eid: lost.wall for eid, lost in self._held_sources.items()}

    @property
    def oldest_held_source(self) -> tuple[str, float] | None:
        """Return the held source that lost its reading first and when it did, or None when no reading is held."""
        if not self._held_sources:
            return None
        eid, lost = min(self._held_sources.items(), key=lambda item: item[1].monotonic)
        return eid, lost.wall

    @property
    def hold_expires_at(self) -> float | None:
        """Return when the oldest held reading becomes too old to use, on the monotonic clock.

        None when no reading is held. The monotonic clock keeps the hold its
        configured length when the wall clock is set.
        """
        if not self._held_sources:
            return None
        return min(lost.monotonic for lost in self._held_sources.values()) + self._hold_seconds

    @property
    def native_value(self) -> float | bool | None:
        """Return the current scalar value in display units.

        Percentage fields are scaled back to 0-100 for presentation. Returns the
        first value for time-series fields.
        """
        value = self._value
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        scalar = float(value[0]) if isinstance(value, np.ndarray) else float(value)
        return scalar * 100.0 if self.is_percent else scalar

    @property
    def display_values(self) -> tuple[float | bool, ...] | None:
        """Return resolved values in display units as a tuple, or None.

        Percentage fields are scaled back to 0-100. Booleans pass through.
        """
        value = self._value
        if value is None:
            return None
        if isinstance(value, bool):
            return (value,)
        raw = tuple(float(v) for v in value) if isinstance(value, np.ndarray) else (float(value),)
        return tuple(v * 100.0 for v in raw) if self.is_percent else raw

    @property
    def forecast_timestamps(self) -> tuple[float, ...]:
        """Return the timestamps that align with the loaded time-series values."""
        return self._loaded_timestamps

    @property
    def horizon_start(self) -> float | None:
        """Return the first loaded forecast timestamp, or None."""
        if self._loaded_timestamps:
            return self._loaded_timestamps[0]
        return None

    @property
    def captured_source_states(self) -> dict[str, EntityState]:
        """Source states captured from the last data load."""
        return self._captured_source_states

    # --- Readiness ---

    def is_ready(self) -> bool:
        """Return True if data has been loaded and store is ready."""
        return self._data_ready.is_set()

    async def wait_ready(self) -> None:
        """Wait for data to be ready."""
        await self._data_ready.wait()

    async def wait_settled(self) -> None:
        """Wait until the store has data or has rejected its source's value."""
        await self._settled.wait()

    # --- Change notification ---

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback fired whenever the resolved value changes.

        Returns an unsubscribe callable.
        """
        self._listeners.append(listener)

        def _unsub() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _unsub

    def notify_listeners(self) -> None:
        """Fire all registered change listeners."""
        for listener in list(self._listeners):
            listener()

    # --- Mutation ---

    def set_value(self, value: float | bool) -> None:  # noqa: FBT001 (bool is a valid input value)
        """Set a new constant value (display units) and re-resolve.

        Updates the resolved value, marks ready, and notifies listeners if the
        value changed. Persistence is performed separately via :meth:`persist`.
        """
        self._constant = value
        if self._resolve_from_constant():
            self.notify_listeners()

    async def persist(self, schema_value: object) -> None:
        """Persist a schema value through the bound storage."""
        await self._storage.write(schema_value)

    def load(self, sm: StateMachine) -> bool:
        """Resolve the value over the current horizon without notifying listeners.

        An editable store resolves its constant and a driven store reads its
        sources, as :meth:`resolve_from_sources` does. Returns True when
        listeners should be notified.
        """
        if self._mode == InputMode.EDITABLE:
            return self._resolve_from_constant()
        return self.resolve_from_sources(sm)

    def resolve_from_sources(self, sm: StateMachine) -> bool:
        """Resolve data from source entities without notifying listeners.

        Lets a caller reload several stores before any listener runs, then
        notify each with :meth:`notify_listeners`. Returns True when listeners
        should be notified because the value, its timestamps, its availability,
        or the reason its source's value was rejected changed. Reloading an
        identical value returns False so consumers do not re-optimize for
        nothing. A failed load keeps the previous value. A rejected value is
        recorded in :attr:`error`, so consumers report it rather than silently
        keeping the previous value.

        A source with no reading resolves from its last reading until it has
        been without one for ``hold_seconds``, and is listed in
        :attr:`held_sources` meanwhile.
        """
        now = _LostReading(monotonic=time.monotonic(), wall=time.time())
        states = {eid: sm.get(eid) for eid in self._source_entity_ids}
        for eid, state in states.items():
            if state is not None and state.state not in NO_READING_STATES:
                self._last_readings[eid] = state
                self._missing_since.pop(eid, None)
            else:
                self._missing_since.setdefault(eid, now)
        held = {
            eid: self._last_readings[eid]
            for eid, lost in self._missing_since.items()
            if eid in self._last_readings and now.monotonic - lost.monotonic < self._hold_seconds
        }
        unavailable_sources = tuple(
            eid for eid in self._source_entity_ids if eid in self._missing_since and eid not in held
        )
        self._captured_source_states = {
            eid: state for eid in self._source_entity_ids if (state := held.get(eid, states[eid])) is not None
        }
        if held:
            sm = _HeldStateMachine(sm, held)

        if self._sources is None or not self._source_entity_ids:
            return self._mark_unavailable(unavailable_sources)

        forecast_timestamps = self._get_forecast_timestamps()
        try:
            resolved = resolve_field(
                self._sources,
                self._hint,
                sm,
                list(forecast_timestamps),
                negate=self._negate,
            )
        except InputError as err:
            changed = self._available or not _same_error(self._error, err)
            self._error = err
            self._available = False
            self._unavailable_sources = ()
            self._held_sources = {}
            self._settled.set()
            return changed
        except Exception as err:
            # Loading runs in state change callbacks, where an exception would
            # stop every other input updating too. The expected failures return
            # None or raise InputError, so anything else is a bug: report it with
            # its traceback, once until it changes or a load succeeds, and mark
            # only this input unavailable.
            if (failure := repr(err)) != self._logged_failure:
                self._logged_failure = failure
                _LOGGER.warning(
                    "Unexpected error loading from sources %s; marking the input unavailable",
                    self._source_entity_ids,
                    exc_info=True,
                )
            return self._mark_unavailable(unavailable_sources)

        if (
            resolved is None
            or not isinstance(resolved, (bool, float, int, np.ndarray))
            or (isinstance(resolved, np.ndarray) and resolved.size == 0)
        ):
            _LOGGER.debug(
                "Load returned no value from sources %s; keeping previous value",
                self._source_entity_ids,
            )
            return self._mark_unavailable(unavailable_sources)

        held_sources = {eid: self._missing_since[eid] for eid in held}
        changed = self._commit(resolved, forecast_timestamps) or held_sources != self._held_sources
        self._held_sources = held_sources
        self._data_ready.set()
        self._settled.set()
        return changed

    def expire_holds(self) -> bool:
        """Mark the store unavailable once its oldest held reading is too old, and return whether it was.

        A held source that is still without a reading reloads no differently
        before it expires, so nothing reloads the store when it does. Call this
        once :attr:`hold_expires_at` has passed.
        """
        expires_at = self.hold_expires_at
        if expires_at is None or time.monotonic() < expires_at:
            return False
        return self._mark_unavailable(tuple(eid for eid in self._source_entity_ids if eid in self._missing_since))

    def _resolve_from_constant(self) -> bool:
        """Resolve the stored constant, mark the store ready, and return whether consumers should be told."""
        changed = self._resolve_value_from_constant()
        self._data_ready.set()
        self._settled.set()
        return changed

    def _resolve_value_from_constant(self) -> bool:
        """Resolve the stored constant into the optimization value and return whether consumers should be told."""
        if self._constant is None:
            changed = self._mark_unavailable(())
            self._value = None
            self._loaded_timestamps = ()
            return changed
        forecast_timestamps = self._get_forecast_timestamps()
        return self._commit(
            resolve_constant(self._constant, self._hint, list(forecast_timestamps)), forecast_timestamps
        )

    def _commit(self, value: InputValue, forecast_timestamps: tuple[float, ...]) -> bool:
        """Store a resolved value and return whether consumers should be told."""
        loaded_timestamps = forecast_timestamps if self._hint.time_series else ()
        changed = (
            not self._available
            or self._error is not None
            or loaded_timestamps != self._loaded_timestamps
            or not _same_value(self._value, value)
        )
        self._value = value
        self._available = True
        self._error = None
        self._logged_failure = None
        self._unavailable_sources = ()
        self._loaded_timestamps = loaded_timestamps
        return changed

    def _mark_unavailable(self, unavailable_sources: tuple[str, ...]) -> bool:
        """Mark the store unavailable, keeping its value, and return whether consumers should be told."""
        changed = self._available or self._error is not None or unavailable_sources != self._unavailable_sources
        self._available = False
        self._error = None
        self._unavailable_sources = unavailable_sources
        self._held_sources = {}
        return changed


class _HeldStateMachine(StateMachine):
    """State machine decorator that reads held sources from their last reading."""

    def __init__(self, base: StateMachine, held: Mapping[str, EntityState]) -> None:
        """Initialize with a base state machine and the last reading of each held source."""
        self._base = base
        self._held = held

    @property
    def time_zone(self) -> tzinfo:
        """Return the base state machine's time zone."""
        return self._base.time_zone

    def get(self, entity_id: str) -> EntityState | None:
        """Return the held reading of a held source, or the entity's state."""
        return self._held.get(entity_id) or self._base.get(entity_id)


def _same_value(previous: InputValue | None, resolved: InputValue) -> bool:
    """Return whether a newly resolved value equals the previous one, including its type."""
    return (
        previous is not None
        and type(previous) is type(resolved)
        and bool(np.array_equal(previous, resolved, equal_nan=True))
    )


def _same_error(previous: InputError | None, error: InputError) -> bool:
    """Return whether a rejection reports the same problem as the previous one."""
    return (
        previous is not None
        and previous.translation_key == error.translation_key
        and previous.translation_placeholders == error.translation_placeholders
    )


def create_input_store(
    *,
    value: object,
    storage: Storage,
    hint: FieldHint,
    get_forecast_timestamps: Callable[[], tuple[float, ...]],
    negate: bool = False,
    hold_seconds: float = 0.0,
) -> InputStore:
    """Create an InputStore from the value it resolves from, its storage binding, and field hint.

    The value is the input's schema value, as ``input_value`` returns it, and
    determines mode and initial state:
    - {"type": "entity", "value": [...]} → DRIVEN mode
    - {"type": "constant", "value": X} → EDITABLE mode with that value
    - bare bool/int/float → EDITABLE mode with that value
    - {"type": "none"} or None → EDITABLE mode with no value

    When ``negate`` is True, values resolved from source entities are negated.
    Constant values are already stored negated, so the flag only changes the
    driven path. ``hold_seconds`` is how long a driven store holds a source's
    last reading once the source has no reading.
    """
    mode = InputMode.EDITABLE
    sources: EntityValue | None = None
    initial_value: float | bool | None = None
    match value:
        case {"type": "entity"} if is_entity_value(value):
            mode = InputMode.DRIVEN
            sources = value
        case {"type": "constant", "value": bool() as constant} | (bool() as constant):
            initial_value = constant
        case {"type": "constant", "value": Real() as constant} | (Real() as constant):
            initial_value = float(constant)
        case {"type": "none"} | None:
            pass
        case _:
            msg = f"Invalid config value: {value}"
            raise RuntimeError(msg)

    return InputStore(
        mode=mode,
        sources=sources,
        hint=hint,
        get_forecast_timestamps=get_forecast_timestamps,
        storage=storage,
        initial_value=initial_value,
        negate=negate,
        hold_seconds=hold_seconds,
    )


__all__ = ["InputMode", "InputStore", "InputValue", "create_input_store"]
