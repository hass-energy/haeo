"""SOC-based pricing segment — penalizes operation outside SOC thresholds."""

from typing import Any, Literal, NotRequired

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
    discharge_energy_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    charge_capacity_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    discharge_energy_price: NotRequired[NDArray[np.floating[Any]] | float | None]
    charge_capacity_price: NotRequired[NDArray[np.floating[Any]] | float | None]


class SocPricingSegment(Segment):
    """Penalizes battery operation outside SOC thresholds using slack variables.

    All four spec fields are exposed as :class:`TrackedParam` descriptors so
    that the coordinator's ``ElementUpdater`` can write fresh values through
    on subsequent optimizations.  Slack variables are always created so that
    constraint/cost expressions stay structurally stable even when a price
    transitions between ``None`` and a numeric value across runs.
    """

    # Parameters exposed for TrackedParam-based updates from the coordinator.
    discharge_energy_threshold: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    charge_capacity_threshold: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    discharge_energy_price: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    charge_capacity_price: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
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

        # Preserve the historical guard: a price without a corresponding
        # threshold has no meaning and indicates a config bug.
        if self.discharge_energy_price is not None and self.discharge_energy_threshold is None:
            msg = "discharge_energy_threshold is required when discharge_energy_price is set"
            raise ValueError(msg)
        if self.charge_capacity_price is not None and self.charge_capacity_threshold is None:
            msg = "charge_capacity_threshold is required when charge_capacity_price is set"
            raise ValueError(msg)

        # Always create slack variables so that the LP structure remains
        # stable across runs even if a price transitions between ``None`` and
        # a numeric value.  When the corresponding price/threshold is absent
        # the slack is left unconstrained at zero (lb=0) and contributes
        # nothing to the cost.
        self._discharge_energy_slack: HighspyArray = solver.addVariables(
            n_periods,
            lb=0,
            name_prefix=f"{segment_id}_discharge_energy_",
            out_array=True,
        )

        self._charge_capacity_slack: HighspyArray = solver.addVariables(
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
        if self.discharge_energy_price is None or self.discharge_energy_threshold is None:
            return None
        return self._discharge_energy_slack

    @property
    def charge_capacity_slack(self) -> HighspyArray | None:
        """Slack for energy above charge capacity threshold."""
        if self.charge_capacity_price is None or self.charge_capacity_threshold is None:
            return None
        return self._charge_capacity_slack

    @constraint
    def discharge_energy_slack_bound(self) -> list[highs_linear_expression] | None:
        """Bound discharge slack to threshold violation.

        Only emits a constraint when both the threshold and price are set;
        otherwise the slack stays free (and zero, since lb=0 and no cost).
        """
        if self.discharge_energy_threshold is None or self.discharge_energy_price is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._discharge_energy_slack >= self.discharge_energy_threshold - stored_energy[1:])

    @constraint
    def charge_capacity_slack_bound(self) -> list[highs_linear_expression] | None:
        """Bound charge slack to threshold violation.

        Only emits a constraint when both the threshold and price are set;
        otherwise the slack stays free (and zero, since lb=0 and no cost).
        """
        if self.charge_capacity_threshold is None or self.charge_capacity_price is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._charge_capacity_slack >= stored_energy[1:] - self.charge_capacity_threshold)

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
