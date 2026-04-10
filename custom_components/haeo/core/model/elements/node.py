"""Node entity for electrical system modeling."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import constraint

type NodeElementTypeName = Literal["node"]
ELEMENT_TYPE: Final[NodeElementTypeName] = "node"

type NodeConstraintName = Literal["node_power_balance"]

type NodeOutputName = NodeConstraintName

NODE_POWER_BALANCE: Final[NodeOutputName] = "node_power_balance"

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset((NODE_POWER_BALANCE,))


class NodeElementConfig(TypedDict):
    """Configuration for Node model elements."""

    element_type: NodeElementTypeName
    name: str
    is_source: NotRequired[bool]
    is_sink: NotRequired[bool]


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
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        is_source: bool = True,
        is_sink: bool = True,
    ) -> None:
        """Initialize a node entity.

        Args:
            name: Name of the node
            periods: Array of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            is_source: Whether this element can produce power (source behavior)
            is_sink: Whether this element can consume power (sink behavior)

        """
        super().__init__(name=name, periods=periods, solver=solver, output_names=NODE_OUTPUT_NAMES)

        # Store if we are a source and/or sink
        self.is_source = is_source
        self.is_sink = is_sink

    @constraint(output=True, unit="$/kW")
    def node_power_balance(self) -> list[highs_linear_expression] | None:
        """Bound the connection power based on source/sink behavior.

        Output: shadow price indicating the marginal cost/value of power at this node.
        """
        conn_power = self.connection_power()

        if not self.is_source and not self.is_sink:
            return list(conn_power == 0)
        if self.is_source and not self.is_sink:
            return list(conn_power <= 0)
        if not self.is_source and self.is_sink:
            return list(conn_power >= 0)
        return None

    @constraint
    def node_tag_power_balance(self) -> list[highs_linear_expression] | None:
        """Per-tag power balance at this node.

        Each tag's power must independently satisfy the same source/sink
        constraints as the total. This ensures tagged power cannot be
        "laundered" by mixing tags at intermediate nodes.

        For junction nodes (not source, not sink): each tag balances to zero.
        For source-only nodes: each tag can flow out independently.
        For sink-only nodes: each tag can flow in independently.
        For source+sink nodes: no per-tag constraint (free to mix).
        """
        tags = self.connection_tags()
        if not tags or len(tags) <= 1:
            # Single tag — per-tag balance is redundant with total balance
            return None

        constraints = []
        for tag in tags:
            tag_power = self.connection_power_for_tag(tag)

            if not self.is_source and not self.is_sink:
                constraints.extend(list(tag_power == 0))
            elif self.is_source and not self.is_sink:
                constraints.extend(list(tag_power <= 0))
            elif not self.is_source and self.is_sink:
                constraints.extend(list(tag_power >= 0))
            # source+sink: no constraint per tag

        return constraints if constraints else None
