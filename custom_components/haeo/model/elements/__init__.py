"""HAEO model elements.

This module re-exports all element classes for convenient imports.
"""

from dataclasses import dataclass
from typing import Final, Literal

from .connection import CONNECTION_OUTPUT_NAMES as CONNECTION_OUTPUT_NAMES
from .connection import CONNECTION_POWER_SOURCE_TARGET as CONNECTION_POWER_SOURCE_TARGET
from .connection import CONNECTION_POWER_TARGET_SOURCE as CONNECTION_POWER_TARGET_SOURCE
from .connection import CONNECTION_TIME_SLICE as CONNECTION_TIME_SLICE
from .connection import Connection as Connection
from .connection import ConnectionConstraintName as ConnectionConstraintName
from .connection import ConnectionOutputName as ConnectionOutputName
from .energy_balance_connection import ELEMENT_TYPE as MODEL_ELEMENT_ENERGY_BALANCE_CONNECTION
from .energy_balance_connection import ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES as ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES
from .energy_balance_connection import EnergyBalanceConnection as EnergyBalanceConnection
from .energy_balance_connection import EnergyBalanceConnectionOutputName as EnergyBalanceConnectionOutputName
from .energy_storage import ENERGY_STORAGE_OUTPUT_NAMES as ENERGY_STORAGE_OUTPUT_NAMES
from .energy_storage import ENERGY_STORAGE_POWER_CONSTRAINTS as ENERGY_STORAGE_POWER_CONSTRAINTS
from .energy_storage import EnergyStorage as EnergyStorage
from .energy_storage import EnergyStorageConstraintName as EnergyStorageConstraintName
from .energy_storage import EnergyStorageOutputName as EnergyStorageOutputName
from .node import NODE_OUTPUT_NAMES
from .node import Node as Node
from .node import NodeOutputName as NodeOutputName
from .power_connection import POWER_CONNECTION_OUTPUT_NAMES as POWER_CONNECTION_OUTPUT_NAMES
from .power_connection import PowerConnection as PowerConnection
from .power_connection import PowerConnectionOutputName as PowerConnectionOutputName

# Element type constants for model layer
MODEL_ELEMENT_TYPE_ENERGY_STORAGE: Final = "energy_storage"
MODEL_ELEMENT_TYPE_NODE: Final = "node"
MODEL_ELEMENT_TYPE_CONNECTION: Final = "connection"
MODEL_ELEMENT_TYPE_ENERGY_BALANCE_CONNECTION: Final = "energy_balance_connection"

# Type for all model element types
ModelElementType = Literal[
    "energy_storage",
    "node",
    "connection",
    "energy_balance_connection",
]


@dataclass(frozen=True, slots=True)
class ElementSpec:
    """Specification for a model element type."""

    factory: type
    output_names: frozenset[str]


# Registry of all model element types.
# Keys are element type strings used by Network.add().
ELEMENTS: Final[dict[ModelElementType, ElementSpec]] = {
    MODEL_ELEMENT_TYPE_ENERGY_STORAGE: ElementSpec(
        factory=EnergyStorage,
        output_names=ENERGY_STORAGE_OUTPUT_NAMES,
    ),
    MODEL_ELEMENT_TYPE_NODE: ElementSpec(
        factory=Node,
        output_names=NODE_OUTPUT_NAMES,
    ),
    MODEL_ELEMENT_TYPE_CONNECTION: ElementSpec(
        factory=PowerConnection,
        output_names=POWER_CONNECTION_OUTPUT_NAMES,
    ),
    MODEL_ELEMENT_TYPE_ENERGY_BALANCE_CONNECTION: ElementSpec(
        factory=EnergyBalanceConnection,
        output_names=ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES,
    ),
}

__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
    "ELEMENTS",
    "ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES",
    "ENERGY_STORAGE_OUTPUT_NAMES",
    "ENERGY_STORAGE_POWER_CONSTRAINTS",
    "MODEL_ELEMENT_ENERGY_BALANCE_CONNECTION",
    "MODEL_ELEMENT_TYPE_CONNECTION",
    "MODEL_ELEMENT_TYPE_ENERGY_BALANCE_CONNECTION",
    "MODEL_ELEMENT_TYPE_ENERGY_STORAGE",
    "MODEL_ELEMENT_TYPE_NODE",
    "POWER_CONNECTION_OUTPUT_NAMES",
    "Connection",
    "ConnectionConstraintName",
    "ConnectionOutputName",
    "ElementSpec",
    "EnergyBalanceConnection",
    "EnergyBalanceConnectionOutputName",
    "EnergyStorage",
    "EnergyStorageConstraintName",
    "EnergyStorageOutputName",
    "ModelElementType",
    "Node",
    "NodeOutputName",
    "PowerConnection",
    "PowerConnectionOutputName",
]
