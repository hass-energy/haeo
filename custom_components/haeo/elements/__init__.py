"""HAEO element registry with field-based metadata."""

from collections.abc import Callable, Sequence
from typing import Any, Literal, NamedTuple, Required, TypedDict

from homeassistant.config_entries import ConfigEntry

from .battery import BATTERY_CONFIG_DEFAULTS, BatteryConfigData, BatteryConfigSchema
from .battery import ELEMENT_TYPE as ELEMENT_TYPE_BATTERY
from .battery import model_description as battery_model_description
from .connection import CONNECTION_CONFIG_DEFAULTS, ConnectionConfigData, ConnectionConfigSchema
from .connection import ELEMENT_TYPE as ELEMENT_TYPE_CONNECTION
from .connection import model_description as connection_model_description
from .constant_load import CONSTANT_LOAD_CONFIG_DEFAULTS, ConstantLoadConfigData, ConstantLoadConfigSchema
from .constant_load import ELEMENT_TYPE as ELEMENT_TYPE_CONSTANT_LOAD
from .constant_load import model_description as constant_load_model_description
from .forecast_load import ELEMENT_TYPE as ELEMENT_TYPE_FORECAST_LOAD
from .forecast_load import FORECAST_LOAD_CONFIG_DEFAULTS, ForecastLoadConfigData, ForecastLoadConfigSchema
from .forecast_load import model_description as forecast_load_model_description
from .grid import ELEMENT_TYPE as ELEMENT_TYPE_GRID
from .grid import GRID_CONFIG_DEFAULTS, GridConfigData, GridConfigSchema
from .grid import model_description as grid_model_description
from .node import ELEMENT_TYPE as ELEMENT_TYPE_NODE
from .node import NODE_CONFIG_DEFAULTS, NodeConfigData, NodeConfigSchema
from .node import model_description as node_model_description
from .photovoltaics import ELEMENT_TYPE as ELEMENT_TYPE_PHOTOVOLTAICS
from .photovoltaics import PHOTOVOLTAICS_CONFIG_DEFAULTS, PhotovoltaicsConfigData, PhotovoltaicsConfigSchema
from .photovoltaics import model_description as photovoltaics_model_description

type ElementType = Literal[
    "battery",
    "connection",
    "photovoltaics",
    "grid",
    "constant_load",
    "forecast_load",
    "node",
]


class SubentryDataDict(TypedDict, total=False):
    """Typed dictionary for subentry data with required name field."""

    name_value: Required[str]
    type: str


def assert_config_entry_exists(entry: ConfigEntry | None, entry_id: str) -> ConfigEntry:
    """Assert that a config entry exists and return it."""

    if entry is None:
        msg = f"Config entry {entry_id} must exist"
        raise RuntimeError(msg)
    return entry


def assert_subentry_has_name(name: str | None, subentry_id: str) -> str:
    """Assert that a subentry has a name_value field."""

    if name is None:
        msg = f"Subentry {subentry_id} must have name_value"
        raise RuntimeError(msg)
    return name


ElementConfigSchema = (
    BatteryConfigSchema
    | GridConfigSchema
    | ConstantLoadConfigSchema
    | ForecastLoadConfigSchema
    | PhotovoltaicsConfigSchema
    | NodeConfigSchema
    | ConnectionConfigSchema
)

ElementConfigData = (
    BatteryConfigData
    | GridConfigData
    | ConstantLoadConfigData
    | ForecastLoadConfigData
    | PhotovoltaicsConfigData
    | NodeConfigData
    | ConnectionConfigData
)


class ElementRegistryEntry(NamedTuple):
    """Registry entry for an element type."""

    schema: type[Any]
    data: type[Any]
    defaults: dict[str, Any]
    translation_key: ElementType
    describe: Callable[[Any], str]


ELEMENT_TYPES: dict[ElementType, ElementRegistryEntry] = {
    ELEMENT_TYPE_BATTERY: ElementRegistryEntry(
        schema=BatteryConfigSchema,
        data=BatteryConfigData,
        defaults=BATTERY_CONFIG_DEFAULTS,
        translation_key=ELEMENT_TYPE_BATTERY,
        describe=battery_model_description,
    ),
    ELEMENT_TYPE_CONNECTION: ElementRegistryEntry(
        schema=ConnectionConfigSchema,
        data=ConnectionConfigData,
        defaults=CONNECTION_CONFIG_DEFAULTS,
        translation_key=ELEMENT_TYPE_CONNECTION,
        describe=connection_model_description,
    ),
    ELEMENT_TYPE_PHOTOVOLTAICS: ElementRegistryEntry(
        schema=PhotovoltaicsConfigSchema,
        data=PhotovoltaicsConfigData,
        defaults=PHOTOVOLTAICS_CONFIG_DEFAULTS,
        translation_key=ELEMENT_TYPE_PHOTOVOLTAICS,
        describe=photovoltaics_model_description,
    ),
    ELEMENT_TYPE_GRID: ElementRegistryEntry(
        schema=GridConfigSchema,
        data=GridConfigData,
        defaults=GRID_CONFIG_DEFAULTS,
        translation_key=ELEMENT_TYPE_GRID,
        describe=grid_model_description,
    ),
    ELEMENT_TYPE_CONSTANT_LOAD: ElementRegistryEntry(
        schema=ConstantLoadConfigSchema,
        data=ConstantLoadConfigData,
        defaults=CONSTANT_LOAD_CONFIG_DEFAULTS,
        translation_key=ELEMENT_TYPE_CONSTANT_LOAD,
        describe=constant_load_model_description,
    ),
    ELEMENT_TYPE_FORECAST_LOAD: ElementRegistryEntry(
        schema=ForecastLoadConfigSchema,
        data=ForecastLoadConfigData,
        defaults=FORECAST_LOAD_CONFIG_DEFAULTS,
        translation_key=ELEMENT_TYPE_FORECAST_LOAD,
        describe=forecast_load_model_description,
    ),
    ELEMENT_TYPE_NODE: ElementRegistryEntry(
        schema=NodeConfigSchema,
        data=NodeConfigData,
        defaults=NODE_CONFIG_DEFAULTS,
        translation_key=ELEMENT_TYPE_NODE,
        describe=node_model_description,
    ),
}


SUPPORTED_ELEMENT_TYPES: tuple[ElementType, ...] = tuple(ELEMENT_TYPES)


def get_model_description(config: ElementConfigData) -> str:
    """Get model description for an element configuration."""

    entry = ELEMENT_TYPES.get(config["element_type"])
    if entry is None:
        msg = f"Unknown element type: {config['element_type']}"
        raise ValueError(msg)
    return entry.describe(config)


SensorValue = str | Sequence[str]
ForecastTimes = Sequence[int]


__all__ = [
    "ELEMENT_TYPES",
    "ELEMENT_TYPE_BATTERY",
    "ELEMENT_TYPE_CONNECTION",
    "ELEMENT_TYPE_CONSTANT_LOAD",
    "ELEMENT_TYPE_FORECAST_LOAD",
    "ELEMENT_TYPE_GRID",
    "ELEMENT_TYPE_NODE",
    "ELEMENT_TYPE_PHOTOVOLTAICS",
    "SUPPORTED_ELEMENT_TYPES",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementRegistryEntry",
    "ElementType",
    "ForecastTimes",
    "SensorValue",
    "SubentryDataDict",
    "assert_config_entry_exists",
    "assert_subentry_has_name",
    "get_model_description",
]
