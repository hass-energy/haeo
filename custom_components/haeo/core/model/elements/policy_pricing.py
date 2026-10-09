"""Policy pricing element for reactive policy cost updates.

A PolicyPricing element applies a single tracked price to one or more
connection/tag power flow terms (from connections on the min-cut).
Updating the price triggers reactive cost invalidation so the next
optimization picks up the new value without rebuilding the network.
"""

from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, cost
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .connection import Connection

type PolicyPricingElementTypeName = Literal["policy_pricing"]
ELEMENT_TYPE: Final[PolicyPricingElementTypeName] = "policy_pricing"

POLICY_PRICING_OUTPUT_NAMES: Final[frozenset[str]] = frozenset()


class PolicyPricingTerm(TypedDict):
    """A single connection+tag reference for pricing placement."""

    connection: str
    tag: int


class PolicyPricingElementConfig(TypedDict):
    """Configuration for creating a PolicyPricing model element."""

    element_type: PolicyPricingElementTypeName
    name: str
    label: NotRequired[str]
    price: float | NDArray[np.floating[Any]]
    terms: list[PolicyPricingTerm]


class PolicyPricing(Element[str]):
    """Policy pricing with reactive price updates.

    Each PolicyPricing element applies a tracked price to one or more
    per-tag power flow terms and computes a cost from their product.
    Multiple elements can price the same or different connections/tags;
    their costs are summed by the network.
    """

    price: TrackedParam[NDArray[np.floating[Any]]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        price: float | NDArray[np.floating[Any]],
        priced_flows: list[tuple[Connection[Any], int]],
        terms: list[PolicyPricingTerm] | None = None,
    ) -> None:
        """Initialize with a price and the connection tags it applies to.

        Each tag's power is read at the connection's measured point when the cost
        is built, so a flow shaped by the connection's efficiency follows changes to it.
        """
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=POLICY_PRICING_OUTPUT_NAMES,
        )
        self.price = broadcast_to_sequence(price, self.n_periods)
        self._priced_flows = priced_flows
        self.terms = terms or []
        self.label: str = ""

    @cost
    def pricing_cost(self) -> highs_linear_expression | None:
        """Compute the pricing cost for this policy rule placement."""
        price = self.price
        costs = [
            Highs.qsum(connection.measured_power[tag] * price * self.periods) for connection, tag in self._priced_flows
        ]
        return costs[0] if len(costs) == 1 else Highs.qsum(costs)
