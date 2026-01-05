"""Node entity for electrical system modeling."""

from collections.abc import Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_linear_expression

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import constraint, output

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
    def power_balance_constraint(self) -> list[highs_linear_expression] | None:
        """Bound the connection power based on source/sink behavior."""
        # We don't need power variables explicitly defined here, a source is a lack of upper bound on power out,
        # and a sink is a lack of upper bound on power in. We just need to enforce power balance with connection power.

        conn_power = self.connection_power()

        if not self.is_source and not self.is_sink:
            # Power balance is that connection power must be zero
            return list(conn_power == 0)
        if self.is_source and not self.is_sink:
            # Only produce power therefore connection power can be less than or equal to zero
            return list(conn_power <= 0)
        if not self.is_source and self.is_sink:
            # Only consume power therefore connection power can be >= 0
            return list(conn_power >= 0)
        # Can both produce and consume power so there are no bounds
        return None

    @output
    def node_power_balance(self) -> OutputData | None:
        """Output: shadow price for power balance constraint.

        Adapter layer maps this to element-specific names (grid_power_imported, load_power_consumed, etc.)
        """
        if "power_balance_constraint" not in self._applied_constraints:
            return None
        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit="$/kW",
            values=self.extract_values(self._applied_constraints["power_balance_constraint"]),
        )
