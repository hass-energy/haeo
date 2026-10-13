"""Holding cost element for pricing stored energy beyond a threshold.

A HoldingCost element charges a rate for every kWh a battery holds above or
below a threshold, for every hour it stays there. Like policy pricing, it adds
cost without taking part in the power balance, and it reads the stored energy
of the battery it references rather than owning any of its own.
"""

from typing import Final, Literal, Protocol, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost
from custom_components.haeo.core.model.util import broadcast_to_sequence

type HoldingCostElementTypeName = Literal["holding_cost"]
ELEMENT_TYPE: Final[HoldingCostElementTypeName] = "holding_cost"

type HoldingCostDirection = Literal["above", "below"]

HOLDING_COST_OUTPUT_NAMES: Final[frozenset[str]] = frozenset()


class StoredEnergy(Protocol):
    """An element whose stored energy a holding cost applies to."""

    stored_energy: HighspyArray


class HoldingCostElementConfig(TypedDict):
    """Configuration for creating a HoldingCost model element.

    ``threshold`` is the stored energy (kWh) at the end of each period that the
    cost is measured from, and ``price`` is the holding cost rate ($/kWh/h).
    """

    element_type: HoldingCostElementTypeName
    name: str
    storage: str
    direction: HoldingCostDirection
    threshold: NDArray[np.float64] | float
    price: NDArray[np.float64] | float


class HoldingCost(Element[str]):
    """Holding cost on the energy a battery stores beyond a threshold.

    The excess is a non-negative slack per period, bounded below by how far the
    stored energy at the end of the period is past the threshold in the configured
    direction. Minimizing cost drives the slack down onto that distance, so the
    cost is the rate times the excess times the period length.
    """

    threshold: TrackedParam[NDArray[np.float64]] = TrackedParam()
    price: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Highs,
        storage: StoredEnergy,
        direction: HoldingCostDirection,
        threshold: NDArray[np.float64] | float,
        price: NDArray[np.float64] | float,
    ) -> None:
        """Initialize a holding cost on the stored energy of a battery."""
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=HOLDING_COST_OUTPUT_NAMES,
        )
        self._storage = storage
        self.direction: HoldingCostDirection = direction
        self.threshold = broadcast_to_sequence(threshold, self.n_periods)
        self.price = broadcast_to_sequence(price, self.n_periods)
        self.excess = solver.addVariables(self.n_periods, lb=0.0, name_prefix=f"{name}_excess_", out_array=True)

    @constraint
    def holding_cost_excess(self) -> list[highs_linear_expression]:
        """Constraint: the excess is at least how far stored energy is past the threshold.

        Below: excess >= threshold - stored_energy.
        Above: excess >= stored_energy - threshold.
        """
        stored = np.asarray(self._storage.stored_energy, dtype=object)[1:]
        if self.direction == "below":
            return list(self.excess + stored >= self.threshold)
        return list(self.excess - stored >= -self.threshold)

    @cost
    def holding_cost(self) -> highs_linear_expression:
        """Cost: the holding rate for each kWh past the threshold, for each hour it stays there."""
        return Highs.qsum(self.excess * self.price * self.periods)


__all__ = [
    "ELEMENT_TYPE",
    "HOLDING_COST_OUTPUT_NAMES",
    "HoldingCost",
    "HoldingCostDirection",
    "HoldingCostElementConfig",
    "HoldingCostElementTypeName",
    "StoredEnergy",
]
