"""Connection class for electrical system modeling."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from pulp import LpConstraint, LpVariable

from .const import (
    OUTPUT_NAME_POWER_FLOW,
    OUTPUT_NAME_SHADOW_PRICE_POWER_FLOW_MAX,
    OUTPUT_NAME_SHADOW_PRICE_POWER_FLOW_MIN,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_SHADOW_PRICE,
    OutputData,
    OutputName,
    extract_values,
)


@dataclass
class Connection:
    """Connection class for electrical system modeling."""

    def __init__(
        self,
        name: str,
        period: float,  # noqa: ARG002
        n_periods: int,
        *,
        source: str,
        target: str,
        min_power: float | None = None,
        max_power: float | None = None,
    ) -> None:
        """Initialize a connection between two elements.

        Args:
            name: Name of the connection
            period: Time period in hours
            n_periods: Number of time periods
            source: Name of the source element
            target: Name of the target element
            min_power: Minimum power flow in kW (negative for bidirectional)
            max_power: Maximum power flow in kW

        """
        self.name = name
        self.source = source
        self.target = target

        # Initialize power variables for the connection
        # For bidirectional connections, min_power can be negative
        # Positive power = flow from source to target
        # Negative power = flow from target to source
        # None bounds mean no limit (infinite bounds)
        self.power = [
            LpVariable(name=f"{name}_power_{i}", lowBound=min_power, upBound=max_power) for i in range(n_periods)
        ]
        self.power_min_constraints: dict[int, LpConstraint] = {}
        self.power_max_constraints: dict[int, LpConstraint] = {}

    def build(self) -> None:
        """Store explicit constraints for power bounds so duals are available."""

        self.power_min_constraints.clear()
        self.power_max_constraints.clear()

        for index, power_var in enumerate(self.power):
            if power_var.lowBound is not None:
                constraint = cast("LpConstraint", power_var >= float(power_var.lowBound))
                constraint.name = f"{self.name}_power_min_{index}"
                self.power_min_constraints[index] = constraint

            if power_var.upBound is not None:
                constraint = cast("LpConstraint", power_var <= float(power_var.upBound))
                constraint.name = f"{self.name}_power_max_{index}"
                self.power_max_constraints[index] = constraint

    def constraints(self) -> Sequence[LpConstraint]:
        """Return stored connection constraints."""

        return (*self.power_min_constraints.values(), *self.power_max_constraints.values())

    def cost(self) -> float:
        """Return the cost of the connection with cycling penalties."""
        return 0

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return output specifications for the connection."""

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_FLOW: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power))
        }

        if self.power_min_constraints:
            outputs[OUTPUT_NAME_SHADOW_PRICE_POWER_FLOW_MIN] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._shadow_prices(self.power_min_constraints),
            )

        if self.power_max_constraints:
            outputs[OUTPUT_NAME_SHADOW_PRICE_POWER_FLOW_MAX] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._shadow_prices(self.power_max_constraints),
            )

        return outputs

    @staticmethod
    def _shadow_prices(constraints: Mapping[int, LpConstraint]) -> tuple[float, ...]:
        """Return dual values for the provided constraints."""

        return tuple(
            float(pi) if (pi := getattr(constraint, "pi", None)) is not None else 0.0
            for constraint in constraints.values()
        )
