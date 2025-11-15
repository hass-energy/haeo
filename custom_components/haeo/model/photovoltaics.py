"""Photovoltaics entity for electrical system modeling."""

from collections.abc import Mapping, Sequence

from pulp import LpAffineExpression, LpVariable, lpSum

from .const import (
    CONSTRAINT_NAME_POWER_BALANCE,
    OUTPUT_NAME_POWER_AVAILABLE,
    OUTPUT_NAME_POWER_PRODUCED,
    OUTPUT_NAME_PRICE_PRODUCTION,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OutputData,
    OutputName,
)
from .element import Element
from .util import broadcast_to_sequence, extract_values


class Photovoltaics(Element):
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

        # Validate and store forecasts
        self.forecast = broadcast_to_sequence(forecast, n_periods)
        self.price_production = broadcast_to_sequence(price_production, n_periods)

        # Power production variables or constants
        self.power_production: list[LpVariable] | list[float] = (
            [LpVariable(name=f"{name}_power_{i}", lowBound=0, upBound=v) for i, v in enumerate(self.forecast)]
            if curtailment
            else self.forecast
        )

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the photovoltaics.

        This includes power balance constraints using connection_power().
        """
        self._constraints[CONSTRAINT_NAME_POWER_BALANCE] = [
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

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return photovoltaics output specifications."""

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_production)
            ),
            OUTPUT_NAME_POWER_AVAILABLE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(self.forecast)),
        }

        if self.price_production is not None:
            outputs[OUTPUT_NAME_PRICE_PRODUCTION] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.price_production)
            )

        return outputs
