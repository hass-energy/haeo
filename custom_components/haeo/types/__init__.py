"""HAEO type system with field-based metadata."""

from __future__ import annotations

from .battery import BatteryConfig
from .connection import ConnectionConfig
from .constant_load import ConstantLoadConfig
from .forecast_load import ForecastLoadConfig
from .generator import GeneratorConfig
from .grid import GridConfig
from .net import NetConfig

# Type-safe discriminated union for element configurations
ElementConfig = (
    BatteryConfig
    | GridConfig
    | ConstantLoadConfig
    | ForecastLoadConfig
    | GeneratorConfig
    | NetConfig
    | ConnectionConfig
)

# List of all element types for iteration
ELEMENT_TYPES: dict[str, type[ElementConfig]] = {
    "battery": BatteryConfig,
    "connection": ConnectionConfig,
    "generator": GeneratorConfig,
    "grid": GridConfig,
    "constant_load": ConstantLoadConfig,
    "forecast_load": ForecastLoadConfig,
    "net": NetConfig,
}
