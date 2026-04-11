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
    access_list: NotRequired[list[int] | None]


class Node(Element[NodeOutputName]):
    """Node entity for electrical system modeling.

    Tagged power (inherited from Element):
    - source_tag: only this tag can carry outbound power
    - access_list: only these tags can be consumed
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
        access_list: list[int] | None = None,
    ) -> None:
        """Initialize a node entity."""
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=NODE_OUTPUT_NAMES,
            source_tag=source_tag,
            access_list=access_list,
        )
        self.is_source = is_source
        self.is_sink = is_sink

    @constraint(output=True, unit="$/kW")
    def node_power_balance(self) -> list[highs_linear_expression] | None:
        """Bound the connection power based on source/sink behavior."""
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

        Each tag independently satisfies source/sink constraints.
        Source enforcement and access lists handled by Element.element_tag_enforcement.
        """
        tags = self.connection_tags()
        if not tags or len(tags) <= 1:
            return None

        constraints = []
        for tag in tags:
            # Skip tags handled by element_tag_enforcement
            if self._source_tag is not None and tag != self._source_tag:
                continue
            if self._access_list is not None and tag not in self._access_list and tag != self._source_tag:
                continue

            tag_power = self.connection_power_for_tag(tag)
            if not self.is_source and not self.is_sink:
                constraints.extend(list(tag_power == 0))
            elif self.is_source and not self.is_sink:
                constraints.extend(list(tag_power <= 0))
            elif not self.is_source and self.is_sink:
                constraints.extend(list(tag_power >= 0))

        return constraints if constraints else None
