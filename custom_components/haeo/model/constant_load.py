"""Constant load entity for electrical system modeling."""

from .element import Element


class ConstantLoad(Element):
    """Constant load entity for electrical system modeling."""

    def __init__(self, name: str, period: float, n_periods: int, *, power: float) -> None:
        """Initialize a constant load.

        Args:
            name: Name of the load
            period: Time period in hours
            n_periods: Number of periods
            power: Constant power consumption in kW

        """
        # Create a constant forecast array with the same power value for all periods
        forecast = [power] * n_periods

        # Loads only consume power, they don't produce
        # Power consumption is positive (consuming power)
        # For constant loads, we want to ensure they consume the specified amount therefore there are no variables here
        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_consumption=forecast,
        )
