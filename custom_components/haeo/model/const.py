"""Constants for HAEO energy modeling."""

from typing import Final, Literal

# Network-level output names (created by coordinator, not individual elements)
type NetworkOutputName = Literal[
    "optimization_cost",
    "optimization_status",
    "optimization_duration",
]

NETWORK_OUTPUT_NAMES: Final[frozenset[NetworkOutputName]] = frozenset(
    (
        OUTPUT_NAME_OPTIMIZATION_COST := "optimization_cost",
        OUTPUT_NAME_OPTIMIZATION_STATUS := "optimization_status",
        OUTPUT_NAME_OPTIMIZATION_DURATION := "optimization_duration",
    )
)

# Output types
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

OUTPUT_TYPES: Final[frozenset[OutputType]] = frozenset(
    (
        OUTPUT_TYPE_POWER := "power",
        OUTPUT_TYPE_POWER_FLOW := "power_flow",
        OUTPUT_TYPE_POWER_LIMIT := "power_limit",
        OUTPUT_TYPE_ENERGY := "energy",
        OUTPUT_TYPE_PRICE := "price",
        OUTPUT_TYPE_SOC := "soc",
        OUTPUT_TYPE_COST := "cost",
        OUTPUT_TYPE_STATUS := "status",
        OUTPUT_TYPE_DURATION := "duration",
        OUTPUT_TYPE_SHADOW_PRICE := "shadow_price",
    )
)
