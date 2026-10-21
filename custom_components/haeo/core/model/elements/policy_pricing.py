"""Policy pricing element for reactive policy cost updates.

A PolicyPricing element applies a single tracked price to one or more
connection/tag power flow terms (from connections on the min-cut).
Updating the price triggers reactive cost invalidation so the next
optimization picks up the new value without rebuilding the network.
"""

from collections.abc import Mapping
from typing import Final, Literal, NotRequired, Protocol, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import LinearArray, total
from custom_components.haeo.core.model.reactive import TrackedParam, cost
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .connection import Connection

type PolicyPricingElementTypeName = Literal["policy_pricing"]
ELEMENT_TYPE: Final[PolicyPricingElementTypeName] = "policy_pricing"

POLICY_PRICING_OUTPUT_NAMES: Final[frozenset[str]] = frozenset()


class MeasuredFlows(Protocol):
    """A connection's per-tag power at its measured point, which a policy price applies to."""

    @property
    def measured_power(self) -> dict[int, LinearArray]:
        """Per-tag power at the measured point."""
        ...


class PolicyPricingTerm(TypedDict):
    """A single connection+tag reference for pricing placement."""

    connection: str
    tag: int


class PolicyPricingElementConfig(TypedDict):
    """Configuration for creating a PolicyPricing model element."""

    element_type: PolicyPricingElementTypeName
    name: str
    label: NotRequired[str]
    price: float | NDArray[np.float64]
    terms: list[PolicyPricingTerm]


def policy_pricing_arguments(config: PolicyPricingElementConfig, elements: Mapping[str, object]) -> dict[str, object]:
    """Return a policy pricing's constructor arguments, with each term resolved to the connection it prices."""
    name = config["name"]
    priced_flows: list[tuple[MeasuredFlows, int]] = []
    for term in config["terms"]:
        connection_name = term["connection"]
        tag = term["tag"]
        connection = elements.get(connection_name)
        if not isinstance(connection, Connection):
            msg = f"PolicyPricing '{name}' references unknown connection '{connection_name}'"
            raise TypeError(msg)
        if tag not in connection.measured_power:
            msg = f"PolicyPricing '{name}' references tag {tag} not on connection '{connection_name}'"
            raise ValueError(msg)
        priced_flows.append((connection, tag))
    return {
        "price": config["price"],
        "priced_flows": priced_flows,
        "terms": config["terms"],
        "label": config.get("label", ""),
    }


class PolicyPricing(Element[str]):
    """Policy pricing with reactive price updates.

    Each PolicyPricing element applies a tracked price to one or more
    per-tag power flow terms and computes a cost from their product.
    Multiple elements can price the same or different connections/tags;
    their costs are summed by the network.
    """

    price: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        price: float | NDArray[np.float64],
        priced_flows: list[tuple[MeasuredFlows, int]],
        terms: list[PolicyPricingTerm] | None = None,
        label: str = "",
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
        self.label = label

    @cost
    def pricing_cost(self) -> LinearArray | None:
        """Compute the pricing cost for this policy rule placement."""
        price = self.price
        return total([connection.measured_power[tag] * price * self.periods for connection, tag in self._priced_flows])
