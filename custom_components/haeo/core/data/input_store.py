"""Input data store for HAEO configuration fields.

Holds the live value for a single input field and feeds it to the optimization.
Fully decoupled from Home Assistant: it depends only on the StateMachine
protocol, the shared field resolver, and a Storage binding for persistence.

An ``InputStore`` is the single source of truth for one field's value:

- It is built from configuration (via :func:`create_input_store`) and bound to
  a ``Storage`` that backs it to persistent config.
- DRIVEN stores resolve from source entities through ``async_load``.
- EDITABLE stores hold a constant that is persisted through the storage on
  ``set_value``.
- Consumers (the coordinator) read the resolved ``value`` and subscribe to
  changes via ``add_listener``.
"""

import asyncio
from collections.abc import Callable
from enum import Enum
import logging
from typing import Any

import numpy as np

from custom_components.haeo.core.data.loader.config_loader import is_percent_field, resolve_constant, resolve_field
from custom_components.haeo.core.data.storage import Storage
from custom_components.haeo.core.schema import as_entity_value
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.core.state import EntityState, StateMachine

_LOGGER = logging.getLogger(__name__)


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
        source_entity_ids: Entity IDs that drive this store (empty for editable).
        hint: Field hint describing output type, time-series shape, etc.
        get_forecast_timestamps: Callable returning current forecast timestamps.
        storage: Persistence binding backing this store.
        initial_value: Initial constant value (display units) for editable mode.
        negate: When True, values resolved from source entities are negated.

    """

    def __init__(
        self,
        *,
        mode: InputMode,
        source_entity_ids: list[str],
        hint: FieldHint,
        get_forecast_timestamps: Callable[[], tuple[float, ...]],
        storage: Storage,
        initial_value: float | bool | None = None,
        negate: bool = False,
    ) -> None:
        """Initialize the input store."""
        self._mode = mode
        self._source_entity_ids = source_entity_ids
        self._hint = hint
        self._get_forecast_timestamps = get_forecast_timestamps
        self._storage = storage

        # When True, values resolved from source entities are negated so the
        # optimization sees the running cost's negative. Constant (editable)
        # values are negated at the storage layer instead, so this only affects
        # the driven path; see ``async_load``.
        self._negate = negate

        self._constant: float | bool | None = initial_value
        self._value: bool | float | np.ndarray | None = None
        self._available = False
        self._loaded_timestamps: tuple[float, ...] = ()
        self._captured_source_states: dict[str, EntityState] = {}
        self._data_ready = asyncio.Event()
        self._listeners: list[Callable[[], None]] = []

        if mode == InputMode.EDITABLE and initial_value is not None:
            self._resolve_from_constant(mark_ready=False)

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
    def value(self) -> bool | float | np.ndarray | None:
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

    def capture_state(self, entity_id: str, state: EntityState) -> None:
        """Capture a single source entity state (e.g., from a state change event)."""
        self._captured_source_states = {entity_id: state}

    # --- Readiness ---

    def is_ready(self) -> bool:
        """Return True if data has been loaded and store is ready."""
        return self._data_ready.is_set()

    async def wait_ready(self) -> None:
        """Wait for data to be ready."""
        await self._data_ready.wait()

    def mark_ready(self) -> None:
        """Explicitly mark the store as ready."""
        self._data_ready.set()

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

    def _notify(self) -> None:
        """Fire all registered change listeners."""
        for listener in list(self._listeners):
            listener()

    # --- Mutation ---

    def set_value(self, value: float | bool) -> None:  # noqa: FBT001 (bool is a valid input value)
        """Set a new constant value (display units) and re-resolve.

        Updates the resolved value, marks ready, and notifies listeners.
        Persistence is performed separately via :meth:`persist`.
        """
        self._constant = value
        self._resolve_from_constant(mark_ready=True)

    async def persist(self, schema_value: Any) -> None:
        """Persist a schema value through the bound storage."""
        await self._storage.write(schema_value)

    def refresh(self) -> None:
        """Re-resolve editable values (e.g., after a horizon change) and mark ready."""
        if self._mode == InputMode.EDITABLE:
            self._resolve_from_constant(mark_ready=True)

    async def async_load(self, sm: StateMachine) -> bool:
        """Resolve data from source entities via the provided state machine.

        Returns True if data was successfully loaded, False otherwise. Does not
        modify state on failure (keeps previous values).
        """
        self._captured_source_states = {
            eid: state for eid in self._source_entity_ids if (state := sm.get(eid)) is not None
        }

        if not self._source_entity_ids:
            self._available = False
            return False

        forecast_timestamps = self._get_forecast_timestamps()
        try:
            resolved = resolve_field(
                as_entity_value(self._source_entity_ids),
                self._hint,
                sm,
                list(forecast_timestamps),
            )
        except Exception:
            _LOGGER.debug(
                "Load failed from sources %s; keeping previous value",
                self._source_entity_ids,
                exc_info=True,
            )
            self._available = False
            return False

        if resolved is None or not isinstance(resolved, (bool, float, int, np.ndarray)):
            _LOGGER.debug(
                "Load returned no value from sources %s; keeping previous value",
                self._source_entity_ids,
            )
            self._available = False
            return False

        if isinstance(resolved, np.ndarray) and resolved.size == 0:
            self._available = False
            return False

        if self._negate and not isinstance(resolved, bool):
            resolved = -resolved

        self._value = resolved
        self._available = True
        self._loaded_timestamps = forecast_timestamps if self._hint.time_series else ()
        self._data_ready.set()
        self._notify()
        return True

    def _resolve_from_constant(self, *, mark_ready: bool) -> None:
        """Resolve the stored constant into the optimization value."""
        if self._constant is None:
            self._value = None
            self._available = False
            self._loaded_timestamps = ()
        else:
            forecast_timestamps = self._get_forecast_timestamps()
            self._value = resolve_constant(self._constant, self._hint, list(forecast_timestamps))
            self._available = True
            self._loaded_timestamps = forecast_timestamps if self._hint.time_series else ()

        if mark_ready:
            self._data_ready.set()
            self._notify()


def create_input_store(
    *,
    storage: Storage,
    hint: FieldHint,
    get_forecast_timestamps: Callable[[], tuple[float, ...]],
    negate: bool = False,
) -> InputStore:
    """Create an InputStore from its storage binding and field hint.

    Reads the persisted schema value to determine mode and initial state:
    - {"type": "entity", "value": [...]} → DRIVEN mode
    - {"type": "constant", "value": X} → EDITABLE mode with that value
    - bare bool/int/float → EDITABLE mode with that value
    - {"type": "none"} or None → EDITABLE mode with no value

    When ``negate`` is True, values resolved from source entities are negated.
    Constant values are already stored negated, so the flag only changes the
    driven path.
    """
    config_value = storage.read()
    match config_value:
        case {"type": "entity", "value": entity_ids} if isinstance(entity_ids, (list, tuple)):
            return InputStore(
                mode=InputMode.DRIVEN,
                source_entity_ids=list(entity_ids),
                hint=hint,
                get_forecast_timestamps=get_forecast_timestamps,
                storage=storage,
                negate=negate,
            )
        case {"type": "constant", "value": constant}:
            return InputStore(
                mode=InputMode.EDITABLE,
                source_entity_ids=[],
                hint=hint,
                get_forecast_timestamps=get_forecast_timestamps,
                storage=storage,
                initial_value=constant if isinstance(constant, bool) else float(constant),
                negate=negate,
            )
        case {"type": "none"} | None:
            return InputStore(
                mode=InputMode.EDITABLE,
                source_entity_ids=[],
                hint=hint,
                get_forecast_timestamps=get_forecast_timestamps,
                storage=storage,
                negate=negate,
            )
        case bool() as constant:
            return InputStore(
                mode=InputMode.EDITABLE,
                source_entity_ids=[],
                hint=hint,
                get_forecast_timestamps=get_forecast_timestamps,
                storage=storage,
                initial_value=constant,
                negate=negate,
            )
        case int() | float() as constant:
            return InputStore(
                mode=InputMode.EDITABLE,
                source_entity_ids=[],
                hint=hint,
                get_forecast_timestamps=get_forecast_timestamps,
                storage=storage,
                initial_value=float(constant),
                negate=negate,
            )
        case _:
            msg = f"Invalid config value: {config_value}"
            raise RuntimeError(msg)


__all__ = ["InputMode", "InputStore", "create_input_store"]
