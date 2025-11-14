"""Load entity for electrical system modeling."""

from collections.abc import Sequence

from .element import Element


class Load(Element):
    """Load entity for electrical system modeling."""

    def __init__(self, name: str, period: float, n_periods: int, forecast: Sequence[float]) -> None:
        """Initialize a load.

        Args:
            name: Name of the load
            period: Time period in hours
            n_periods: Number of periods
            forecast: Sequence of forecasted power consumption values in kW

        """
        if len(forecast) != n_periods:
            msg = f"forecast length ({len(forecast)}) must match n_periods ({n_periods})"
            raise ValueError(msg)

        # Loads only consume power, they don't produce
        # For forecast loads, we want to ensure they consume the forecast amount therefore there are no variables here
        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_consumption=forecast,
        )
