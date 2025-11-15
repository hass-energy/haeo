"""Connection class for electrical system modeling."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from pulp import LpAffineExpression, LpConstraint, LpVariable, lpSum

from .const import (
    OUTPUT_NAME_POWER_FLOW_SOURCE_TARGET,
    OUTPUT_NAME_POWER_FLOW_TARGET_SOURCE,
    OUTPUT_TYPE_POWER,
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
        period: float,
        n_periods: int,
        *,
        source: str,
        target: str,
        max_power_source_target: float | Sequence[float] | None = None,
        max_power_target_source: float | Sequence[float] | None = None,
        efficiency_source_target: float | Sequence[float] | None = None,
        efficiency_target_source: float | Sequence[float] | None = None,
        price_source_target: Sequence[float] | None = None,
        price_target_source: Sequence[float] | None = None,
    ) -> None:
        """Initialize a connection between two elements.

        Args:
            name: Name of the connection
            period: Time period in hours
            n_periods: Number of time periods
            source: Name of the source element
            target: Name of the target element
            max_power_source_target: Maximum power flow from source to target in kW (per period)
            max_power_target_source: Maximum power flow from target to source in kW (per period)
            efficiency_source_target: Efficiency percentage (0-100) for source to target flow
            efficiency_target_source: Efficiency percentage (0-100) for target to source flow
            price_source_target: Price in $/kWh for source to target flow (per period)
            price_target_source: Price in $/kWh for target to source flow (per period)

        """
        self.name = name
        self.period = period
        self.source = source
        self.target = target

        # Broadcast power limits to n_periods using numpy
        if max_power_source_target is not None:
            st_array = np.broadcast_to(np.atleast_1d(max_power_source_target), (n_periods,))
            st_bounds = st_array.tolist()
        else:
            st_bounds = [None] * n_periods

        if max_power_target_source is not None:
            ts_array = np.broadcast_to(np.atleast_1d(max_power_target_source), (n_periods,))
            ts_bounds = ts_array.tolist()
        else:
            ts_bounds = [None] * n_periods

        # Initialize separate power variables for each direction (both positive)
        self.power_source_target = [
            LpVariable(name=f"{name}_power_st_{i}", lowBound=0, upBound=st_bounds[i]) for i in range(n_periods)
        ]
        self.power_target_source = [
            LpVariable(name=f"{name}_power_ts_{i}", lowBound=0, upBound=ts_bounds[i]) for i in range(n_periods)
        ]

        # Broadcast and convert efficiency to fraction (default 100% = 1.0)
        if efficiency_source_target is not None:
            st_eff_array = np.broadcast_to(np.atleast_1d(efficiency_source_target), (n_periods,))
            self.efficiency_source_target = (st_eff_array / 100.0).tolist()
        else:
            self.efficiency_source_target = [1.0] * n_periods

        if efficiency_target_source is not None:
            ts_eff_array = np.broadcast_to(np.atleast_1d(efficiency_target_source), (n_periods,))
            self.efficiency_target_source = (ts_eff_array / 100.0).tolist()
        else:
            self.efficiency_target_source = [1.0] * n_periods

        # Store prices (None means no cost)
        self.price_source_target = price_source_target
        self.price_target_source = price_target_source

    def constraints(self) -> Sequence[LpConstraint]:
        """Return constraints for the connection."""
        return []

    def cost(self) -> Sequence[tuple[LpAffineExpression, str]]:
        """Return the cost expressions of the connection with transfer pricing.

        Returns a sequence of (cost_expression, label) tuples for aggregation at the network level.
        """
        costs: list[tuple[LpAffineExpression, str]] = []
        if self.price_source_target is not None:
            source_target_cost = lpSum(
                price * power * self.period
                for price, power in zip(self.price_source_target, self.power_source_target, strict=False)
            )
            if isinstance(source_target_cost, LpAffineExpression):
                costs.append((source_target_cost, f"{self.name}_source_to_target_cost"))

        if self.price_target_source is not None:
            target_source_cost = lpSum(
                price * power * self.period
                for price, power in zip(self.price_target_source, self.power_target_source, strict=False)
            )
            if isinstance(target_source_cost, LpAffineExpression):
                costs.append((target_source_cost, f"{self.name}_target_to_source_cost"))

        return costs

    def get_outputs(self) -> Mapping[OutputName, OutputData]:
        """Return output specifications for the connection."""

        return {
            OUTPUT_NAME_POWER_FLOW_SOURCE_TARGET: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_source_target)
            ),
            OUTPUT_NAME_POWER_FLOW_TARGET_SOURCE: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_target_source)
            ),
        }
