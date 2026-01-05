"""Node entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_cons

from .const import OutputType
from .element import Element
from .output_data import OutputData
from .reactive import constraint

type NodeConstraintName = Literal["node_power_balance"]

type NodeOutputName = NodeConstraintName

NODE_POWER_BALANCE: Final[NodeOutputName] = "node_power_balance"

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset((NODE_POWER_BALANCE,))


class Node(Element[NodeOutputName]):
    """Node entity for electrical system modeling.

    Node acts as an infinite source and/or sink. Power limits and pricing are configured
    on the Connection to/from the node.

    Behavior is controlled by is_source and is_sink flags:
    - is_source=True, is_sink=True: Can both produce and consume (Grid)
    - is_source=False, is_sink=True: Can only consume (Load)
    - is_source=True, is_sink=False: Can only produce (Solar)
    - is_source=False, is_sink=False: Pure junction with no generation/consumption (Node)
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        is_source: bool = True,
        is_sink: bool = True,
    ) -> None:
        """Initialize a node entity.

        Args:
            name: Name of the node
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            is_source: Whether this element can produce power (source behavior)
            is_sink: Whether this element can consume power (sink behavior)

        """
        super().__init__(name=name, periods=periods, solver=solver)

        # Store if we are a source and/or sink
        self.is_source = is_source
        self.is_sink = is_sink

    @constraint
    def power_balance_constraint(self) -> list[highs_cons] | None:
        """Bound the connection power based on source/sink behavior."""
        h = self._solver

        # We don't need power variables explicitly defined here, a source is a lack of upper bound on power out,
        # and a sink is a lack of upper bound on power in. We just need to enforce power balance with connection power.

        conn_power = self.connection_power()

        if not self.is_source and not self.is_sink:
            # Power balance is that connection power must be zero
            return h.addConstrs(conn_power == 0)
        if self.is_source and not self.is_sink:
            # Only produce power therefore connection power can be less than or equal to zero
            return h.addConstrs(conn_power <= 0)
        if not self.is_source and self.is_sink:
            # Only consume power therefore connection power can be >= 0
            return h.addConstrs(conn_power >= 0)
        # Can both produce and consume power so there are no bounds
        return None

    def outputs(self) -> Mapping[NodeOutputName, OutputData]:
        """Return element-agnostic outputs for the node.

        Adapter layer maps these to element-specific names (grid_power_imported, load_power_consumed, etc.)
        """
        outputs: dict[NodeOutputName, OutputData] = {}

        # All constraints are power balance for Node
        if "power_balance_constraint" in self._applied_constraints:
            constraint = self._applied_constraints["power_balance_constraint"]
            outputs[NODE_POWER_BALANCE] = OutputData(
                type=OutputType.SHADOW_PRICE,
                unit="$/kW",
                values=self.extract_values(constraint),
            )

        return outputs
