"""Power connection class for electrical system modeling."""

from collections.abc import Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.model.util import broadcast_to_sequence

from .connection import (
    CONNECTION_OUTPUT_NAMES,
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
    Connection,
    ConnectionConstraintName,
    ConnectionOutputName,
)

type PowerConnectionConstraintName = (
    Literal[
        "connection_shadow_power_max_source_target",
        "connection_shadow_power_max_target_source",
    ]
    | ConnectionConstraintName
)

type PowerConnectionOutputName = (
    Literal[
        "connection_cost_source_target",
        "connection_cost_target_source",
    ]
    | PowerConnectionConstraintName
    | ConnectionOutputName
)

POWER_CONNECTION_OUTPUT_NAMES: Final[frozenset[PowerConnectionOutputName]] = frozenset(
    (
        # Cost outputs
        CONNECTION_COST_SOURCE_TARGET := "connection_cost_source_target",
        CONNECTION_COST_TARGET_SOURCE := "connection_cost_target_source",
        # Constraints
        CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET := "connection_shadow_power_max_source_target",
        CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE := "connection_shadow_power_max_target_source",
        CONNECTION_TIME_SLICE,
        *CONNECTION_OUTPUT_NAMES,
    )
)


class PowerConnection(Connection[PowerConnectionOutputName]):
    """Power connection for electrical system modeling.

    Models bidirectional power flow between elements with optional limits,
    efficiency losses, and transfer pricing.

    Extends the base Connection class with:
    - Power limits (max_power_source_target, max_power_target_source)
    - Efficiency losses (efficiency_source_target, efficiency_target_source)
    - Transfer pricing (price_source_target, price_target_source)
    """

    # Parameters
    max_power_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    max_power_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    price_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    price_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        source: str,
        target: str,
        max_power_source_target: float | Sequence[float] | None = None,
        max_power_target_source: float | Sequence[float] | None = None,
        fixed_power: bool = False,
        efficiency_source_target: float | Sequence[float] | None = None,
        efficiency_target_source: float | Sequence[float] | None = None,
        price_source_target: float | Sequence[float] | None = None,
        price_target_source: float | Sequence[float] | None = None,
    ) -> None:
        """Initialize a connection between two elements.

        Args:
            name: Name of the connection
            periods: Sequence of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints
            source: Name of the source element
            target: Name of the target element
            max_power_source_target: Maximum power flow from source to target in kW (per period)
            max_power_target_source: Maximum power flow from target to source in kW (per period)
            fixed_power: If True, power flow is fixed to max_power values
            efficiency_source_target: Efficiency percentage (0-100) for source to target flow
            efficiency_target_source: Efficiency percentage (0-100) for target to source flow
            price_source_target: Price in $/kWh for source to target flow (per period)
            price_target_source: Price in $/kWh for target to source flow (per period)

        """
        # Initialize base Connection class (creates power variables and stores source/target)
        # Pass PowerConnection's extended output set which includes base CONNECTION_OUTPUT_NAMES
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            source=source,
            target=target,
            output_names=POWER_CONNECTION_OUTPUT_NAMES,  # type: ignore[arg-type]  # Parent accepts concrete subclass output names
        )
        n_periods = self.n_periods

        # Set tracked parameters via broadcast
        self.max_power_source_target = broadcast_to_sequence(max_power_source_target, n_periods)
        self.max_power_target_source = broadcast_to_sequence(max_power_target_source, n_periods)
        self.price_source_target = broadcast_to_sequence(price_source_target, n_periods)
        self.price_target_source = broadcast_to_sequence(price_target_source, n_periods)

        # Store fixed_power flag for constraint building
        self._fixed_power = fixed_power

        # Broadcast and convert efficiency to fraction (default 100% = 1.0)
        st_eff_values = broadcast_to_sequence(efficiency_source_target, n_periods)
        if st_eff_values is None:
            st_eff_values = np.ones(n_periods) * 100.0
        self._efficiency_source_target: NDArray[np.floating] = st_eff_values / 100.0

        ts_eff_values = broadcast_to_sequence(efficiency_target_source, n_periods)
        if ts_eff_values is None:
            ts_eff_values = np.ones(n_periods) * 100.0
        self._efficiency_target_source: NDArray[np.floating] = ts_eff_values / 100.0

    @property
    def power_into_source(self) -> HighspyArray:
        """Return effective power flowing into the source element.

        Power leaving source (negative) plus power arriving from target (with efficiency).
        """
        return self._power_target_source * self._efficiency_target_source - self._power_source_target

    @property
    def power_into_target(self) -> HighspyArray:
        """Return effective power flowing into the target element.

        Power arriving from source (with efficiency) minus power leaving target.
        """
        return self._power_source_target * self._efficiency_source_target - self._power_target_source

    @constraint(output=True, unit="$/kW")
    def connection_shadow_power_max_source_target(self) -> list[highs_linear_expression] | None:
        """Constraint: limit power flow from source to target.

        Output: shadow price indicating the marginal value of additional power capacity.
        """
        if self.max_power_source_target is None:
            return None

        if self._fixed_power:
            return list(self.power_source_target == self.max_power_source_target)
        return list(self.power_source_target <= self.max_power_source_target)

    @constraint(output=True, unit="$/kW")
    def connection_shadow_power_max_target_source(self) -> list[highs_linear_expression] | None:
        """Constraint: limit power flow from target to source.

        Output: shadow price indicating the marginal value of additional power capacity.
        """
        if self.max_power_target_source is None:
            return None

        if self._fixed_power:
            return list(self.power_target_source == self.max_power_target_source)
        return list(self.power_target_source <= self.max_power_target_source)

    @constraint(output=True, unit="$/kW")
    def connection_time_slice(self) -> list[highs_linear_expression] | None:
        """Constraint: prevent simultaneous full bidirectional power flow.

        Output: shadow price for time slice constraint.
        """
        if self.max_power_source_target is None or self.max_power_target_source is None:
            return None

        # Create constraints for all periods to maintain consistent structure
        # For periods with zero max power, np.divide gives 0 (where=False)
        # This makes the constraint 0 + 0 <= 1 (always satisfied)
        normalized_st = self.power_source_target * np.divide(
            1.0,
            self.max_power_source_target,
            out=np.zeros(self.n_periods),
            where=np.asarray(self.max_power_source_target) > 0,
        )
        normalized_ts = self.power_target_source * np.divide(
            1.0,
            self.max_power_target_source,
            out=np.zeros(self.n_periods),
            where=np.asarray(self.max_power_target_source) > 0,
        )
        time_slice_exprs = normalized_st + normalized_ts <= 1.0
        return list(time_slice_exprs)

    @cost
    def cost_source_target(self) -> highs_linear_expression | None:
        """Cost for power flow from source to target."""
        if self.price_source_target is None:
            return None
        # Multiply power array by price tuple and period tuple
        return Highs.qsum(self.power_source_target * self.price_source_target * self.periods)

    @cost
    def cost_target_source(self) -> highs_linear_expression | None:
        """Cost for power flow from target to source."""
        if self.price_target_source is None:
            return None
        # Multiply power array by price tuple and period tuple
        return Highs.qsum(self.power_target_source * self.price_target_source * self.periods)

    @output
    def connection_cost_source_target(self) -> OutputData | None:
        """Cost for power flow from source to target."""
        if self.price_source_target is None:
            return None
        power_st = self.extract_values(self.power_source_target)
        cost_st = tuple(p * pw * t for p, pw, t in zip(self.price_source_target, power_st, self.periods, strict=True))
        return OutputData(type=OutputType.COST, unit="$", values=cost_st, direction="+")

    @output
    def connection_cost_target_source(self) -> OutputData | None:
        """Cost for power flow from target to source."""
        if self.price_target_source is None:
            return None
        power_ts = self.extract_values(self.power_target_source)
        cost_ts = tuple(p * pw * t for p, pw, t in zip(self.price_target_source, power_ts, self.periods, strict=True))
        return OutputData(type=OutputType.COST, unit="$", values=cost_ts, direction="-")


# Re-export connection constants for consumers that import from power_connection
__all__ = [
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "PowerConnection",
    "PowerConnectionOutputName",
]
