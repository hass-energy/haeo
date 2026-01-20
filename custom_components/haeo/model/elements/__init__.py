"""HAEO model elements.

This module re-exports all element classes for convenient imports.
"""

from dataclasses import dataclass
from typing import Final

from .battery import BATTERY_OUTPUT_NAMES as BATTERY_OUTPUT_NAMES
from .battery import BATTERY_POWER_CONSTRAINTS as BATTERY_POWER_CONSTRAINTS
from .battery import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_BATTERY
from .battery import Battery as Battery
from .battery import BatteryConstraintName as BatteryConstraintName
from .battery import BatteryElementConfig as BatteryElementConfig
from .battery import BatteryElementTypeName as BatteryElementTypeName
from .battery import BatteryOutputName as BatteryOutputName
from .connection import CONNECTION_OUTPUT_NAMES as CONNECTION_OUTPUT_NAMES
from .connection import CONNECTION_POWER_SOURCE_TARGET as CONNECTION_POWER_SOURCE_TARGET
from .connection import CONNECTION_POWER_TARGET_SOURCE as CONNECTION_POWER_TARGET_SOURCE
from .connection import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_CONNECTION
from .connection import Connection as Connection
from .connection import ConnectionElementConfig as ConnectionElementConfig
from .connection import ConnectionElementTypeName as ConnectionElementTypeName
from .connection import ConnectionOutputName as ConnectionOutputName
from .node import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_NODE
from .node import NODE_OUTPUT_NAMES
from .node import Node as Node
from .node import NodeElementConfig as NodeElementConfig
from .node import NodeElementTypeName as NodeElementTypeName
from .node import NodeOutputName as NodeOutputName
from .segments import BatteryBalanceSegment as BatteryBalanceSegment
from .segments import BatteryBalanceSegmentSpec as BatteryBalanceSegmentSpec
from .segments import EfficiencySegment as EfficiencySegment
from .segments import PassthroughSegment as PassthroughSegment
from .segments import PowerLimitSegment as PowerLimitSegment
from .segments import PricingSegment as PricingSegment
from .segments import Segment as Segment
from .segments import SegmentSpec as SegmentSpec
from .segments import SegmentType as SegmentType

# Type for all model element types
ModelElementType = BatteryElementTypeName | NodeElementTypeName | ConnectionElementTypeName

# Typed configs for all model elements (discriminated by element_type)
ModelElementConfig = BatteryElementConfig | NodeElementConfig | ConnectionElementConfig


@dataclass(frozen=True, slots=True)
class ElementSpec:
    """Specification for a model element type."""

    factory: type
    output_names: frozenset[str]


# Registry of all model element types.
# Keys are element type strings used by Network.add().
ELEMENTS: Final[dict[ModelElementType, ElementSpec]] = {
    MODEL_ELEMENT_TYPE_BATTERY: ElementSpec(
        factory=Battery,
        output_names=BATTERY_OUTPUT_NAMES,
    ),
    MODEL_ELEMENT_TYPE_NODE: ElementSpec(
        factory=Node,
        output_names=NODE_OUTPUT_NAMES,
    ),
    MODEL_ELEMENT_TYPE_CONNECTION: ElementSpec(
        factory=Connection,
        output_names=CONNECTION_OUTPUT_NAMES,
    ),
}

__all__ = [
    "BATTERY_OUTPUT_NAMES",
    "BATTERY_POWER_CONSTRAINTS",
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "ELEMENTS",
    "MODEL_ELEMENT_TYPE_BATTERY",
    "MODEL_ELEMENT_TYPE_CONNECTION",
    "MODEL_ELEMENT_TYPE_NODE",
    "Battery",
    "BatteryBalanceSegment",
    "BatteryBalanceSegmentSpec",
    "BatteryConstraintName",
    "BatteryElementConfig",
    "BatteryOutputName",
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputName",
    "EfficiencySegment",
    "ElementSpec",
    "ModelElementConfig",
    "ModelElementType",
    "Node",
    "NodeElementConfig",
    "NodeOutputName",
    "PassthroughSegment",
    "PowerLimitSegment",
    "PricingSegment",
    "Segment",
    "SegmentSpec",
    "SegmentType",
]
