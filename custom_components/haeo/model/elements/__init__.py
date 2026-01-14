"""HAEO model elements.

This module re-exports all element classes for convenient imports.
"""

from dataclasses import dataclass
from typing import Final, Literal

from .battery import BATTERY_OUTPUT_NAMES as BATTERY_OUTPUT_NAMES
from .battery import BATTERY_POWER_CONSTRAINTS as BATTERY_POWER_CONSTRAINTS
from .battery import Battery as Battery
from .battery import BatteryConstraintName as BatteryConstraintName
from .battery import BatteryOutputName as BatteryOutputName
from .battery_balance_connection import BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES
from .battery_balance_connection import ELEMENT_TYPE as MODEL_ELEMENT_BATTERY_BALANCE_CONNECTION
from .battery_balance_connection import BatteryBalanceConnection as BatteryBalanceConnection
from .composite_connection import COMPOSITE_CONNECTION_OUTPUT_NAMES as COMPOSITE_CONNECTION_OUTPUT_NAMES
from .composite_connection import CONNECTION_POWER_SOURCE_TARGET as CONNECTION_POWER_SOURCE_TARGET
from .composite_connection import CONNECTION_POWER_TARGET_SOURCE as CONNECTION_POWER_TARGET_SOURCE
from .composite_connection import CONNECTION_TIME_SLICE as CONNECTION_TIME_SLICE
from .composite_connection import CompositeConnection as CompositeConnection
from .composite_connection import CompositeConnectionOutputName as CompositeConnectionOutputName
from .node import NODE_OUTPUT_NAMES
from .node import Node as Node
from .node import NodeOutputName as NodeOutputName
from .segments import EfficiencySegment as EfficiencySegment
from .segments import PowerLimitSegment as PowerLimitSegment
from .segments import PricingSegment as PricingSegment
from .segments import Segment as Segment

# Element type constants for model layer
MODEL_ELEMENT_TYPE_BATTERY: Final = "battery"
MODEL_ELEMENT_TYPE_NODE: Final = "node"
MODEL_ELEMENT_TYPE_CONNECTION: Final = "connection"
MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION: Final = "battery_balance_connection"

# Type for all model element types
ModelElementType = Literal[
    "battery",
    "node",
    "connection",
    "battery_balance_connection",
]


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
        factory=CompositeConnection,
        output_names=COMPOSITE_CONNECTION_OUTPUT_NAMES,
    ),
    MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION: ElementSpec(
        factory=BatteryBalanceConnection,
        output_names=BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES,
    ),
}

__all__ = [
    "BATTERY_OUTPUT_NAMES",
    "BATTERY_POWER_CONSTRAINTS",
    "COMPOSITE_CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
    "ELEMENTS",
    "MODEL_ELEMENT_BATTERY_BALANCE_CONNECTION",
    "MODEL_ELEMENT_TYPE_BATTERY",
    "MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION",
    "MODEL_ELEMENT_TYPE_CONNECTION",
    "MODEL_ELEMENT_TYPE_NODE",
    "Battery",
    "BatteryBalanceConnection",
    "BatteryConstraintName",
    "BatteryOutputName",
    "CompositeConnection",
    "CompositeConnectionOutputName",
    "EfficiencySegment",
    "ElementSpec",
    "ModelElementType",
    "Node",
    "NodeOutputName",
    "PowerLimitSegment",
    "PricingSegment",
    "Segment",
]
