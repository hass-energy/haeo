"""Node for electrical system modeling."""

from custom_components.haeo.model.element import Element


class Node(Element):
    """Node for electrical system modeling."""

    def __init__(self, name: str, period: int, n_periods: int) -> None:
        """Initialize a node.

        Args:
            name: Name of the node
            period: Time period in seconds
            n_periods: Number of time periods

        """
        super().__init__(name=name, period=period, n_periods=n_periods)
