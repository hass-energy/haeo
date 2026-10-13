"""SOC-based pricing segment — penalizes operation outside SOC thresholds."""

from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; segments only use these via hasattr/isinstance duck typing.
    Literal,
    NotRequired,
    Protocol,
    runtime_checkable,
)

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import LinearArray, Rows, total
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import FlowProvider, Segment


@runtime_checkable
class _BatteryLike(Protocol):
    """Structural type for the battery endpoint SocPricingSegment penalizes.

    Avoids importing Battery directly (elements/battery.py sits alongside this module and
    importing it here would invert the intended dependency direction); duck-typed instead.
    """

    stored_energy: LinearArray


class SocPricingSegmentSpec(TypedDict):
    """Specification for creating a SocPricingSegment."""

    segment_type: Literal["soc_pricing"]
    discharge_energy_threshold: NotRequired[NDArray[np.float64] | float | None]
    charge_capacity_threshold: NotRequired[NDArray[np.float64] | float | None]
    discharge_energy_price: NotRequired[NDArray[np.float64] | float | None]
    charge_capacity_price: NotRequired[NDArray[np.float64] | float | None]


def _exposed_slack(
    threshold: NDArray[np.float64] | None,
    price: NDArray[np.float64] | None,
    slack: LinearArray,
) -> LinearArray | None:
    return slack if threshold is not None and price is not None else None


class SocPricingSegment(Segment):
    """Penalizes battery operation outside SOC thresholds using slack variables."""

    discharge_energy_threshold: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    charge_capacity_threshold: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    discharge_energy_price: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    charge_capacity_price: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Solver,
        *,
        spec: SocPricingSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize SOC pricing segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            upstream=upstream,
        )
        self._battery = self._get_battery()

        self.discharge_energy_threshold = broadcast_to_sequence(spec.get("discharge_energy_threshold"), n_periods)
        self.charge_capacity_threshold = broadcast_to_sequence(spec.get("charge_capacity_threshold"), n_periods)
        self.discharge_energy_price = broadcast_to_sequence(spec.get("discharge_energy_price"), n_periods)
        self.charge_capacity_price = broadcast_to_sequence(spec.get("charge_capacity_price"), n_periods)

        if self.discharge_energy_price is not None and self.discharge_energy_threshold is None:
            msg = "discharge_energy_threshold is required when discharge_energy_price is set"
            raise ValueError(msg)
        if self.charge_capacity_price is not None and self.charge_capacity_threshold is None:
            msg = "charge_capacity_threshold is required when charge_capacity_price is set"
            raise ValueError(msg)

        self._discharge_energy_slack = solver.add_variables(n_periods)
        self._charge_capacity_slack = solver.add_variables(n_periods)

    def _get_battery(self) -> _BatteryLike:
        """Find the battery element from the connection endpoints."""
        for element in (self.source_element, self.target_element):
            if isinstance(element, _BatteryLike):
                return element
        msg = "SOC pricing segment requires a battery element endpoint"
        raise TypeError(msg)

    @property
    def discharge_energy_slack(self) -> LinearArray | None:
        """Slack for energy below discharge threshold."""
        return _exposed_slack(
            self.discharge_energy_threshold,
            self.discharge_energy_price,
            self._discharge_energy_slack,
        )

    @property
    def charge_capacity_slack(self) -> LinearArray | None:
        """Slack for energy above charge capacity threshold."""
        return _exposed_slack(
            self.charge_capacity_threshold,
            self.charge_capacity_price,
            self._charge_capacity_slack,
        )

    @constraint
    def soc_slack_bounds(self) -> Rows:
        """Bound slack variables to SOC threshold violations when penalties apply.

        Both sides always have rows. A side without a priced threshold has free
        rows, so it can be priced later without changing the LP's shape.
        """
        stored = self._battery.stored_energy[1:]
        below = self._discharge_energy_slack + stored
        above = self._charge_capacity_slack - stored

        if self.discharge_energy_threshold is not None and self.discharge_energy_price is not None:
            below_rows = below >= self.discharge_energy_threshold
        else:
            below_rows = below.free()

        if self.charge_capacity_threshold is not None and self.charge_capacity_price is not None:
            above_rows = above >= -self.charge_capacity_threshold
        else:
            above_rows = above.free()

        return Rows.concat([below_rows, above_rows])

    @cost
    def soc_pricing_cost(self) -> LinearArray | None:
        """Penalty cost for operating outside SOC thresholds."""
        cost_terms: list[LinearArray] = []
        if self.discharge_energy_price is not None and self.discharge_energy_threshold is not None:
            cost_terms.append(self._discharge_energy_slack * self.discharge_energy_price * self.periods)
        if self.charge_capacity_price is not None and self.charge_capacity_threshold is not None:
            cost_terms.append(self._charge_capacity_slack * self.charge_capacity_price * self.periods)
        return total(cost_terms)


__all__ = ["SocPricingSegment", "SocPricingSegmentSpec"]
