"""Photovoltaics entity for electrical system modeling."""

from collections.abc import Mapping, Sequence

import numpy as np
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
        price_production: float | Sequence[float] | None = None,
        price_consumption: float | Sequence[float] | None = None,
    ) -> None:
        """Initialize a photovoltaics entity.

        Args:
            name: Name of the photovoltaics system
            period: Time period in hours
            n_periods: Number of time periods
            forecast: Forecasted power generation in kW
            price_production: Price in $/kWh for production
            price_consumption: Price in $/kWh for consumption (if applicable)
            curtailment: Whether generation can be curtailed below forecast

        """
        # Validate forecast length matches n_periods if provided
        if len(forecast) != n_periods:
            msg = f"forecast length ({len(forecast)}) must match n_periods ({n_periods})"
            raise ValueError(msg)

        # Store the forecast to return as available power
        self.forecast = forecast

        ones = np.ones(n_periods)

        # If we can curtail then we can set the power limits from 0 to the forecast
        # Otherwise we just set the power to the forecast
        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_production=[
                LpVariable(name=f"{name}_power_{i}", lowBound=0, upBound=v) for i, v in enumerate(forecast)
            ]
            if curtailment
            else forecast,
            # ones * price will either be a noop if price is a sequence or will create a sequence if price is a scalar
            price_production=(ones * price_production).tolist() if price_production is not None else None,
            price_consumption=(ones * price_consumption).tolist() if price_consumption is not None else None,
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
