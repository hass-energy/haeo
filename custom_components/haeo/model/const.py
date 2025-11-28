"""Constants for HAEO energy modeling."""

from typing import Final, Literal

# Network-level output names (created by coordinator, not individual elements)
OUTPUT_NAME_OPTIMIZATION_COST: Final = "optimization_cost"
OUTPUT_NAME_OPTIMIZATION_STATUS: Final = "optimization_status"
OUTPUT_NAME_OPTIMIZATION_DURATION: Final = "optimization_duration"

# Output types
OUTPUT_TYPE_POWER: Final = "power"
OUTPUT_TYPE_POWER_FLOW: Final = "power_flow"
OUTPUT_TYPE_POWER_LIMIT: Final = "power_limit"
OUTPUT_TYPE_ENERGY: Final = "energy"
OUTPUT_TYPE_PRICE: Final = "price"
OUTPUT_TYPE_SOC: Final = "soc"
OUTPUT_TYPE_COST: Final = "cost"
OUTPUT_TYPE_STATUS: Final = "status"
OUTPUT_TYPE_DURATION: Final = "duration"
OUTPUT_TYPE_SHADOW_PRICE: Final = "shadow_price"

type OutputType = Literal[
    "power",
    "power_flow",
    "power_limit",
    "energy",
    "price",
    "soc",
    "cost",
    "status",
    "duration",
    "shadow_price",
]
