"""Connection class for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from pulp import LpAffineExpression, LpVariable, lpSum

from .const import OUTPUT_TYPE_POWER_FLOW, OUTPUT_TYPE_SHADOW_PRICE, OutputData
from .element import Element
from .util import broadcast_to_sequence, extract_values

CONNECTION_POWER_SOURCE_TARGET: Final = "connection_power_source_target"
CONNECTION_POWER_TARGET_SOURCE: Final = "connection_power_target_source"

CONNECTION_MAX_POWER_SOURCE_TARGET: Final = "connection_max_power_source_target"
CONNECTION_MAX_POWER_TARGET_SOURCE: Final = "connection_max_power_target_source"

type ConnectionConstraintName = Literal[
    "connection_max_power_source_target",
    "connection_max_power_target_source",
]

type ConnectionOutputName = (
    Literal[
        "connection_power_source_target",
        "connection_power_target_source",
    ]
    | ConnectionConstraintName
)

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_SOURCE_TARGET,
        CONNECTION_POWER_TARGET_SOURCE,
        CONNECTION_MAX_POWER_SOURCE_TARGET,
        CONNECTION_MAX_POWER_TARGET_SOURCE,
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

        # Initialize base Element class
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Store source and target
        self.source = source
        self.target = target

        # Broadcast power limits to n_periods
        st_bounds = broadcast_to_sequence(max_power_source_target, n_periods)
        ts_bounds = broadcast_to_sequence(max_power_target_source, n_periods)

        # Initialize separate power variables for each direction (both positive, bounds as constraints)
        self.power_source_target = [LpVariable(name=f"{name}_power_st_{i}", lowBound=0) for i in range(n_periods)]
        self.power_target_source = [LpVariable(name=f"{name}_power_ts_{i}", lowBound=0) for i in range(n_periods)]

        # Add power bound constraints if specified
        if st_bounds is not None:
            self._constraints[CONNECTION_MAX_POWER_SOURCE_TARGET] = [
                self.power_source_target[t] <= st_bounds[t] for t in range(n_periods)
            ]
        if ts_bounds is not None:
            self._constraints[CONNECTION_MAX_POWER_TARGET_SOURCE] = [
                self.power_target_source[t] <= ts_bounds[t] for t in range(n_periods)
            ]

        # Broadcast and convert efficiency to fraction (default 100% = 1.0)
        st_eff_values = broadcast_to_sequence(efficiency_source_target, n_periods)
        self.efficiency_source_target = [e / 100.0 for e in st_eff_values] if st_eff_values else [1.0] * n_periods

        ts_eff_values = broadcast_to_sequence(efficiency_target_source, n_periods)
        self.efficiency_target_source = [e / 100.0 for e in ts_eff_values] if ts_eff_values else [1.0] * n_periods

        # Store prices (None means no cost)
        self.price_source_target = price_source_target
        self.price_target_source = price_target_source

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the connection with transfer pricing.

        Returns a sequence of cost expressions for aggregation at the network level.
        """
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
                type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=extract_values(self.power_source_target), direction="+"
            ),
            CONNECTION_POWER_TARGET_SOURCE: OutputData(
                type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=extract_values(self.power_target_source), direction="-"
            ),
        }

        # Shadow prices for power flow limits
        if shadow_prices := self._get_shadow_prices(CONNECTION_MAX_POWER_SOURCE_TARGET):
            outputs[CONNECTION_MAX_POWER_SOURCE_TARGET] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        if shadow_prices := self._get_shadow_prices(CONNECTION_MAX_POWER_TARGET_SOURCE):
            outputs[CONNECTION_MAX_POWER_TARGET_SOURCE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        return outputs
