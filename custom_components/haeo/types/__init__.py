"""HAEO type system with field-based metadata."""

from collections.abc import Sequence

from .battery import BatteryConfig as BatteryConfig
from .connection import ConnectionConfig as ConnectionConfig
from .constant_load import ConstantLoadConfig as ConstantLoadConfig
from .element_data import BatteryElementData as BatteryElementData
from .element_data import ConnectionElementData as ConnectionElementData
from .element_data import ConstantLoadElementData as ConstantLoadElementData
from .element_data import ElementData as ElementData
from .element_data import ForecastLoadElementData as ForecastLoadElementData
from .element_data import GeneratorElementData as GeneratorElementData
from .element_data import GridElementData as GridElementData
from .element_data import NetElementData as NetElementData
from .forecast_load import ForecastLoadConfig as ForecastLoadConfig
from .generator import GeneratorConfig as GeneratorConfig
from .grid import GridConfig as GridConfig
from .net import NetConfig as NetConfig

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

# Common type aliases used throughout the codebase
SensorValue = str | Sequence[str]
ForecastTimes = Sequence[int]
