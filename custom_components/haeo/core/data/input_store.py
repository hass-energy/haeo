"""Input data store for HAEO configuration fields.

Manages data loading, caching, and readiness for input fields. Fully
decoupled from Home Assistant — depends only on the StateMachine protocol
and core loaders. Can be driven by any system that provides a StateMachine.
"""

import asyncio
from collections.abc import Callable
from enum import Enum
import logging
from typing import Any

from custom_components.haeo.core.data.loader import ScalarLoader, TimeSeriesLoader
from custom_components.haeo.core.schema import as_entity_value
from custom_components.haeo.core.state import EntityState, StateMachine

_LOGGER = logging.getLogger(__name__)


class InputMode(Enum):
    """Operating mode for an input store."""

    EDITABLE = "editable"
    DRIVEN = "driven"


class InputStore:
    """Holds data for a single input field.

    Pure data container with no Home Assistant dependencies. Loading is
    triggered externally by passing a StateMachine instance.

    Parameters
    ----------
        mode: Whether this store is user-editable or driven by entities
        source_entity_ids: Entity IDs that drive this store (empty for editable)
        time_series: Whether this field produces time-series forecasts
        boundaries: Whether time-series values are at boundaries (n+1) vs intervals (n)
        get_forecast_timestamps: Callable returning current forecast timestamps
        is_percentage: Whether values should be divided by 100 when accessed via get_values()
        initial_value: Initial constant value for editable mode

    """

    def __init__(
        self,
        *,
        mode: InputMode,
        source_entity_ids: list[str],
        time_series: bool = False,
        boundaries: bool = False,
        get_forecast_timestamps: Callable[[], tuple[float, ...]],
        is_percentage: bool = False,
        initial_value: float | None = None,
    ) -> None:
        """Initialize the input store."""
        self._mode = mode
        self._source_entity_ids = source_entity_ids
        self._time_series = time_series
        self._boundaries = boundaries
        self._get_forecast_timestamps = get_forecast_timestamps
        self._is_percentage = is_percentage

        self._native_value: float | None = initial_value
        self._values: tuple[float, ...] | None = None
        self._captured_source_states: dict[str, EntityState] = {}
        self._data_ready = asyncio.Event()

        # Loaders
        self._time_series_loader = TimeSeriesLoader()
        self._scalar_loader = ScalarLoader()

        # If editable with an initial value, compute values (but don't mark ready
        # until explicitly signaled — the HA layer controls readiness timing)
        if mode == InputMode.EDITABLE and initial_value is not None:
            self._rebuild_editable_values(mark_ready=False)

    @property
    def mode(self) -> InputMode:
        """Return the operating mode."""
        return self._mode

    @property
    def source_entity_ids(self) -> list[str]:
        """Return source entity IDs for driven mode."""
        return self._source_entity_ids

    @property
    def time_series(self) -> bool:
        """Return whether this store produces time-series data."""
        return self._time_series

    @property
    def native_value(self) -> float | None:
        """Return the current scalar value (without percentage conversion)."""
        return self._native_value

    @property
    def values(self) -> tuple[float, ...] | None:
        """Return loaded values with percentage conversion applied.

        For time-series: tuple of forecast values.
        For scalar: single-element tuple.
        Returns None if not loaded.
        """
        return self._values

    @property
    def forecast_timestamps(self) -> tuple[float, ...]:
        """Return the current forecast timestamps."""
        return self._get_forecast_timestamps()

    @property
    def captured_source_states(self) -> dict[str, EntityState]:
        """Source states captured from the last data load."""
        return self._captured_source_states

    def capture_state(self, entity_id: str, state: EntityState) -> None:
        """Capture a single source entity state (e.g., from a state change event)."""
        self._captured_source_states = {entity_id: state}

    def is_ready(self) -> bool:
        """Return True if data has been loaded and store is ready."""
        return self._data_ready.is_set()

    async def wait_ready(self) -> None:
        """Wait for data to be ready."""
        await self._data_ready.wait()

    def mark_ready(self) -> None:
        """Explicitly mark the store as ready."""
        self._data_ready.set()

    def get_values(self) -> tuple[float, ...] | None:
        """Return values (alias for the values property)."""
        return self._values

    def set_value(self, value: float) -> None:
        """Set a new constant value (editable mode).

        Updates the native value and regenerates computed values.
        """
        self._native_value = value
        self._rebuild_editable_values(mark_ready=True)

    def refresh(self) -> None:
        """Refresh computed values for editable mode (e.g., after horizon change).

        Also marks the store as ready.
        """
        if self._mode == InputMode.EDITABLE:
            self._rebuild_editable_values(mark_ready=True)

    async def async_load(self, sm: StateMachine) -> bool:
        """Load data from source entities via the provided state machine.

        Returns True if data was successfully loaded, False otherwise.
        Does not modify state on failure (keeps previous values).
        """
        # Capture source states
        self._captured_source_states = {
            eid: state for eid in self._source_entity_ids if (state := sm.get(eid)) is not None
        }

        if not self._time_series:
            if not self._source_entity_ids:
                return False
            try:
                scalar_value = await self._scalar_loader.load(
                    sm=sm,
                    value=as_entity_value(self._source_entity_ids),
                )
            except Exception:
                _LOGGER.debug(
                    "Scalar load failed from sources %s; keeping previous value",
                    self._source_entity_ids,
                    exc_info=True,
                )
                return False

            self._native_value = scalar_value
            self._apply_values((scalar_value,))
            return True

        forecast_timestamps = self._get_forecast_timestamps()

        try:
            if self._boundaries:
                raw_values = await self._time_series_loader.load_boundaries(
                    sm=sm,
                    value=as_entity_value(self._source_entity_ids),
                    forecast_times=list(forecast_timestamps),
                )
            else:
                raw_values = await self._time_series_loader.load_intervals(
                    sm=sm,
                    value=as_entity_value(self._source_entity_ids),
                    forecast_times=list(forecast_timestamps),
                )
        except Exception:
            _LOGGER.debug(
                "Time-series load failed from sources %s; keeping previous values",
                self._source_entity_ids,
                exc_info=True,
            )
            return False

        if not raw_values:
            _LOGGER.debug(
                "Time-series load returned no values from sources %s; keeping previous values",
                self._source_entity_ids,
            )
            return False

        self._native_value = raw_values[0]
        self._apply_values(tuple(raw_values))
        return True

    def _apply_values(self, raw: tuple[float, ...]) -> None:
        """Apply raw values with percentage conversion and mark ready."""
        if self._is_percentage:
            self._values = tuple(v / 100.0 for v in raw)
        else:
            self._values = raw
        self._data_ready.set()

    def _rebuild_editable_values(self, *, mark_ready: bool = True) -> None:
        """Regenerate values for editable mode from the current constant value."""
        if self._native_value is None:
            self._values = None
            if mark_ready:
                self._data_ready.set()
            return

        if self._time_series:
            forecast_timestamps = self._get_forecast_timestamps()
            # For boundaries: n+1 values, for intervals: n values
            count = len(forecast_timestamps) if self._boundaries else max(0, len(forecast_timestamps) - 1)
            raw = tuple(self._native_value for _ in range(count))
        else:
            raw = (self._native_value,)

        if mark_ready:
            self._apply_values(raw)
        elif self._is_percentage:
            self._values = tuple(v / 100.0 for v in raw)
        else:
            self._values = raw


def create_input_store(
    *,
    config_value: Any,
    time_series: bool = False,
    boundaries: bool = False,
    get_forecast_timestamps: Callable[[], tuple[float, ...]],
    is_percentage: bool = False,
) -> InputStore:
    """Create an InputStore from a config schema value.

    Interprets the config value to determine mode and initial state:
    - {"type": "entity", "value": [...]} → DRIVEN mode
    - {"type": "constant", "value": X} → EDITABLE mode
    - {"type": "none"} or None → EDITABLE mode with no value
    """
    match config_value:
        case {"type": "entity", "value": entity_ids} if isinstance(entity_ids, list):
            return InputStore(
                mode=InputMode.DRIVEN,
                source_entity_ids=entity_ids,
                time_series=time_series,
                boundaries=boundaries,
                get_forecast_timestamps=get_forecast_timestamps,
                is_percentage=is_percentage,
            )
        case {"type": "constant", "value": constant}:
            return InputStore(
                mode=InputMode.EDITABLE,
                source_entity_ids=[],
                time_series=time_series,
                boundaries=boundaries,
                get_forecast_timestamps=get_forecast_timestamps,
                is_percentage=is_percentage,
                initial_value=float(constant),
            )
        case {"type": "none"} | None:
            return InputStore(
                mode=InputMode.EDITABLE,
                source_entity_ids=[],
                time_series=time_series,
                boundaries=boundaries,
                get_forecast_timestamps=get_forecast_timestamps,
                is_percentage=is_percentage,
            )
        case bool() | int() | float() as constant:
            return InputStore(
                mode=InputMode.EDITABLE,
                source_entity_ids=[],
                time_series=time_series,
                boundaries=boundaries,
                get_forecast_timestamps=get_forecast_timestamps,
                is_percentage=is_percentage,
                initial_value=float(constant),
            )
        case _:
            msg = f"Invalid config value: {config_value}"
            raise RuntimeError(msg)


__all__ = ["InputMode", "InputStore", "create_input_store"]
