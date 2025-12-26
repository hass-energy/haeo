"""Constants for HAEO energy modeling."""

from typing import Final, Literal

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
    "boolean",
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
        OUTPUT_TYPE_BOOLEAN := "boolean",
    )
)
