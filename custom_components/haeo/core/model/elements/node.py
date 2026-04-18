"""Node entity for electrical system modeling."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, NetworkElement

type NodeElementTypeName = Literal["node"]
ELEMENT_TYPE: Final[NodeElementTypeName] = "node"

type NodeOutputName = Literal["element_power_balance"]

NODE_POWER_BALANCE: Final[NodeOutputName] = ELEMENT_POWER_BALANCE

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset((NODE_POWER_BALANCE,))


class NodeElementConfig(TypedDict):
    """Configuration for Node model elements."""

    element_type: NodeElementTypeName
    name: str
    is_source: NotRequired[bool]
    is_sink: NotRequired[bool]
    outbound_tags: NotRequired[set[int] | None]
    inbound_tags: NotRequired[set[int] | None]


class Node(NetworkElement[NodeOutputName]):
    """Node entity for electrical system modeling.

    Node acts as an infinite source and/or sink. Power limits and pricing are
    configured on the Connection to/from the node.

    Behavior is controlled by is_source and is_sink flags:

    - source+sink: produced ≥ 0, consumed ≥ 0
    - source only: produced ≥ 0, consumed = 0
    - sink only: produced = 0, consumed ≥ 0
    - junction: both 0 (conservation only)
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        is_source: bool = True,
        is_sink: bool = True,
        outbound_tags: set[int] | None = None,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a node entity."""
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=NODE_OUTPUT_NAMES,
            outbound_tags=outbound_tags,
            inbound_tags=inbound_tags,
        )
        self.is_source = is_source
        self.is_sink = is_sink

        n = self.n_periods
        self._produced = (
            solver.addVariables(n, lb=0, name_prefix=f"{name}_prod_", out_array=True) if is_source else None
        )
        self._consumed = solver.addVariables(n, lb=0, name_prefix=f"{name}_cons_", out_array=True) if is_sink else None

    def element_power_produced(self) -> HighspyArray | None:
        """Return production: bounded [0, inf] for sources, None otherwise."""
        return self._produced

    def element_power_consumed(self) -> HighspyArray | None:
        """Return consumption: bounded [0, inf] for sinks, None otherwise."""
        return self._consumed
