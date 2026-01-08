"""HAEO model elements.

This module re-exports all element classes for convenient imports.
"""

from dataclasses import dataclass
from typing import Final

from .battery import BATTERY_CONSTRAINT_NAMES as BATTERY_CONSTRAINT_NAMES
from .battery import BATTERY_OUTPUT_NAMES as BATTERY_OUTPUT_NAMES
from .battery import BATTERY_POWER_CONSTRAINTS as BATTERY_POWER_CONSTRAINTS
from .battery import Battery as Battery
from .battery import BatteryConstraintName as BatteryConstraintName
from .battery import BatteryOutputName as BatteryOutputName
from .battery_balance_connection import BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES
from .battery_balance_connection import ELEMENT_TYPE as MODEL_ELEMENT_BATTERY_BALANCE_CONNECTION
from .battery_balance_connection import BatteryBalanceConnection as BatteryBalanceConnection
from .connection import CONNECTION_OUTPUT_NAMES as CONNECTION_OUTPUT_NAMES
from .connection import CONNECTION_POWER_SOURCE_TARGET as CONNECTION_POWER_SOURCE_TARGET
from .connection import CONNECTION_POWER_TARGET_SOURCE as CONNECTION_POWER_TARGET_SOURCE
from .connection import CONNECTION_TIME_SLICE as CONNECTION_TIME_SLICE
from .connection import Connection as Connection
from .connection import ConnectionConstraintName as ConnectionConstraintName
from .connection import ConnectionOutputName as ConnectionOutputName
from .node import NODE_OUTPUT_NAMES
from .node import Node as Node
from .node import NodeOutputName as NodeOutputName
from .power_connection import POWER_CONNECTION_OUTPUT_NAMES as POWER_CONNECTION_OUTPUT_NAMES
from .power_connection import PowerConnection as PowerConnection
from .power_connection import PowerConnectionOutputName as PowerConnectionOutputName


@dataclass(frozen=True, slots=True)
class ElementSpec:
    """Specification for a model element type."""

    factory: type
    output_names: frozenset[str]


# Registry of all model element types.
# Keys are element type strings used by Network.add().
ELEMENTS: Final[dict[str, ElementSpec]] = {
    "battery": ElementSpec(
        factory=Battery,
        output_names=BATTERY_OUTPUT_NAMES,
    ),
    "node": ElementSpec(
        factory=Node,
        output_names=NODE_OUTPUT_NAMES,
    ),
    "connection": ElementSpec(
        factory=PowerConnection,
        output_names=POWER_CONNECTION_OUTPUT_NAMES,
    ),
    "battery_balance_connection": ElementSpec(
        factory=BatteryBalanceConnection,
        output_names=BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES,
    ),
}

__all__ = [
    "BATTERY_CONSTRAINT_NAMES",
    "BATTERY_OUTPUT_NAMES",
    "BATTERY_POWER_CONSTRAINTS",
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
    "ELEMENTS",
    "MODEL_ELEMENT_BATTERY_BALANCE_CONNECTION",
    "POWER_CONNECTION_OUTPUT_NAMES",
    "Battery",
    "BatteryBalanceConnection",
    "BatteryConstraintName",
    "BatteryOutputName",
    "Connection",
    "ConnectionConstraintName",
    "ConnectionOutputName",
    "ElementSpec",
    "Node",
    "NodeOutputName",
    "PowerConnection",
    "PowerConnectionOutputName",
]
