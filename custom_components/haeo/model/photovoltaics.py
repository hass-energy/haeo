"""Photovoltaics entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from pulp import LpAffineExpression, LpVariable, lpSum

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_POWER_LIMIT, OUTPUT_TYPE_PRICE, OUTPUT_TYPE_SHADOW_PRICE, OutputData
from .element import Element
from .util import broadcast_to_sequence

PHOTOVOLTAICS_POWER_PRODUCED: Final = "photovoltaics_power_produced"
PHOTOVOLTAICS_POWER_AVAILABLE: Final = "photovoltaics_power_available"
PHOTOVOLTAICS_PRICE_PRODUCTION: Final = "photovoltaics_price_production"

PHOTOVOLTAICS_POWER_BALANCE: Final = "photovoltaics_power_balance"
PHOTOVOLTAICS_FORECAST_LIMIT: Final = "photovoltaics_forecast_limit"

type PhotovoltaicsConstraintName = Literal[
    "photovoltaics_power_balance",
    "photovoltaics_forecast_limit",
]

type PhotovoltaicsOutputName = (
    Literal[
        "photovoltaics_power_produced",
        "photovoltaics_power_available",
        "photovoltaics_price_production",
    ]
    | PhotovoltaicsConstraintName
)

PHOTOVOLTAICS_OUTPUT_NAMES: Final[frozenset[PhotovoltaicsOutputName]] = frozenset(
    (
        PHOTOVOLTAICS_POWER_PRODUCED,
        PHOTOVOLTAICS_POWER_AVAILABLE,
        PHOTOVOLTAICS_PRICE_PRODUCTION,
        PHOTOVOLTAICS_POWER_BALANCE,
        PHOTOVOLTAICS_FORECAST_LIMIT,
    )
)


class Photovoltaics(Element[PhotovoltaicsOutputName, PhotovoltaicsConstraintName]):
    """Photovoltaics (solar) entity for electrical system modeling."""

    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
        *,
        forecast: Sequence[float],
        curtailment: bool = True,
        price_production: Sequence[float] | None = None,
    ) -> None:
        """Initialize a photovoltaics entity.

        Args:
            name: Name of the photovoltaics system
            period: Time period in hours
            n_periods: Number of time periods
            forecast: Forecasted power generation in kW per period
            price_production: Price in $/kWh for production per period (e.g., maintenance cost)
            curtailment: Whether generation can be curtailed below forecast

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Validate forecast length strictly
        if len(forecast) != n_periods:
            msg = f"Sequence length {len(forecast)} must match n_periods {n_periods}"
            raise ValueError(msg)

        # Validate price_production length strictly
        if isinstance(price_production, Sequence) and len(price_production) != n_periods:
            msg = f"Sequence length {len(price_production)} must match n_periods {n_periods}"
            raise ValueError(msg)

        # Validate and store forecasts
        self.forecast = broadcast_to_sequence(forecast, n_periods)
        self.price_production = broadcast_to_sequence(price_production, n_periods)
        self.curtailment = curtailment

        # Power production variables or constants
        if curtailment:
            # Use explicit constraint instead of upBound to capture shadow price
            self.power_production: list[LpVariable | LpAffineExpression] = [
                LpVariable(name=f"{name}_power_{i}", lowBound=0) for i in range(n_periods)
            ]
            self._constraints[PHOTOVOLTAICS_FORECAST_LIMIT] = [
                self.power_production[t] <= self.forecast[t] for t in range(n_periods)
            ]
        else:
            self.power_production = [LpAffineExpression(constant=v) for v in self.forecast]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the photovoltaics.

        This includes power balance constraints using connection_power().
        """
        self._constraints[PHOTOVOLTAICS_POWER_BALANCE] = [
            self.connection_power(t) + self.power_production[t] == 0 for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the photovoltaics."""
        if self.price_production is None:
            return []

        return [
            lpSum(
                price * power * self.period
                for price, power in zip(self.price_production, self.power_production, strict=True)
            )
        ]

    def outputs(self) -> Mapping[PhotovoltaicsOutputName, OutputData]:
        """Return photovoltaics output specifications."""

        outputs: dict[PhotovoltaicsOutputName, OutputData] = {
            PHOTOVOLTAICS_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_production, direction="+"
            ),
            PHOTOVOLTAICS_POWER_AVAILABLE: OutputData(
                type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=self.forecast, direction="+"
            ),
        }

        if self.price_production is not None:
            outputs[PHOTOVOLTAICS_PRICE_PRODUCTION] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=self.price_production
            )

        # Shadow prices
        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
