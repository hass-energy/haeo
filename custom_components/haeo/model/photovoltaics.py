"""Photovoltaics entity for electrical system modeling."""

from collections.abc import Mapping, Sequence

from pulp import LpVariable

from .const import OUTPUT_NAME_POWER_AVAILABLE, OUTPUT_TYPE_POWER, OutputData, OutputName
from .element import Element


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
        price_consumption: Sequence[float] | None = None,
    ) -> None:
        """Initialize a photovoltaics entity.

        Args:
            name: Name of the photovoltaics system
            period: Time period in hours
            n_periods: Number of time periods
            forecast: Forecasted power generation in kW per period
            price_production: Price in $/kWh for production per period
            price_consumption: Price in $/kWh for consumption per period (if applicable)
            curtailment: Whether generation can be curtailed below forecast

        """
        if len(forecast) != n_periods:
            msg = f"forecast length ({len(forecast)}) must match n_periods ({n_periods})"
            raise ValueError(msg)
        if price_production is not None and len(price_production) != n_periods:
            msg = f"price_production length ({len(price_production)}) must match n_periods ({n_periods})"
            raise ValueError(msg)
        if price_consumption is not None and len(price_consumption) != n_periods:
            msg = f"price_consumption length ({len(price_consumption)}) must match n_periods ({n_periods})"
            raise ValueError(msg)

        self.forecast = forecast

        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_production=[
                LpVariable(name=f"{name}_power_{i}", lowBound=0, upBound=v) for i, v in enumerate(forecast)
            ]
            if curtailment
            else forecast,
            price_production=price_production,
            price_consumption=price_consumption,
        )

    def get_outputs(self) -> Mapping[OutputName, OutputData]:
        """Return photovoltaics output specifications."""

        return {
            **super().get_outputs(),
            # Add the available power sensor output
            OUTPUT_NAME_POWER_AVAILABLE: OutputData(
                type=OUTPUT_TYPE_POWER,
                unit="kW",
                values=tuple(self.forecast),
            ),
        }
