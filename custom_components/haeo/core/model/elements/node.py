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
    source_tag: NotRequired[int | None]


class Node(Element[NodeOutputName]):
    """Node entity for electrical system modeling.

    Node acts as an infinite source and/or sink. Power limits and pricing are configured
    on the Connection to/from the node.

    Behavior is controlled by is_source and is_sink flags:
    - is_source=True, is_sink=True: Can both produce and consume (Grid)
    - is_source=False, is_sink=True: Can only consume (Load)
    - is_source=True, is_sink=False: Can only produce (Solar)
    - is_source=False, is_sink=False: Pure junction with no generation/consumption (Node)

    Tagged power:
    When source_tag is set, only that tag can carry outbound (produced) power
    from this node. Other tags can only flow inbound or be zero. This is the
    source enforcement mechanism for the policy/VLAN system.
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        is_source: bool = True,
        is_sink: bool = True,
        source_tag: int | None = None,
    ) -> None:
        """Initialize a node entity.

        Args:
            name: Name of the node
            periods: Array of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            is_source: Whether this element can produce power (source behavior)
            is_sink: Whether this element can consume power (sink behavior)
            source_tag: If set, only this tag can carry outbound power from this node.

        """
        super().__init__(name=name, periods=periods, solver=solver, output_names=NODE_OUTPUT_NAMES)

        self.is_source = is_source
        self.is_sink = is_sink
        self._source_tag = source_tag

    @property
    def source_tag(self) -> int | None:
        """Return the source tag for this node, or None."""
        return self._source_tag

    @source_tag.setter
    def source_tag(self, value: int | None) -> None:
        """Set the source tag."""
        self._source_tag = value

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
        """Per-tag power balance and source enforcement at this node.

        Two purposes:
        1. Each tag independently satisfies source/sink constraints at junction nodes.
        2. Source enforcement: when source_tag is set, only that tag can carry
           outbound power. Other tags must have tag_power >= 0 (no outflow).

        This prevents tagged power from being "laundered" at intermediate nodes
        and ensures power provenance is tracked correctly.
        """
        tags = self.connection_tags()
        if not tags or len(tags) <= 1:
            return None

        constraints = []
        for tag in tags:
            tag_power = self.connection_power_for_tag(tag)

            if self._source_tag is not None and tag != self._source_tag:
                # Source enforcement: non-source tags cannot flow outbound.
                # tag_power >= 0 means power can only flow INTO this node for this tag.
                constraints.extend(list(tag_power >= 0))
            elif not self.is_source and not self.is_sink:
                # Junction: each tag must balance to zero
                constraints.extend(list(tag_power == 0))
            elif self.is_source and not self.is_sink:
                # Source-only: each tag can flow out
                constraints.extend(list(tag_power <= 0))
            elif not self.is_source and self.is_sink:
                # Sink-only: each tag can flow in
                constraints.extend(list(tag_power >= 0))
            # source+sink with source_tag: the source_tag has no per-tag constraint
            # (it can flow freely in/out), other tags are constrained above

        return constraints if constraints else None
