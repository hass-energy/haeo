"""SOC-based pricing segment — penalizes operation outside SOC thresholds."""

from typing import Any, Literal, NotRequired  # noqa: TID251  # legacy Any usage; migrate to precise types

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment


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
    slack: HighspyArray,
) -> HighspyArray | None:
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
        solver: Highs,
        *,
        spec: SocPricingSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        power_in: dict[int, HighspyArray],
    ) -> None:
        """Initialize SOC pricing segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            power_in=power_in,
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

        self._discharge_energy_slack = solver.addVariables(
            n_periods,
            lb=0,
            name_prefix=f"{segment_id}_discharge_energy_",
            out_array=True,
        )
        self._charge_capacity_slack = solver.addVariables(
            n_periods,
            lb=0,
            name_prefix=f"{segment_id}_charge_capacity_",
            out_array=True,
        )

    def _get_battery(self) -> Any:
        """Find the battery element from the connection endpoints."""
        for element in (self.source_element, self.target_element):
            if hasattr(element, "stored_energy"):
                return element
        msg = "SOC pricing segment requires a battery element endpoint"
        raise TypeError(msg)

    @property
    def discharge_energy_slack(self) -> HighspyArray | None:
        """Slack for energy below discharge threshold."""
        return _exposed_slack(
            self.discharge_energy_threshold,
            self.discharge_energy_price,
            self._discharge_energy_slack,
        )

    @property
    def charge_capacity_slack(self) -> HighspyArray | None:
        """Slack for energy above charge capacity threshold."""
        return _exposed_slack(
            self.charge_capacity_threshold,
            self.charge_capacity_price,
            self._charge_capacity_slack,
        )

    @constraint
    def soc_slack_bounds(self) -> list[highs_linear_expression] | None:
        """Bound slack variables to SOC threshold violations when penalties apply."""
        bounds: list[highs_linear_expression] = []
        stored = np.asarray(self._battery.stored_energy, dtype=object)[1:]

        if self.discharge_energy_threshold is not None and self.discharge_energy_price is not None:
            bounds.extend(list(self._discharge_energy_slack >= self.discharge_energy_threshold - stored))

        if self.charge_capacity_threshold is not None and self.charge_capacity_price is not None:
            bounds.extend(list(self._charge_capacity_slack >= stored - self.charge_capacity_threshold))

        return bounds or None

    @cost
    def soc_pricing_cost(self) -> highs_linear_expression | None:
        """Penalty cost for operating outside SOC thresholds."""
        cost_terms = []
        if self.discharge_energy_price is not None and self.discharge_energy_threshold is not None:
            cost_terms.append(Highs.qsum(self._discharge_energy_slack * self.discharge_energy_price * self.periods))
        if self.charge_capacity_price is not None and self.charge_capacity_threshold is not None:
            cost_terms.append(Highs.qsum(self._charge_capacity_slack * self.charge_capacity_price * self.periods))
        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)


__all__ = ["SocPricingSegment", "SocPricingSegmentSpec"]
