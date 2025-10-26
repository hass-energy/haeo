"""Loader type alias for field type-specific data loading.

Loader instances are accessed through FieldMeta.loader, providing full type safety.
Individual loaders are defined in their respective modules (constant_loader.py, sensor_loader.py, etc.)
and should not be imported directly - use the type system instead.
"""

from collections.abc import Sequence
from typing import Any

from .constant_loader import ConstantLoader as ConstantLoader
from .forecast_and_sensor_loader import ForecastAndSensorLoader as ForecastAndSensorLoader
from .forecast_and_sensor_loader import ForecastAndSensorValue as ForecastAndSensorValue
from .forecast_loader import ForecastLoader as ForecastLoader
from .sensor_loader import SensorLoader as SensorLoader

# Type aliases for loader value parameters
type ForecastValue = Sequence[str]
type SensorValue = Sequence[str]

# Union of all concrete loader types
Loader = ConstantLoader[Any] | SensorLoader | ForecastLoader | ForecastAndSensorLoader
