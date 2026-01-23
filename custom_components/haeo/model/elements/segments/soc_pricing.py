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
    undercharge_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    overcharge_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    undercharge_price: NotRequired[NDArray[np.floating[Any]] | float | None]
    overcharge_price: NotRequired[NDArray[np.floating[Any]] | float | None]


class SocPricingSegment(Segment):
    """Segment that penalizes battery SOC outside configured thresholds."""

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

        self._undercharge_threshold = broadcast_to_sequence(spec.get("undercharge_threshold"), n_periods)
        self._overcharge_threshold = broadcast_to_sequence(spec.get("overcharge_threshold"), n_periods)
        self._undercharge_price = broadcast_to_sequence(spec.get("undercharge_price"), n_periods)
        self._overcharge_price = broadcast_to_sequence(spec.get("overcharge_price"), n_periods)

        self._undercharge_slack: HighspyArray | None = None
        if self._undercharge_price is not None:
            if self._undercharge_threshold is None:
                msg = "undercharge_threshold is required when undercharge_price is set"
                raise ValueError(msg)
            self._undercharge_slack = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_undercharge_", out_array=True
            )

        self._overcharge_slack: HighspyArray | None = None
        if self._overcharge_price is not None:
            if self._overcharge_threshold is None:
                msg = "overcharge_threshold is required when overcharge_price is set"
                raise ValueError(msg)
            self._overcharge_slack = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_overcharge_", out_array=True
            )

    def _get_battery(self) -> Any:
        for element in (self.source_element, self.target_element):
            if hasattr(element, "stored_energy"):
                return element
        msg = "SOC pricing segment requires a battery element endpoint"
        raise TypeError(msg)

    @property
    def undercharge_slack(self) -> HighspyArray | None:
        """Return slack for energy below undercharge threshold."""
        return self._undercharge_slack

    @property
    def overcharge_slack(self) -> HighspyArray | None:
        """Return slack for energy above overcharge threshold."""
        return self._overcharge_slack

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
    def undercharge_slack_bound(self) -> list[highs_linear_expression] | None:
        """Slack constraint for energy below undercharge threshold."""
        if self._undercharge_slack is None or self._undercharge_threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._undercharge_slack >= self._undercharge_threshold - stored_energy[1:])

    @constraint
    def overcharge_slack_bound(self) -> list[highs_linear_expression] | None:
        """Slack constraint for energy above overcharge threshold."""
        if self._overcharge_slack is None or self._overcharge_threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._overcharge_slack >= stored_energy[1:] - self._overcharge_threshold)

    @cost
    def soc_pricing_cost(self) -> highs_linear_expression | None:
        """Return cost contribution from SOC pricing."""
        cost_terms = []
        if self._undercharge_slack is not None and self._undercharge_price is not None:
            cost_terms.append(Highs.qsum(self._undercharge_slack * self._undercharge_price))
        if self._overcharge_slack is not None and self._overcharge_price is not None:
            cost_terms.append(Highs.qsum(self._overcharge_slack * self._overcharge_price))
        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)


__all__ = ["SocPricingSegment", "SocPricingSegmentSpec"]
