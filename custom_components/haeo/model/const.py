"""Constants for HAEO energy modeling."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal, cast

from pulp import LpVariable
from pulp import value as pulp_value

PulpValueFn = Callable[[LpVariable], float]
_PULP_VALUE: Final[PulpValueFn] = cast("Callable[[LpVariable], float]", pulp_value)

# Output names
OUTPUT_NAME_POWER_FLOW: Final = "power_flow"
OUTPUT_NAME_POWER_FLOW_SOURCE_TARGET: Final = "power_flow_source_target"
OUTPUT_NAME_POWER_FLOW_TARGET_SOURCE: Final = "power_flow_target_source"
OUTPUT_NAME_POWER_AVAILABLE: Final = "power_available"
OUTPUT_NAME_POWER_CONSUMED: Final = "power_consumed"
OUTPUT_NAME_POWER_PRODUCED: Final = "power_produced"
OUTPUT_NAME_POWER_IMPORTED: Final = "power_imported"
OUTPUT_NAME_POWER_EXPORTED: Final = "power_exported"

OUTPUT_NAME_PRICE_CONSUMPTION: Final = "price_consumption"
OUTPUT_NAME_PRICE_PRODUCTION: Final = "price_production"
OUTPUT_NAME_PRICE_IMPORT: Final = "price_import"
OUTPUT_NAME_PRICE_EXPORT: Final = "price_export"

OUTPUT_NAME_ENERGY_STORED: Final = "energy_stored"
OUTPUT_NAME_BATTERY_STATE_OF_CHARGE: Final = "battery_state_of_charge"
OUTPUT_NAME_OPTIMIZATION_COST: Final = "optimization_cost"
OUTPUT_NAME_OPTIMIZATION_STATUS: Final = "optimization_status"
OUTPUT_NAME_OPTIMIZATION_DURATION: Final = "optimization_duration"

# Constraint names (will become outputs in future PR)
CONSTRAINT_NAME_ENERGY_BALANCE: Final = "energy_balance"
CONSTRAINT_NAME_POWER_BALANCE: Final = "power_balance"
CONSTRAINT_NAME_MAX_CHARGE_POWER: Final = "max_charge_power"
CONSTRAINT_NAME_MAX_DISCHARGE_POWER: Final = "max_discharge_power"
CONSTRAINT_NAME_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONSTRAINT_NAME_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"

type OutputName = Literal[
    "power_flow",
    "power_flow_source_target",
    "power_flow_target_source",
    "power_available",
    "power_consumed",
    "power_produced",
    "power_imported",
    "power_exported",
    "price_consumption",
    "price_production",
    "price_import",
    "price_export",
    "energy_stored",
    "battery_state_of_charge",
    "optimization_cost",
    "optimization_status",
    "optimization_duration",
]

# Output types
OUTPUT_TYPE_POWER: Final = "power"
OUTPUT_TYPE_ENERGY: Final = "energy"
OUTPUT_TYPE_PRICE: Final = "price"
OUTPUT_TYPE_SOC: Final = "soc"
OUTPUT_TYPE_COST: Final = "cost"
OUTPUT_TYPE_STATUS: Final = "status"
OUTPUT_TYPE_DURATION: Final = "duration"

type OutputType = Literal[
    "power",
    "energy",
    "price",
    "soc",
    "cost",
    "status",
    "duration",
]


@dataclass(frozen=True, slots=True)
class OutputData:
    """Specification for an output exposed by a model element."""

    type: OutputType
    unit: str | None
    values: Sequence[Any]
