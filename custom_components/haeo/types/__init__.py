"""HAEO type system with field-based metadata."""

from collections.abc import Sequence
from typing import Any

# Redundant aliases for explicit exports (import X as X pattern)
from .battery import BATTERY_CONFIG_DEFAULTS as BATTERY_CONFIG_DEFAULTS
from .battery import BatteryConfigData as BatteryConfigData
from .battery import BatteryConfigSchema as BatteryConfigSchema
from .connection import CONNECTION_CONFIG_DEFAULTS as CONNECTION_CONFIG_DEFAULTS
from .connection import ConnectionConfigData as ConnectionConfigData
from .connection import ConnectionConfigSchema as ConnectionConfigSchema
from .constant_load import CONSTANT_LOAD_CONFIG_DEFAULTS as CONSTANT_LOAD_CONFIG_DEFAULTS
from .constant_load import ConstantLoadConfigData as ConstantLoadConfigData
from .constant_load import ConstantLoadConfigSchema as ConstantLoadConfigSchema
from .forecast_load import FORECAST_LOAD_CONFIG_DEFAULTS as FORECAST_LOAD_CONFIG_DEFAULTS
from .forecast_load import ForecastLoadConfigData as ForecastLoadConfigData
from .forecast_load import ForecastLoadConfigSchema as ForecastLoadConfigSchema
from .generator import GENERATOR_CONFIG_DEFAULTS as GENERATOR_CONFIG_DEFAULTS
from .generator import GeneratorConfigData as GeneratorConfigData
from .generator import GeneratorConfigSchema as GeneratorConfigSchema
from .grid import GRID_CONFIG_DEFAULTS as GRID_CONFIG_DEFAULTS
from .grid import GridConfigData as GridConfigData
from .grid import GridConfigSchema as GridConfigSchema
from .net import NET_CONFIG_DEFAULTS as NET_CONFIG_DEFAULTS
from .net import NetConfigData as NetConfigData
from .net import NetConfigSchema as NetConfigSchema

# Type-safe discriminated union for element configurations (schema mode)
ElementConfigSchema = (
    BatteryConfigSchema
    | GridConfigSchema
    | ConstantLoadConfigSchema
    | ForecastLoadConfigSchema
    | GeneratorConfigSchema
    | NetConfigSchema
    | ConnectionConfigSchema
)

# Type-safe discriminated union for element configurations (data mode)
ElementConfigData = (
    BatteryConfigData
    | GridConfigData
    | ConstantLoadConfigData
    | ForecastLoadConfigData
    | GeneratorConfigData
    | NetConfigData
    | ConnectionConfigData
)

# Mapping of element type strings to (Schema type, Data type, defaults) tuples
ELEMENT_TYPES: dict[str, tuple[type[ElementConfigSchema], type[ElementConfigData], dict[str, Any]]] = {
    "battery": (BatteryConfigSchema, BatteryConfigData, BATTERY_CONFIG_DEFAULTS),
    "connection": (ConnectionConfigSchema, ConnectionConfigData, CONNECTION_CONFIG_DEFAULTS),
    "generator": (GeneratorConfigSchema, GeneratorConfigData, GENERATOR_CONFIG_DEFAULTS),
    "grid": (GridConfigSchema, GridConfigData, GRID_CONFIG_DEFAULTS),
    "constant_load": (ConstantLoadConfigSchema, ConstantLoadConfigData, CONSTANT_LOAD_CONFIG_DEFAULTS),
    "forecast_load": (ForecastLoadConfigSchema, ForecastLoadConfigData, FORECAST_LOAD_CONFIG_DEFAULTS),
    "net": (NetConfigSchema, NetConfigData, NET_CONFIG_DEFAULTS),
}

# Common type aliases used throughout the codebase (defined locally, implicitly exported)
SensorValue = str | Sequence[str]
ForecastTimes = Sequence[int]
