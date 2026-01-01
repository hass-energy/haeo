"""Power connection class for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .connection import (
    CONNECTION_OUTPUT_NAMES,
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
    Connection,
    ConnectionConstraintName,
)
from .const import OutputType
from .output_data import OutputData
from .util import broadcast_to_sequence

type PowerConnectionConstraintName = (
    Literal[
        "connection_shadow_power_max_source_target",
        "connection_shadow_power_max_target_source",
    ]
    | ConnectionConstraintName
)

type PowerConnectionOutputName = (
    Literal[
        "connection_power_source_target",
        "connection_power_target_source",
        "connection_power_active",
    ]
    | PowerConnectionConstraintName
)

POWER_CONNECTION_OUTPUT_NAMES: Final[frozenset[PowerConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_ACTIVE := "connection_power_active",
        # Constraints
        CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET := "connection_shadow_power_max_source_target",
        CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE := "connection_shadow_power_max_target_source",
        CONNECTION_TIME_SLICE,
        *CONNECTION_OUTPUT_NAMES,
    )
)


class PowerConnection(Connection[PowerConnectionOutputName, PowerConnectionConstraintName]):
    """Power connection for electrical system modeling.

    Models bidirectional power flow between elements with optional limits,
    efficiency losses, and transfer pricing.

    Extends the base Connection class with:
    - Power limits (max_power_source_target, max_power_target_source)
    - Efficiency losses (efficiency_source_target, efficiency_target_source)
    - Transfer pricing (price_source_target, price_target_source)
    """

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
        super().__init__(name=name, periods=periods, solver=solver, source=source, target=target)
        n_periods = self.n_periods

        # Broadcast power limits to n_periods
        self.max_power_source_target = broadcast_to_sequence(max_power_source_target, n_periods)
        self.max_power_target_source = broadcast_to_sequence(max_power_target_source, n_periods)

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

        # Store prices (None means no cost)
        self.price_source_target = broadcast_to_sequence(price_source_target, n_periods)
        self.price_target_source = broadcast_to_sequence(price_target_source, n_periods)

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

    def build_constraints(self) -> None:
        """Build constraints for the connection.

        Variables are created in __init__, this method only adds constraints.
        """
        h = self._solver

        # Add power constraints - equality if the power is fixed, inequality if only max bounds are provided
        if self.max_power_source_target is not None:
            if self._fixed_power:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = h.addConstrs(
                    self.power_source_target == self.max_power_source_target
                )
            else:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = h.addConstrs(
                    self.power_source_target <= self.max_power_source_target
                )

        if self.max_power_target_source is not None:
            if self._fixed_power:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = h.addConstrs(
                    self.power_target_source == self.max_power_target_source
                )
            else:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = h.addConstrs(
                    self.power_target_source <= self.max_power_target_source
                )

        # Time slicing constraint: prevent simultaneous full bidirectional power flow
        # This allows cycling but on a time-sliced basis (e.g., 50% forward, 50% backward)
        if self.max_power_source_target is not None and self.max_power_target_source is not None:
            # Create constraints for all periods to maintain consistent structure
            # For periods with zero max power, np.divide gives 0 (where=False)
            # This makes the constraint 0 + 0 <= 1 (always satisfied)
            normalized_st = self.power_source_target * np.divide(
                1.0,
                self.max_power_source_target,
                out=np.zeros(self.n_periods),
                where=self.max_power_source_target > 0,
            )
            normalized_ts = self.power_target_source * np.divide(
                1.0,
                self.max_power_target_source,
                out=np.zeros(self.n_periods),
                where=self.max_power_target_source > 0,
            )
            time_slice_exprs = normalized_st + normalized_ts <= 1.0
            self._constraints[CONNECTION_TIME_SLICE] = h.addConstrs(time_slice_exprs)

    def cost(self) -> Sequence[highs_linear_expression]:
        """Return the cost expressions of the connection with transfer pricing."""

        costs: list[highs_linear_expression] = []
        if self.price_source_target is not None:
            costs.append(Highs.qsum(self.price_source_target * self.power_source_target * self.periods))

        if self.price_target_source is not None:
            costs.append(Highs.qsum(self.price_target_source * self.power_target_source * self.periods))

        return costs

    def outputs(self) -> Mapping[PowerConnectionOutputName, OutputData]:
        """Return output specifications for the connection."""
        outputs: dict[PowerConnectionOutputName, OutputData] = {
            CONNECTION_POWER_SOURCE_TARGET: OutputData(
                type=OutputType.POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.power_source_target),
                direction="+",
            ),
            CONNECTION_POWER_TARGET_SOURCE: OutputData(
                type=OutputType.POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.power_target_source),
                direction="-",
            ),
        }

        # Output constraint shadow prices
        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OutputType.SHADOW_PRICE,
                unit="$/kW",
                values=self.extract_values(self._constraints[constraint_name]),
            )

        return outputs
