"""HAEO element registry with field-based metadata."""

from collections.abc import Callable, Sequence
from typing import Any, Literal, NamedTuple, Required, TypedDict

from homeassistant.config_entries import ConfigEntry

from . import battery, connection, constant_load, forecast_load, grid, node, photovoltaics

type ElementType = Literal[
    "battery",
    "connection",
    "photovoltaics",
    "grid",
    "constant_load",
    "forecast_load",
    "node",
]


ELEMENT_TYPE_BATTERY = battery.ELEMENT_TYPE
ELEMENT_TYPE_CONNECTION = connection.ELEMENT_TYPE
ELEMENT_TYPE_PHOTOVOLTAICS = photovoltaics.ELEMENT_TYPE
ELEMENT_TYPE_GRID = grid.ELEMENT_TYPE
ELEMENT_TYPE_CONSTANT_LOAD = constant_load.ELEMENT_TYPE
ELEMENT_TYPE_FORECAST_LOAD = forecast_load.ELEMENT_TYPE
ELEMENT_TYPE_NODE = node.ELEMENT_TYPE


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
    battery.BatteryConfigSchema
    | grid.GridConfigSchema
    | constant_load.ConstantLoadConfigSchema
    | forecast_load.ForecastLoadConfigSchema
    | photovoltaics.PhotovoltaicsConfigSchema
    | node.NodeConfigSchema
    | connection.ConnectionConfigSchema
)

ElementConfigData = (
    battery.BatteryConfigData
    | grid.GridConfigData
    | constant_load.ConstantLoadConfigData
    | forecast_load.ForecastLoadConfigData
    | photovoltaics.PhotovoltaicsConfigData
    | node.NodeConfigData
    | connection.ConnectionConfigData
)


class ElementRegistryEntry(NamedTuple):
    """Registry entry for an element type."""

    schema: type[Any]
    data: type[Any]
    defaults: dict[str, Any]
    translation_key: ElementType
    describe: Callable[[Any], str]


ELEMENT_TYPES: dict[ElementType, ElementRegistryEntry] = {
    battery.ELEMENT_TYPE: ElementRegistryEntry(
        schema=battery.BatteryConfigSchema,
        data=battery.BatteryConfigData,
        defaults=battery.CONFIG_DEFAULTS,
        translation_key=battery.ELEMENT_TYPE,
        describe=battery.model_description,
    ),
    connection.ELEMENT_TYPE: ElementRegistryEntry(
        schema=connection.ConnectionConfigSchema,
        data=connection.ConnectionConfigData,
        defaults=connection.CONFIG_DEFAULTS,
        translation_key=connection.ELEMENT_TYPE,
        describe=connection.model_description,
    ),
    photovoltaics.ELEMENT_TYPE: ElementRegistryEntry(
        schema=photovoltaics.PhotovoltaicsConfigSchema,
        data=photovoltaics.PhotovoltaicsConfigData,
        defaults=photovoltaics.CONFIG_DEFAULTS,
        translation_key=photovoltaics.ELEMENT_TYPE,
        describe=photovoltaics.model_description,
    ),
    grid.ELEMENT_TYPE: ElementRegistryEntry(
        schema=grid.GridConfigSchema,
        data=grid.GridConfigData,
        defaults=grid.CONFIG_DEFAULTS,
        translation_key=grid.ELEMENT_TYPE,
        describe=grid.model_description,
    ),
    constant_load.ELEMENT_TYPE: ElementRegistryEntry(
        schema=constant_load.ConstantLoadConfigSchema,
        data=constant_load.ConstantLoadConfigData,
        defaults=constant_load.CONFIG_DEFAULTS,
        translation_key=constant_load.ELEMENT_TYPE,
        describe=constant_load.model_description,
    ),
    forecast_load.ELEMENT_TYPE: ElementRegistryEntry(
        schema=forecast_load.ForecastLoadConfigSchema,
        data=forecast_load.ForecastLoadConfigData,
        defaults=forecast_load.CONFIG_DEFAULTS,
        translation_key=forecast_load.ELEMENT_TYPE,
        describe=forecast_load.model_description,
    ),
    node.ELEMENT_TYPE: ElementRegistryEntry(
        schema=node.NodeConfigSchema,
        data=node.NodeConfigData,
        defaults=node.CONFIG_DEFAULTS,
        translation_key=node.ELEMENT_TYPE,
        describe=node.model_description,
    ),
}


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
