"""Node for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from .const import OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData

type NodeConstraintName = Literal["node_power_balance"]

type NodeOutputName = NodeConstraintName

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset(
    (NODE_POWER_BALANCE := "node_power_balance",),
)


class Node(Element[NodeOutputName, NodeConstraintName]):
    """Node for electrical system modeling."""

    def __init__(self, name: str, periods: Sequence[float]) -> None:
        """Initialize a node.

        Args:
            name: Name of the node
            periods: Sequence of time period durations in hours (one per optimization interval)

        """
        super().__init__(name=name, periods=periods)

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the node.

        This includes power balance constraints using connection_power().
        Nodes are pure junctions with no generation or consumption.
        """
        self._constraints[NODE_POWER_BALANCE] = [self.connection_power(t) == 0 for t in range(self.n_periods)]

    def outputs(self) -> Mapping[NodeOutputName, OutputData]:
        """Return node output specifications."""
        outputs: dict[NodeOutputName, OutputData] = {}

        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
