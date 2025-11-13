"""Node for electrical system modeling."""

from collections.abc import Mapping

from .const import OUTPUT_NAME_SHADOW_PRICE_NODE_BALANCE, OUTPUT_TYPE_SHADOW_PRICE, OutputData, OutputName
from .element import Element


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

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return node outputs including power balance shadow prices."""

        outputs = dict(super().outputs())

        if self.power_balance_constraints:
            outputs[OUTPUT_NAME_SHADOW_PRICE_NODE_BALANCE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kWh",
                values=self._shadow_prices(self.power_balance_constraints),
            )

        return outputs
