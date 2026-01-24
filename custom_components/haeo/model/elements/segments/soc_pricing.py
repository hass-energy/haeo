"""SOC-based pricing segment for battery level penalties."""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import constraint, cost
from custom_components.haeo.model.util import broadcast_to_sequence

from .segment import Segment


class SocPricingSegmentSpec(TypedDict):
    """Specification for creating a SocPricingSegment."""

    segment_type: Literal["soc_pricing"]
    lower_energy_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    upper_energy_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    lower_energy_price: NotRequired[NDArray[np.floating[Any]] | float | None]
    upper_energy_price: NotRequired[NDArray[np.floating[Any]] | float | None]


class SocPricingSegment(Segment):
    """Segment that penalizes stored energy outside configured thresholds."""

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
    ) -> None:
        """Initialize SOC pricing segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
        )
        self._battery = self._get_battery()

        # Power variables (lossless segment, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        self._lower_energy_threshold = broadcast_to_sequence(spec.get("lower_energy_threshold"), n_periods)
        self._upper_energy_threshold = broadcast_to_sequence(spec.get("upper_energy_threshold"), n_periods)
        self._lower_energy_price = broadcast_to_sequence(spec.get("lower_energy_price"), n_periods)
        self._upper_energy_price = broadcast_to_sequence(spec.get("upper_energy_price"), n_periods)

        self._lower_energy_slack: HighspyArray | None = None
        if self._lower_energy_price is not None:
            if self._lower_energy_threshold is None:
                msg = "lower_energy_threshold is required when lower_energy_price is set"
                raise ValueError(msg)
            self._lower_energy_slack = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_lower_energy_", out_array=True
            )

        self._upper_energy_slack: HighspyArray | None = None
        if self._upper_energy_price is not None:
            if self._upper_energy_threshold is None:
                msg = "upper_energy_threshold is required when upper_energy_price is set"
                raise ValueError(msg)
            self._upper_energy_slack = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_upper_energy_", out_array=True
            )

    def _get_battery(self) -> Any:
        for element in (self.source_element, self.target_element):
            if hasattr(element, "stored_energy"):
                return element
        msg = "SOC pricing segment requires a battery element endpoint"
        raise TypeError(msg)

    @property
    def lower_energy_slack(self) -> HighspyArray | None:
        """Return slack for energy below lower threshold."""
        return self._lower_energy_slack

    @property
    def upper_energy_slack(self) -> HighspyArray | None:
        """Return slack for energy above upper threshold."""
        return self._upper_energy_slack

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_st

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction (lossless)."""
        return self._power_st

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_ts

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction (lossless)."""
        return self._power_ts

    @constraint
    def lower_energy_slack_bound(self) -> list[highs_linear_expression] | None:
        """Slack constraint for energy below lower threshold."""
        if self._lower_energy_slack is None or self._lower_energy_threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._lower_energy_slack >= self._lower_energy_threshold - stored_energy[1:])

    @constraint
    def upper_energy_slack_bound(self) -> list[highs_linear_expression] | None:
        """Slack constraint for energy above upper threshold."""
        if self._upper_energy_slack is None or self._upper_energy_threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._upper_energy_slack >= stored_energy[1:] - self._upper_energy_threshold)

    @cost
    def soc_pricing_cost(self) -> highs_linear_expression | None:
        """Return cost contribution from SOC pricing."""
        cost_terms = []
        if self._lower_energy_slack is not None and self._lower_energy_price is not None:
            cost_terms.append(Highs.qsum(self._lower_energy_slack * self._lower_energy_price))
        if self._upper_energy_slack is not None and self._upper_energy_price is not None:
            cost_terms.append(Highs.qsum(self._upper_energy_slack * self._upper_energy_price))
        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)


__all__ = ["SocPricingSegment", "SocPricingSegmentSpec"]
