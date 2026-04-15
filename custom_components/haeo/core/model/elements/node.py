"""Node entity for electrical system modeling."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs, kHighsInf
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

    The node's ``element_power()`` returns an LP variable whose bounds encode
    the source/sink behavior:

    - source+sink: ``None`` (unconstrained — no total balance needed)
    - source only: variable ≥ 0 (can only produce)
    - sink only: variable ≤ 0 (can only consume)
    - junction: zeros (no external power)
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
        if is_source and is_sink:
            self._external_power: HighspyArray | NDArray[Any] | None = None
        elif is_source:
            self._external_power = solver.addVariables(
                n, lb=0, name_prefix=f"{name}_ep_", out_array=True,
            )
        elif is_sink:
            self._external_power = solver.addVariables(
                n, lb=-kHighsInf, ub=0, name_prefix=f"{name}_ep_", out_array=True,
            )
        else:
            self._external_power = np.zeros(n, dtype=object)

    def element_power(self) -> HighspyArray | NDArray[Any] | None:
        """Return this node's external power injection."""
        return self._external_power

    def element_power_bounds(self) -> tuple[float, float]:
        """Return conceptual bounds: source can produce, sink can consume."""
        lb = -kHighsInf if self.is_sink else 0.0
        ub = kHighsInf if self.is_source else 0.0
        return (lb, ub)

    @constraint(output=True, unit="$/kW")
    def node_power_balance(self) -> list[highs_linear_expression] | None:
        """Total power balance: connection_power + element_power == 0."""
        ep = self.element_power()
        if ep is None:
            return None
        return list(self.connection_power() + ep == 0)
