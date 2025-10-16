"""HAEO type system with field-based metadata."""

from collections.abc import Sequence
from typing import Any

# Redundant aliases for explicit exports (import X as X pattern)
from .battery import BATTERY_CONFIG_DEFAULTS as BATTERY_CONFIG_DEFAULTS
from .battery import BatteryConfigData as BatteryConfigData
from .battery import BatteryConfigSchema as BatteryConfigSchema
from .battery import model_description as battery_model_description
from .connection import CONNECTION_CONFIG_DEFAULTS as CONNECTION_CONFIG_DEFAULTS
from .connection import ConnectionConfigData as ConnectionConfigData
from .connection import ConnectionConfigSchema as ConnectionConfigSchema
from .connection import model_description as connection_model_description
from .constant_load import CONSTANT_LOAD_CONFIG_DEFAULTS as CONSTANT_LOAD_CONFIG_DEFAULTS
from .constant_load import ConstantLoadConfigData as ConstantLoadConfigData
from .constant_load import ConstantLoadConfigSchema as ConstantLoadConfigSchema
from .constant_load import model_description as constant_load_model_description
from .forecast_load import FORECAST_LOAD_CONFIG_DEFAULTS as FORECAST_LOAD_CONFIG_DEFAULTS
from .forecast_load import ForecastLoadConfigData as ForecastLoadConfigData
from .forecast_load import ForecastLoadConfigSchema as ForecastLoadConfigSchema
from .forecast_load import model_description as forecast_load_model_description
from .grid import GRID_CONFIG_DEFAULTS as GRID_CONFIG_DEFAULTS
from .grid import GridConfigData as GridConfigData
from .grid import GridConfigSchema as GridConfigSchema
from .grid import model_description as grid_model_description
from .node import NODE_CONFIG_DEFAULTS as NODE_CONFIG_DEFAULTS
from .node import NodeConfigData as NodeConfigData
from .node import NodeConfigSchema as NodeConfigSchema
from .node import model_description as node_model_description
from .photovoltaics import PHOTOVOLTAICS_CONFIG_DEFAULTS as PHOTOVOLTAICS_CONFIG_DEFAULTS
from .photovoltaics import PhotovoltaicsConfigData as PhotovoltaicsConfigData
from .photovoltaics import PhotovoltaicsConfigSchema as PhotovoltaicsConfigSchema
from .photovoltaics import model_description as photovoltaics_model_description

# Type-safe discriminated union for element configurations (schema mode)
ElementConfigSchema = (
    BatteryConfigSchema
    | GridConfigSchema
    | ConstantLoadConfigSchema
    | ForecastLoadConfigSchema
    | PhotovoltaicsConfigSchema
    | NodeConfigSchema
    | ConnectionConfigSchema
)

# Type-safe discriminated union for element configurations (data mode)
ElementConfigData = (
    BatteryConfigData
    | GridConfigData
    | ConstantLoadConfigData
    | ForecastLoadConfigData
    | PhotovoltaicsConfigData
    | NodeConfigData
    | ConnectionConfigData
)

# Mapping of element type strings to (Schema type, Data type, defaults) tuples
ELEMENT_TYPES: dict[str, tuple[type[ElementConfigSchema], type[ElementConfigData], dict[str, Any]]] = {
    "battery": (BatteryConfigSchema, BatteryConfigData, BATTERY_CONFIG_DEFAULTS),
    "connection": (ConnectionConfigSchema, ConnectionConfigData, CONNECTION_CONFIG_DEFAULTS),
    "photovoltaics": (PhotovoltaicsConfigSchema, PhotovoltaicsConfigData, PHOTOVOLTAICS_CONFIG_DEFAULTS),
    "grid": (GridConfigSchema, GridConfigData, GRID_CONFIG_DEFAULTS),
    "constant_load": (ConstantLoadConfigSchema, ConstantLoadConfigData, CONSTANT_LOAD_CONFIG_DEFAULTS),
    "forecast_load": (ForecastLoadConfigSchema, ForecastLoadConfigData, FORECAST_LOAD_CONFIG_DEFAULTS),
    "node": (NodeConfigSchema, NodeConfigData, NODE_CONFIG_DEFAULTS),
}


def get_model_description(config: ElementConfigData) -> str:  # noqa: PLR0911
    """Get model description for an element configuration.

    Uses discriminated union type narrowing to dispatch to the appropriate
    type-specific model description function.

    Args:
        config: The element configuration data

    Returns:
        A string describing the element model

    Raises:
        ValueError: If element_type is not recognized

    """
    if config["element_type"] == "battery":
        return battery_model_description(config)
    if config["element_type"] == "connection":
        return connection_model_description(config)
    if config["element_type"] == "photovoltaics":
        return photovoltaics_model_description(config)
    if config["element_type"] == "grid":
        return grid_model_description(config)
    if config["element_type"] == "constant_load":
        return constant_load_model_description(config)
    if config["element_type"] == "forecast_load":
        return forecast_load_model_description(config)
    if config["element_type"] == "node":
        return node_model_description(config)

    msg = f"Unknown element type: {config['element_type']}"
    raise ValueError(msg)


# Common type aliases used throughout the codebase (defined locally, implicitly exported)
SensorValue = str | Sequence[str]
ForecastTimes = Sequence[int]
