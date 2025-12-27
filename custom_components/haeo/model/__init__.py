"""HAEO energy modeling components."""

from typing import Final

from .battery_balance_connection import BatteryBalanceConnection as BatteryBalanceConnection
from .connection import CONNECTION_OUTPUT_NAMES as CONNECTION_OUTPUT_NAMES
from .connection import CONNECTION_POWER_SOURCE_TARGET as CONNECTION_POWER_SOURCE_TARGET
from .connection import CONNECTION_POWER_TARGET_SOURCE as CONNECTION_POWER_TARGET_SOURCE
from .connection import CONNECTION_TIME_SLICE as CONNECTION_TIME_SLICE
from .connection import Connection as Connection
from .connection import ConnectionConstraintName as ConnectionConstraintName
from .connection import ConnectionOutputName as ConnectionOutputName
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
from .power_connection import POWER_CONNECTION_OUTPUT_NAMES as POWER_CONNECTION_OUTPUT_NAMES
from .power_connection import PowerConnection as PowerConnection
from .power_connection import PowerConnectionOutputName as PowerConnectionOutputName

# Model element type constant for balance connections (internal battery bookkeeping)
MODEL_ELEMENT_BATTERY_BALANCE_CONNECTION: Final = "battery_balance_connection"

__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
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
    "POWER_CONNECTION_OUTPUT_NAMES",
    "BatteryBalanceConnection",
    "Connection",
    "ConnectionConstraintName",
    "ConnectionOutputName",
    "Element",
    "ModelOutputName",
    "Network",
    "OutputData",
    "OutputType",
    "PowerConnection",
    "PowerConnectionOutputName",
]
