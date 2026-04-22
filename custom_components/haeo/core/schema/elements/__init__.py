"""Element schema definitions for HAEO integration."""

from typing import Final

from custom_components.haeo.core.schema.elements.battery import BatteryConfigData, BatteryConfigSchema
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
    | GridConfigData
    | LoadConfigData
    | SolarConfigData
    | NodeConfigData
    | PolicyConfigData
    | ConnectionConfigData
)

ELEMENT_CONFIG_SCHEMAS: Final[dict[ElementType, type]] = {
    ElementType.BATTERY: BatteryConfigSchema,
    ElementType.CONNECTION: ConnectionConfigSchema,
    ElementType.GRID: GridConfigSchema,
    ElementType.INVERTER: InverterConfigSchema,
    ElementType.LOAD: LoadConfigSchema,
    ElementType.NODE: NodeConfigSchema,
    ElementType.POLICY: PolicyConfigSchema,
    ElementType.SOLAR: SolarConfigSchema,
}


__all__ = [
    "ELEMENT_CONFIG_SCHEMAS",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementType",
]
