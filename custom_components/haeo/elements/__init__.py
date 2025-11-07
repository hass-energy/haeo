"""HAEO element registry with field-based metadata."""

from collections.abc import Callable, Mapping, Sequence
import logging
from typing import Any, Final, Literal, NamedTuple, TypeGuard

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.schema import flatten, schema_for_type

from . import battery, connection, constant_load, forecast_load, grid, node, photovoltaics

_LOGGER = logging.getLogger(__name__)

type ElementType = Literal[
    "battery",
    "connection",
    "photovoltaics",
    "grid",
    "constant_load",
    "forecast_load",
    "node",
]

ELEMENT_TYPE_BATTERY: Final = battery.ELEMENT_TYPE
ELEMENT_TYPE_CONNECTION: Final = connection.ELEMENT_TYPE
ELEMENT_TYPE_PHOTOVOLTAICS: Final = photovoltaics.ELEMENT_TYPE
ELEMENT_TYPE_GRID: Final = grid.ELEMENT_TYPE
ELEMENT_TYPE_CONSTANT_LOAD: Final = constant_load.ELEMENT_TYPE
ELEMENT_TYPE_FORECAST_LOAD: Final = forecast_load.ELEMENT_TYPE
ELEMENT_TYPE_NODE: Final = node.ELEMENT_TYPE

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


ELEMENT_TYPES: dict[ElementType, ElementRegistryEntry] = {
    battery.ELEMENT_TYPE: ElementRegistryEntry(
        schema=battery.BatteryConfigSchema,
        data=battery.BatteryConfigData,
        defaults=battery.CONFIG_DEFAULTS,
        translation_key=battery.ELEMENT_TYPE,
    ),
    connection.ELEMENT_TYPE: ElementRegistryEntry(
        schema=connection.ConnectionConfigSchema,
        data=connection.ConnectionConfigData,
        defaults=connection.CONFIG_DEFAULTS,
        translation_key=connection.ELEMENT_TYPE,
    ),
    photovoltaics.ELEMENT_TYPE: ElementRegistryEntry(
        schema=photovoltaics.PhotovoltaicsConfigSchema,
        data=photovoltaics.PhotovoltaicsConfigData,
        defaults=photovoltaics.CONFIG_DEFAULTS,
        translation_key=photovoltaics.ELEMENT_TYPE,
    ),
    grid.ELEMENT_TYPE: ElementRegistryEntry(
        schema=grid.GridConfigSchema,
        data=grid.GridConfigData,
        defaults=grid.CONFIG_DEFAULTS,
        translation_key=grid.ELEMENT_TYPE,
    ),
    constant_load.ELEMENT_TYPE: ElementRegistryEntry(
        schema=constant_load.ConstantLoadConfigSchema,
        data=constant_load.ConstantLoadConfigData,
        defaults=constant_load.CONFIG_DEFAULTS,
        translation_key=constant_load.ELEMENT_TYPE,
    ),
    forecast_load.ELEMENT_TYPE: ElementRegistryEntry(
        schema=forecast_load.ForecastLoadConfigSchema,
        data=forecast_load.ForecastLoadConfigData,
        defaults=forecast_load.CONFIG_DEFAULTS,
        translation_key=forecast_load.ELEMENT_TYPE,
    ),
    node.ELEMENT_TYPE: ElementRegistryEntry(
        schema=node.NodeConfigSchema,
        data=node.NodeConfigData,
        defaults=node.CONFIG_DEFAULTS,
        translation_key=node.ELEMENT_TYPE,
    ),
}


class ValidatedElementSubentry(NamedTuple):
    """Validated element subentry with structured configuration."""

    name: str
    element_type: ElementType
    subentry: ConfigSubentry
    config: ElementConfigSchema


def is_element_config_schema(value: Any) -> TypeGuard[ElementConfigSchema]:
    """Return True when value matches any ElementConfigSchema TypedDict."""

    if not isinstance(value, Mapping):
        return False

    element_type = value.get(CONF_ELEMENT_TYPE)
    if element_type not in ELEMENT_TYPES:
        return False

    entry = ELEMENT_TYPES[element_type]
    flattened = flatten({k: v for k, v in value.items() if k != CONF_ELEMENT_TYPE})
    schema = schema_for_type(entry.schema)

    try:
        schema(flattened)
    except (vol.Invalid, vol.MultipleInvalid):
        return False

    return True


def collect_element_subentries(entry: ConfigEntry) -> list[ValidatedElementSubentry]:
    """Return validated element subentries excluding the network element."""

    return [
        ValidatedElementSubentry(
            name=subentry.title,
            element_type=subentry.data[CONF_ELEMENT_TYPE],
            subentry=subentry,
            config=subentry.data,
        )
        for subentry in entry.subentries.values()
        if subentry.subentry_type in ELEMENT_TYPES and is_element_config_schema(subentry.data)
    ]


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
    "ValidatedElementSubentry",
    "collect_element_subentries",
    "is_element_config_schema",
]
