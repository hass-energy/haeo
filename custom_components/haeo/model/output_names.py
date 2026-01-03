"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from typing import Final

from .connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .energy_balance_connection import ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES, EnergyBalanceConnectionOutputName
from .energy_storage import ENERGY_STORAGE_OUTPUT_NAMES, EnergyStorageOutputName
from .node import NODE_OUTPUT_NAMES, NodeOutputName
from .power_connection import POWER_CONNECTION_OUTPUT_NAMES, PowerConnectionOutputName

# Combined type for all possible output names
type ModelOutputName = (
    EnergyStorageOutputName | PowerConnectionOutputName | NodeOutputName | EnergyBalanceConnectionOutputName
)

# Model-level output names
MODEL_OUTPUT_NAMES: Final[frozenset[str]] = frozenset(
    {
        *ENERGY_STORAGE_OUTPUT_NAMES,
        *ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES,
        *POWER_CONNECTION_OUTPUT_NAMES,
        *NODE_OUTPUT_NAMES,
    }
)

__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES",
    "ENERGY_STORAGE_OUTPUT_NAMES",
    "MODEL_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "POWER_CONNECTION_OUTPUT_NAMES",
    "ConnectionOutputName",
    "EnergyBalanceConnectionOutputName",
    "EnergyStorageOutputName",
    "ModelOutputName",
    "NodeOutputName",
    "PowerConnectionOutputName",
]
