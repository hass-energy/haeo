"""Element schema definitions for HAEO integration."""

from collections.abc import Callable, Mapping
from collections.abc import Set as AbstractSet
from typing import Final

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

# Returns an element's config without references to elements outside the given
# names, or None when the element is left with nothing to do and is removed
type ReferencePruner = Callable[[Mapping[str, object], AbstractSet[str]], Mapping[str, object] | None]

# Element types whose config names other elements, and how each drops names
# of elements that no longer exist
ELEMENT_REFERENCE_PRUNERS: Final[Mapping[str, ReferencePruner]] = {
    ElementType.BUFFER: buffer.prune_references,
    ElementType.POLICY: policy.prune_references,
}

__all__ = [
    "ELEMENT_CONFIG_SCHEMAS",
    "ELEMENT_REFERENCE_PRUNERS",
    "ELEMENT_SURFACED_PRICE_HINTS",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementType",
    "ReferencePruner",
]
