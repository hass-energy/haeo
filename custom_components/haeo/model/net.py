"""Net entity for electrical system modeling."""

from .element import Element


class Net(Element):
    """Net entity for electrical system modeling."""

    def __init__(self, name: str, period: float, n_periods: int) -> None:
        """Initialize a net entity.

        Args:
            name: Name of the net
            period: Time period in hours
            n_periods: Number of time periods

        """
        super().__init__(name=name, period=period, n_periods=n_periods)
