"""Element schema definitions for HAEO integration."""

from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.core.const import HubConfigData
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData, BatteryConfigSchema
from custom_components.haeo.core.schema.elements.battery_section import (
    BatterySectionConfigData,
    BatterySectionConfigSchema,
)
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData, ConnectionConfigSchema
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.grid import GridConfigData, GridConfigSchema
from custom_components.haeo.core.schema.elements.inverter import InverterConfigData, InverterConfigSchema
from custom_components.haeo.core.schema.elements.load import LoadConfigData, LoadConfigSchema
from custom_components.haeo.core.schema.elements.node import NodeConfigData, NodeConfigSchema
from custom_components.haeo.core.schema.elements.policy import PolicyConfigData, PolicyConfigSchema
from custom_components.haeo.core.schema.elements.solar import SolarConfigData, SolarConfigSchema

ElementConfigSchema = (
    InverterConfigSchema
    | BatteryConfigSchema
    | BatterySectionConfigSchema
    | GridConfigSchema
    | LoadConfigSchema
    | SolarConfigSchema
    | NodeConfigSchema
    | PolicyConfigSchema
    | ConnectionConfigSchema
)

ElementConfigData = (
    InverterConfigData
    | BatteryConfigData
    | BatterySectionConfigData
    | GridConfigData
    | LoadConfigData
    | SolarConfigData
    | NodeConfigData
    | PolicyConfigData
    | ConnectionConfigData
)

ELEMENT_CONFIG_SCHEMAS: Final[dict[ElementType, type]] = {
    ElementType.BATTERY: BatteryConfigSchema,
    ElementType.BATTERY_SECTION: BatterySectionConfigSchema,
    ElementType.CONNECTION: ConnectionConfigSchema,
    ElementType.GRID: GridConfigSchema,
    ElementType.INVERTER: InverterConfigSchema,
    ElementType.LOAD: LoadConfigSchema,
    ElementType.NODE: NodeConfigSchema,
    ElementType.POLICY: PolicyConfigSchema,
    ElementType.SOLAR: SolarConfigSchema,
}


class HaeoSubentryDict(TypedDict):
    """Typed subentry as returned by `subentry.as_dict()` (subentry_id and unique_id blocklisted)."""

    subentry_type: ElementType | Literal["network"]
    title: str
    data: ElementConfigSchema


class HaeoConfigEntryDict(TypedDict):
    """Typed config entry as returned by `entry.as_dict()` (HA bookkeeping blocklisted)."""

    version: int
    minor_version: int
    domain: Literal["haeo"]
    title: str
    data: HubConfigData
    options: dict[str, Any]
    subentries: list[HaeoSubentryDict]


__all__ = [
    "ELEMENT_CONFIG_SCHEMAS",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementType",
    "HaeoConfigEntryDict",
    "HaeoSubentryDict",
]
