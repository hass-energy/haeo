"""HAEO model elements.

This module re-exports all element classes for convenient imports.
"""

from dataclasses import dataclass
from typing import Final

from .energy_storage import ENERGY_STORAGE_OUTPUT_NAMES as ENERGY_STORAGE_OUTPUT_NAMES
from .energy_storage import ENERGY_STORAGE_POWER_CONSTRAINTS as ENERGY_STORAGE_POWER_CONSTRAINTS
from .energy_storage import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_ENERGY_STORAGE
from .energy_storage import EnergyStorage as EnergyStorage
from .energy_storage import EnergyStorageConstraintName as EnergyStorageConstraintName
from .energy_storage import EnergyStorageElementConfig as EnergyStorageElementConfig
from .energy_storage import EnergyStorageElementTypeName as EnergyStorageElementTypeName
from .energy_storage import EnergyStorageOutputName as EnergyStorageOutputName
from .energy_storage import InventoryCostSpec as InventoryCostSpec
from .connection import CONNECTION_OUTPUT_NAMES as CONNECTION_OUTPUT_NAMES
from .connection import CONNECTION_POWER as CONNECTION_POWER
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
from .segments import EfficiencySegment as EfficiencySegment
from .segments import PassthroughSegment as PassthroughSegment
from .segments import PowerLimitSegment as PowerLimitSegment
from .segments import PricingSegment as PricingSegment
from .segments import Segment as Segment
from .segments import SegmentSpec as SegmentSpec
from .segments import SegmentType as SegmentType

# Type for all model element types
ModelElementType = EnergyStorageElementTypeName | NodeElementTypeName | ConnectionElementTypeName

# Typed configs for all model elements (discriminated by element_type)
ModelElementConfig = EnergyStorageElementConfig | NodeElementConfig | ConnectionElementConfig


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
        factory=Connection,
        output_names=CONNECTION_OUTPUT_NAMES,
    ),
}

__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER",
    "ELEMENTS",
    "ENERGY_STORAGE_OUTPUT_NAMES",
    "ENERGY_STORAGE_POWER_CONSTRAINTS",
    "MODEL_ELEMENT_TYPE_CONNECTION",
    "MODEL_ELEMENT_TYPE_ENERGY_STORAGE",
    "MODEL_ELEMENT_TYPE_NODE",
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputName",
    "EfficiencySegment",
    "ElementSpec",
    "EnergyStorage",
    "EnergyStorageConstraintName",
    "EnergyStorageElementConfig",
    "EnergyStorageOutputName",
    "InventoryCostSpec",
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
