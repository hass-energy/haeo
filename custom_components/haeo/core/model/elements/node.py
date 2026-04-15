"""Node entity for electrical system modeling."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
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

    Node acts as an infinite source and/or sink. Power limits and pricing are
    configured on the Connection to/from the node.

    The node returns separate produced/consumed power expressions whose bounds
    encode the source/sink behavior:

    - source+sink: produced ≥ 0, consumed ≥ 0 (no total balance constraint)
    - source only: produced ≥ 0
    - sink only: consumed ≥ 0
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

        n = self.n_periods
        self._produced: HighspyArray | None = None
        self._consumed: HighspyArray | None = None
        if is_source:
            self._produced = solver.addVariables(n, lb=0, name_prefix=f"{name}_prod_", out_array=True)
        if is_sink:
            self._consumed = solver.addVariables(n, lb=0, name_prefix=f"{name}_cons_", out_array=True)

    def element_power_produced(self) -> HighspyArray | int:
        """Return production: bounded [0, inf] for sources, 0 otherwise."""
        return self._produced if self._produced is not None else 0

    def element_power_consumed(self) -> HighspyArray | int:
        """Return consumption: bounded [0, inf] for sinks, 0 otherwise."""
        return self._consumed if self._consumed is not None else 0

    @constraint(output=True, unit="$/kW")
    def node_power_balance(self) -> list[highs_linear_expression] | None:
        """Total power balance: connection_power + produced - consumed == 0."""
        if self.is_source and self.is_sink:
            return None
        return list(
            self.connection_power()
            + self.element_power_produced()
            - self.element_power_consumed()
            == 0
        )
