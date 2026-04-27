"""Policy pricing element for reactive policy cost updates.

A PolicyPricing element applies a single tracked price to one or more
connection/tag power flow terms (from connections on the min-cut).
Updating the price triggers reactive cost invalidation so the next
optimization picks up the new value without rebuilding the network.
"""

from typing import Any, Final, Literal, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, cost
from custom_components.haeo.core.model.util import broadcast_to_sequence

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
        power_terms: list[HighspyArray],
        terms: list[PolicyPricingTerm] | None = None,
    ) -> None:
        """Initialize with price and LP power flow variables."""
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=POLICY_PRICING_OUTPUT_NAMES,
        )
        self.price = broadcast_to_sequence(price, self.n_periods)
        self._power_terms = power_terms
        self.terms = terms or []

    @cost
    def pricing_cost(self) -> highs_linear_expression | None:
        """Compute the pricing cost for this policy rule placement."""
        price = self.price
        costs = [Highs.qsum(pt * price * self.periods) for pt in self._power_terms]
        return costs[0] if len(costs) == 1 else Highs.qsum(costs)
