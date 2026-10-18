"""Loader for unified time series sensor and forecast data."""

from custom_components.haeo.core.schema import EntityValue
from custom_components.haeo.core.state import StateMachine

from .sensor_loader import load_sensors


class TimeSeriesLoader:
    """Loader that checks the sensors behind a time series input can supply data."""

    def available(self, *, sm: StateMachine, value: EntityValue, **_kwargs: object) -> bool:
        """Return True when every referenced sensor can supply data."""
        return load_sensors(sm, value["value"]) is not None
