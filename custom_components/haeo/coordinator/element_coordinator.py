"""Per-subentry coordinator for managing element input values.

Each element (battery, grid, solar, etc.) gets its own ElementInputCoordinator
that tracks source entity state changes and loads input values.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.util.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ElementInputData:
    """Data for a single element's inputs.

    Attributes:
        field_values: Mapping from field name to loaded values.
            - Time series fields: list[float] with one value per forecast period
            - Scalar fields: float or bool
        forecast_timestamps: Tuple of timestamps for forecast values.

    """

    field_values: dict[str, list[float] | float | bool]
    forecast_timestamps: tuple[float, ...]


def _extract_entity_ids(value: Any) -> list[str]:
    """Extract entity IDs from a config value.

    Entity IDs are identified by containing a '.' (e.g., 'sensor.temperature').
    Handles single values, lists, and nested mappings.
    """
    if isinstance(value, str) and "." in value:
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and "." in v]
    if isinstance(value, dict):
        result: list[str] = []
        for v in value.values():
            result.extend(_extract_entity_ids(v))
        return result
    return []


# Fields that are not inputs (metadata or connection references)
_NON_INPUT_FIELDS = frozenset({"element_type", "name", "connection", "source", "target"})


class ElementInputCoordinator(DataUpdateCoordinator[ElementInputData]):
    """Per-subentry coordinator managing input entity values.

    This coordinator:
    1. Tracks source entity state changes for driven fields
    2. Loads and interpolates forecast data from source entities
    3. Provides current values to input entities
    4. Notifies network coordinator when inputs change
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
        on_input_change: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the element input coordinator.

        Args:
            hass: Home Assistant instance
            config_entry: Parent config entry (the hub)
            subentry: Config subentry for this element
            on_input_change: Optional callback when inputs change

        """
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.entry_id}_{subentry.subentry_id}",
            update_interval=None,  # Event-driven only, no polling
        )

        self._config_entry = config_entry
        self._subentry = subentry
        self._on_input_change = on_input_change

        # Collect source entity IDs from config
        self._source_entity_ids: set[str] = set()
        self._field_sources: dict[str, list[str]] = {}

        for field_name, value in subentry.data.items():
            if field_name in _NON_INPUT_FIELDS:
                continue
            entity_ids = _extract_entity_ids(value)
            if entity_ids:
                self._field_sources[field_name] = entity_ids
                self._source_entity_ids.update(entity_ids)

        self._state_change_unsub: Callable[[], None] | None = None
        self._loader = TimeSeriesLoader()

    @property
    def subentry(self) -> ConfigSubentry:
        """Return the config subentry."""
        return self._subentry

    @property
    def on_input_change(self) -> Callable[[], None] | None:
        """Return the input change callback."""
        return self._on_input_change

    @on_input_change.setter
    def on_input_change(self, callback: Callable[[], None] | None) -> None:
        """Set the input change callback."""
        self._on_input_change = callback

    async def async_setup(self) -> None:
        """Set up state change tracking."""
        if self._source_entity_ids:
            self._state_change_unsub = async_track_state_change_event(
                self.hass,
                list(self._source_entity_ids),
                self._handle_state_change,
            )

    async def async_shutdown(self) -> None:
        """Clean up state change tracking."""
        if self._state_change_unsub:
            self._state_change_unsub()
            self._state_change_unsub = None

    @callback
    def _handle_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle source entity state change."""
        self.hass.async_create_task(self.async_request_refresh())

    async def _async_update_data(self) -> ElementInputData:
        """Load current values from source entities."""
        # Get forecast times from hub config
        periods_seconds = tiers_to_periods_seconds(self._config_entry.data)
        forecast_timestamps = generate_forecast_timestamps(periods_seconds)

        # Load values for each field
        field_values: dict[str, list[float] | float | bool] = {}

        for field_name, value in self._subentry.data.items():
            if field_name in _NON_INPUT_FIELDS:
                continue

            if field_name in self._field_sources:
                # Load from source entities (time series)
                loaded = await self._load_field_values(
                    field_name,
                    self._field_sources[field_name],
                    forecast_timestamps,
                )
                if loaded is not None:
                    field_values[field_name] = loaded
            # Static value from config
            elif isinstance(value, bool):
                field_values[field_name] = value
            elif isinstance(value, (int, float)):
                field_values[field_name] = float(value)

        # Notify network coordinator if callback provided
        if self._on_input_change is not None:
            self._on_input_change()

        return ElementInputData(
            field_values=field_values,
            forecast_timestamps=forecast_timestamps,
        )

    async def _load_field_values(
        self,
        field_name: str,
        entity_ids: list[str],
        forecast_timestamps: Sequence[float],
    ) -> list[float] | None:
        """Load values from source entities with interpolation."""
        try:
            return await self._loader.load(
                hass=self.hass,
                value=entity_ids,
                forecast_times=list(forecast_timestamps),
            )
        except Exception:
            _LOGGER.exception("Failed to load field %s from %s", field_name, entity_ids)
            return None

    def get_field_value(self, field_name: str) -> list[float] | float | bool | None:
        """Get current value for a field.

        Used by input entities to get their current value from the coordinator.
        """
        return self.data.field_values.get(field_name)


__all__ = ["ElementInputCoordinator", "ElementInputData"]
