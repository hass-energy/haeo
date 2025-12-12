"""Connection class for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from pulp import LpAffineExpression, LpVariable, lpSum

from .const import OUTPUT_TYPE_POWER_FLOW, OUTPUT_TYPE_POWER_LIMIT, OUTPUT_TYPE_PRICE, OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence

type ConnectionConstraintName = Literal[
    "connection_shadow_power_max_source_target",
    "connection_shadow_power_max_target_source",
    "connection_time_slice",
]

type ConnectionOutputName = (
    Literal[
        "connection_power_source_target",
        "connection_power_target_source",
        "connection_power_max_source_target",
        "connection_power_max_target_source",
        "connection_price_source_target",
        "connection_price_target_source",
    ]
    | ConnectionConstraintName
)

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_SOURCE_TARGET := "connection_power_source_target",
        CONNECTION_POWER_TARGET_SOURCE := "connection_power_target_source",
        CONNECTION_POWER_MAX_SOURCE_TARGET := "connection_power_max_source_target",
        CONNECTION_POWER_MAX_TARGET_SOURCE := "connection_power_max_target_source",
        CONNECTION_PRICE_SOURCE_TARGET := "connection_price_source_target",
        CONNECTION_PRICE_TARGET_SOURCE := "connection_price_target_source",
        # Constraints
        CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET := "connection_shadow_power_max_source_target",
        CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE := "connection_shadow_power_max_target_source",
        CONNECTION_TIME_SLICE := "connection_time_slice",
    )
)


class Connection(Element[ConnectionOutputName, ConnectionConstraintName]):
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
        fixed_power: bool = False,
        efficiency_source_target: float | Sequence[float] | None = None,
        efficiency_target_source: float | Sequence[float] | None = None,
        price_source_target: float | Sequence[float] | None = None,
        price_target_source: float | Sequence[float] | None = None,
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
            fixed_power: If True, power flow is fixed to max_power values
            efficiency_source_target: Efficiency percentage (0-100) for source to target flow
            efficiency_target_source: Efficiency percentage (0-100) for target to source flow
            price_source_target: Price in $/kWh for source to target flow (per period)
            price_target_source: Price in $/kWh for target to source flow (per period)

        """

        # Initialize base Element class
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Store source and target
        self.source = source
        self.target = target

        # Broadcast power limits to n_periods
        self.max_power_source_target = broadcast_to_sequence(max_power_source_target, n_periods)
        self.max_power_target_source = broadcast_to_sequence(max_power_target_source, n_periods)

        # Initialize separate power variables for each direction (both positive, bounds as constraints)
        self.power_source_target = [LpVariable(name=f"{name}_power_st_{i}", lowBound=0) for i in range(n_periods)]
        self.power_target_source = [LpVariable(name=f"{name}_power_ts_{i}", lowBound=0) for i in range(n_periods)]

        # Broadcast and convert efficiency to fraction (default 100% = 1.0)
        st_eff_values = broadcast_to_sequence(efficiency_source_target, n_periods)
        self.efficiency_source_target = [e / 100.0 for e in st_eff_values] if st_eff_values else [1.0] * n_periods

        ts_eff_values = broadcast_to_sequence(efficiency_target_source, n_periods)
        self.efficiency_target_source = [e / 100.0 for e in ts_eff_values] if ts_eff_values else [1.0] * n_periods

        # Store prices (None means no cost)
        self.price_source_target = broadcast_to_sequence(price_source_target, n_periods)
        self.price_target_source = broadcast_to_sequence(price_target_source, n_periods)

        # Add power constraints - equality if the power is fixed, inequality if only max bounds are provided
        if self.max_power_source_target is not None:
            if fixed_power:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = [
                    self.power_source_target[t] == self.max_power_source_target[t] for t in range(n_periods)
                ]
            else:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = [
                    self.power_source_target[t] <= self.max_power_source_target[t] for t in range(n_periods)
                ]

        if self.max_power_target_source is not None:
            if fixed_power:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = [
                    self.power_target_source[t] == self.max_power_target_source[t] for t in range(n_periods)
                ]
            else:
                self._constraints[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = [
                    self.power_target_source[t] <= self.max_power_target_source[t] for t in range(n_periods)
                ]

        # Time slicing constraint: prevent simultaneous full bidirectional power flow
        # This allows cycling but on a time-sliced basis (e.g., 50% forward, 50% backward)
        if self.max_power_source_target is not None and self.max_power_target_source is not None:
            self._constraints[CONNECTION_TIME_SLICE] = [
                self.power_source_target[t] / self.max_power_source_target[t]
                + self.power_target_source[t] / self.max_power_target_source[t]
                <= 1.0
                for t in range(n_periods)
                if self.max_power_source_target[t] > 0 and self.max_power_target_source[t] > 0
            ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the connection with transfer pricing."""
        costs: list[LpAffineExpression] = []
        if self.price_source_target is not None:
            costs.append(
                lpSum(
                    price * power * self.period
                    for price, power in zip(self.price_source_target, self.power_source_target, strict=True)
                )
            )

        if self.price_target_source is not None:
            costs.append(
                lpSum(
                    price * power * self.period
                    for price, power in zip(self.price_target_source, self.power_target_source, strict=True)
                )
            )

        return costs

    def outputs(self) -> Mapping[ConnectionOutputName, OutputData]:
        """Return output specifications for the connection."""

        outputs: dict[ConnectionOutputName, OutputData] = {
            CONNECTION_POWER_SOURCE_TARGET: OutputData(
                type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=self.power_source_target, direction="+"
            ),
            CONNECTION_POWER_TARGET_SOURCE: OutputData(
                type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=self.power_target_source, direction="-"
            ),
        }

        # Output max power limits if provided
        if self.max_power_source_target is not None:
            outputs[CONNECTION_POWER_MAX_SOURCE_TARGET] = OutputData(
                type=OUTPUT_TYPE_POWER_LIMIT,
                unit="kW",
                values=self.max_power_source_target,
                direction="+",
            )

        if self.max_power_target_source is not None:
            outputs[CONNECTION_POWER_MAX_TARGET_SOURCE] = OutputData(
                type=OUTPUT_TYPE_POWER_LIMIT,
                unit="kW",
                values=self.max_power_target_source,
                direction="-",
            )

        # Output price data if provided
        if self.price_source_target is not None:
            outputs[CONNECTION_PRICE_SOURCE_TARGET] = OutputData(
                type=OUTPUT_TYPE_PRICE,
                unit="$/kWh",
                values=self.price_source_target,
                direction="+",
            )

        if self.price_target_source is not None:
            outputs[CONNECTION_PRICE_TARGET_SOURCE] = OutputData(
                type=OUTPUT_TYPE_PRICE,
                unit="$/kWh",
                values=self.price_target_source,
                direction="-",
            )

        # Output constraint shadow prices
        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
