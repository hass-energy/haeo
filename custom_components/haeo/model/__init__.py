"""HAEO energy modeling components."""

from typing import Final

from .const import (
    OUTPUT_TYPE_COST,
    OUTPUT_TYPE_DURATION,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
    OUTPUT_TYPE_SOC,
    OUTPUT_TYPE_STATUS,
    OutputType,
)
from .element import Element as Element
from .network import Network as Network
from .output_data import OutputData
from .output_names import ModelOutputName

# Model element type constant for balance connections (internal battery bookkeeping)
MODEL_ELEMENT_BATTERY_BALANCE_CONNECTION: Final = "battery_balance_connection"

__all__ = [
    "MODEL_ELEMENT_BATTERY_BALANCE_CONNECTION",
    "OUTPUT_TYPE_COST",
    "OUTPUT_TYPE_DURATION",
    "OUTPUT_TYPE_ENERGY",
    "OUTPUT_TYPE_POWER",
    "OUTPUT_TYPE_POWER_FLOW",
    "OUTPUT_TYPE_POWER_LIMIT",
    "OUTPUT_TYPE_PRICE",
    "OUTPUT_TYPE_SHADOW_PRICE",
    "OUTPUT_TYPE_SOC",
    "OUTPUT_TYPE_STATUS",
    "Element",
    "ModelOutputName",
    "Network",
    "OutputData",
    "OutputType",
]
