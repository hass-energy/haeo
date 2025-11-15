"""Node for electrical system modeling."""

from custom_components.haeo.model.const import CONSTRAINT_NAME_POWER_BALANCE
from custom_components.haeo.model.element import Element


class Node(Element):
    """Node for electrical system modeling."""

    def __init__(self, name: str, period: float, n_periods: int) -> None:
        """Initialize a node.

        Args:
            name: Name of the node
            period: Time period in hours (model units)
            n_periods: Number of time periods

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the node.

        This includes power balance constraints using connection_power().
        Nodes are pure junctions with no generation or consumption.
        """
        self._constraints[CONSTRAINT_NAME_POWER_BALANCE] = [
            self.connection_power(t) == 0 for t in range(self.n_periods)
        ]
