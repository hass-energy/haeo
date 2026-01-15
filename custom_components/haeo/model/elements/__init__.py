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
from .battery import BatteryElementType as BatteryElementType
from .battery import BatteryOutputName as BatteryOutputName
from .battery_balance_connection import BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES
from .battery_balance_connection import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION
from .battery_balance_connection import BatteryBalanceConnection as BatteryBalanceConnection
from .battery_balance_connection import BatteryBalanceConnectionElementConfig as BatteryBalanceConnectionElementConfig
from .battery_balance_connection import BatteryBalanceConnectionElementType as BatteryBalanceConnectionElementType
from .connection import CONNECTION_OUTPUT_NAMES as CONNECTION_OUTPUT_NAMES
from .connection import CONNECTION_POWER_SOURCE_TARGET as CONNECTION_POWER_SOURCE_TARGET
from .connection import CONNECTION_POWER_TARGET_SOURCE as CONNECTION_POWER_TARGET_SOURCE
from .connection import CONNECTION_TIME_SLICE as CONNECTION_TIME_SLICE
from .connection import Connection as Connection
from .connection import ConnectionConstraintName as ConnectionConstraintName
from .connection import ConnectionOutputName as ConnectionOutputName
from .node import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_NODE
from .node import NODE_OUTPUT_NAMES
from .node import Node as Node
from .node import NodeElementConfig as NodeElementConfig
from .node import NodeElementType as NodeElementType
from .node import NodeOutputName as NodeOutputName
from .power_connection import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_CONNECTION
from .power_connection import POWER_CONNECTION_OUTPUT_NAMES as POWER_CONNECTION_OUTPUT_NAMES
from .power_connection import ConnectionElementConfig as ConnectionElementConfig
from .power_connection import ConnectionElementType as ConnectionElementType
from .power_connection import PowerConnection as PowerConnection
from .power_connection import PowerConnectionOutputName as PowerConnectionOutputName

# Type for all model element types
ModelElementType = BatteryElementType | NodeElementType | ConnectionElementType | BatteryBalanceConnectionElementType

# Typed configs for all model elements (discriminated by element_type)
ModelElementConfig = (
    BatteryElementConfig | NodeElementConfig | ConnectionElementConfig | BatteryBalanceConnectionElementConfig
)


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
        factory=PowerConnection,
        output_names=POWER_CONNECTION_OUTPUT_NAMES,
    ),
    MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION: ElementSpec(
        factory=BatteryBalanceConnection,
        output_names=BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES,
    ),
}

__all__ = [
    "BATTERY_OUTPUT_NAMES",
    "BATTERY_POWER_CONSTRAINTS",
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
    "ELEMENTS",
    "MODEL_ELEMENT_TYPE_BATTERY",
    "MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION",
    "MODEL_ELEMENT_TYPE_CONNECTION",
    "MODEL_ELEMENT_TYPE_NODE",
    "POWER_CONNECTION_OUTPUT_NAMES",
    "Battery",
    "BatteryBalanceConnection",
    "BatteryBalanceConnectionElementConfig",
    "BatteryConstraintName",
    "BatteryElementConfig",
    "BatteryOutputName",
    "Connection",
    "ConnectionConstraintName",
    "ConnectionElementConfig",
    "ConnectionOutputName",
    "ElementSpec",
    "ModelElementConfig",
    "ModelElementType",
    "Node",
    "NodeElementConfig",
    "NodeOutputName",
    "PowerConnection",
    "PowerConnectionOutputName",
]
