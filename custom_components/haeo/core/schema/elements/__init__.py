"""Element schema definitions for HAEO integration."""

from collections.abc import Callable, Mapping
from typing import Final

from custom_components.haeo.core.schema.connection_target import map_connection_targets
from custom_components.haeo.core.schema.elements import battery, buffer, load, policy
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData, BatteryConfigSchema
from custom_components.haeo.core.schema.elements.battery_section import (
    BatterySectionConfigData,
    BatterySectionConfigSchema,
)
from custom_components.haeo.core.schema.elements.buffer import BufferConfigData, BufferConfigSchema
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData, ConnectionConfigSchema
from custom_components.haeo.core.schema.elements.deferrable_load import (
    DeferrableLoadConfigData,
    DeferrableLoadConfigSchema,
)
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.ev import EvConfigData, EvConfigSchema
from custom_components.haeo.core.schema.elements.grid import GridConfigData, GridConfigSchema
from custom_components.haeo.core.schema.elements.inverter import InverterConfigData, InverterConfigSchema
from custom_components.haeo.core.schema.elements.junction import JunctionConfigData, JunctionConfigSchema
from custom_components.haeo.core.schema.elements.load import LoadConfigData, LoadConfigSchema
from custom_components.haeo.core.schema.elements.node import NodeConfigData, NodeConfigSchema
from custom_components.haeo.core.schema.elements.policy import PolicyConfigData, PolicyConfigSchema
from custom_components.haeo.core.schema.elements.solar import SolarConfigData, SolarConfigSchema
from custom_components.haeo.core.schema.field_hints import SurfacedPriceHint

ElementConfigSchema = (
    InverterConfigSchema
    | BatteryConfigSchema
    | BatterySectionConfigSchema
    | DeferrableLoadConfigSchema
    | EvConfigSchema
    | GridConfigSchema
    | LoadConfigSchema
    | SolarConfigSchema
    | NodeConfigSchema
    | JunctionConfigSchema
    | PolicyConfigSchema
    | BufferConfigSchema
    | ConnectionConfigSchema
)

ElementConfigData = (
    InverterConfigData
    | BatteryConfigData
    | BatterySectionConfigData
    | DeferrableLoadConfigData
    | EvConfigData
    | GridConfigData
    | LoadConfigData
    | SolarConfigData
    | NodeConfigData
    | JunctionConfigData
    | PolicyConfigData
    | BufferConfigData
    | ConnectionConfigData
)

ELEMENT_CONFIG_SCHEMAS: Final[dict[ElementType, type]] = {
    ElementType.BATTERY: BatteryConfigSchema,
    ElementType.BATTERY_SECTION: BatterySectionConfigSchema,
    ElementType.BUFFER: BufferConfigSchema,
    ElementType.CONNECTION: ConnectionConfigSchema,
    ElementType.DEFERRABLE_LOAD: DeferrableLoadConfigSchema,
    ElementType.EV: EvConfigSchema,
    ElementType.GRID: GridConfigSchema,
    ElementType.INVERTER: InverterConfigSchema,
    ElementType.JUNCTION: JunctionConfigSchema,
    ElementType.LOAD: LoadConfigSchema,
    ElementType.NODE: NodeConfigSchema,
    ElementType.POLICY: PolicyConfigSchema,
    ElementType.SOLAR: SolarConfigSchema,
}

# Policy pricing fields an element type shows on its own form
ELEMENT_SURFACED_PRICE_HINTS: Final[Mapping[str, Mapping[str, SurfacedPriceHint]]] = {
    ElementType.BATTERY: battery.SURFACED_PRICE_HINTS,
    ElementType.LOAD: load.SURFACED_PRICE_HINTS,
}

# Returns an element's config with each element it names replaced by what the
# resolver returns for that name
type ReferenceMapper = Callable[[Mapping[str, object], Callable[[str], str]], Mapping[str, object]]

# Element types whose config names other elements in lists, and how each maps them
ELEMENT_REFERENCE_MAPPERS: Final[Mapping[str, ReferenceMapper]] = {
    ElementType.BUFFER: buffer.map_references,
    ElementType.POLICY: policy.map_references,
}


def map_element_references(
    element_type: str, config: Mapping[str, object], resolve: Callable[[str], str]
) -> Mapping[str, object]:
    """Return an element's config with every element it names replaced by what resolve returns for it.

    Connection targets are renamed wherever they appear in any element's
    config, then element types in ELEMENT_REFERENCE_MAPPERS map the names they list.
    """
    mapped = map_connection_targets(config, resolve)
    mapper = ELEMENT_REFERENCE_MAPPERS.get(element_type)
    return mapper(mapped, resolve) if mapper is not None else mapped


def referenced_element_names(element_type: str, config: Mapping[str, object]) -> set[str]:
    """Return the name of every element an element's config names."""
    names: set[str] = set()

    def record(name: str) -> str:
        names.add(name)
        return name

    map_element_references(element_type, config, record)
    return names


__all__ = [
    "ELEMENT_CONFIG_SCHEMAS",
    "ELEMENT_REFERENCE_MAPPERS",
    "ELEMENT_SURFACED_PRICE_HINTS",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementType",
    "ReferenceMapper",
    "map_element_references",
    "referenced_element_names",
]
