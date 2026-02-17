"""SOC pricing segment with inventory and optional movement costs."""

from typing import Any, Final, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import constraint, cost
from custom_components.haeo.model.util import broadcast_to_sequence

from .segment import Segment

SLACK_REGULARIZATION: Final = 1e-5


class SocPricingSegmentSpec(TypedDict):
    """Specification for creating a SocPricingSegment."""

    segment_type: Literal["soc_pricing"]
    threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    discharge_violation_price: NotRequired[NDArray[np.floating[Any]] | float | None]
    charge_violation_price: NotRequired[NDArray[np.floating[Any]] | float | None]
    discharge_movement_price: NotRequired[NDArray[np.floating[Any]] | float | None]
    charge_movement_price: NotRequired[NDArray[np.floating[Any]] | float | None]


class SocPricingSegment(Segment):
    """Segment that prices SOC threshold violations and optional movement."""

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

        self._threshold = broadcast_to_sequence(spec.get("threshold"), n_periods)
        self._discharge_violation_price = broadcast_to_sequence(spec.get("discharge_violation_price"), n_periods)
        self._charge_violation_price = broadcast_to_sequence(spec.get("charge_violation_price"), n_periods)
        self._discharge_movement_price = broadcast_to_sequence(spec.get("discharge_movement_price"), n_periods)
        self._charge_movement_price = broadcast_to_sequence(spec.get("charge_movement_price"), n_periods)

        self._validate_configuration()

        self._below_slack: HighspyArray | None = None
        if self._discharge_violation_price is not None or self._discharge_movement_price is not None:
            self._below_slack = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_below_", out_array=True)

        self._above_slack: HighspyArray | None = None
        if self._charge_violation_price is not None or self._charge_movement_price is not None:
            self._above_slack = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_above_", out_array=True)

        self._below_enter: HighspyArray | None = None
        self._below_recover: HighspyArray | None = None
        if self._below_slack is not None and (
            self._discharge_movement_price is not None or self._charge_movement_price is not None
        ):
            self._below_enter = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_below_enter_", out_array=True
            )
            self._below_recover = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_below_recover_", out_array=True
            )

        self._above_enter: HighspyArray | None = None
        self._above_recover: HighspyArray | None = None
        if self._above_slack is not None and (
            self._charge_movement_price is not None or self._discharge_movement_price is not None
        ):
            self._above_enter = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_above_enter_", out_array=True
            )
            self._above_recover = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_above_recover_", out_array=True
            )

    def _get_battery(self) -> Any:
        for element in (self.source_element, self.target_element):
            if hasattr(element, "stored_energy"):
                return element
        msg = "SOC pricing segment requires a battery element endpoint"
        raise TypeError(msg)

    def _validate_configuration(self) -> None:
        has_below_config = self._discharge_violation_price is not None or self._discharge_movement_price is not None
        has_above_config = self._charge_violation_price is not None or self._charge_movement_price is not None
        if (has_below_config or has_above_config) and self._threshold is None:
            msg = "threshold is required when SOC pricing is configured"
            raise ValueError(msg)

    @property
    def below_slack(self) -> HighspyArray | None:
        """Return slack for energy below threshold."""
        return self._below_slack

    @property
    def above_slack(self) -> HighspyArray | None:
        """Return slack for energy above threshold."""
        return self._above_slack

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
    def below_slack_bound(self) -> list[highs_linear_expression] | None:
        """Slack constraint for energy below threshold."""
        if self._below_slack is None or self._threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._below_slack >= self._threshold - stored_energy[1:])

    @constraint
    def above_slack_bound(self) -> list[highs_linear_expression] | None:
        """Slack constraint for energy above threshold."""
        if self._above_slack is None or self._threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._above_slack >= stored_energy[1:] - self._threshold)

    @constraint
    def below_delta_balance(self) -> list[highs_linear_expression] | None:
        """Decompose below-slack deltas into enter/recover movement."""
        if self._below_slack is None or self._below_enter is None or self._below_recover is None:
            return None
        constraints: list[highs_linear_expression] = [
            self._below_enter[0] - self._below_recover[0] == self._below_slack[0]
        ]
        constraints.extend(
            list(self._below_enter[1:] - self._below_recover[1:] == self._below_slack[1:] - self._below_slack[:-1])
        )
        return constraints

    @constraint
    def above_delta_balance(self) -> list[highs_linear_expression] | None:
        """Decompose above-slack deltas into enter/recover movement."""
        if self._above_slack is None or self._above_enter is None or self._above_recover is None:
            return None
        constraints: list[highs_linear_expression] = [
            self._above_enter[0] - self._above_recover[0] == self._above_slack[0]
        ]
        constraints.extend(
            list(self._above_enter[1:] - self._above_recover[1:] == self._above_slack[1:] - self._above_slack[:-1])
        )
        return constraints

    @cost
    def soc_pricing_cost(self) -> highs_linear_expression | None:
        """Return cost contribution from SOC pricing."""
        cost_terms: list[highs_linear_expression] = []
        if self._below_slack is not None and self._discharge_violation_price is not None:
            cost_terms.append(Highs.qsum(self._below_slack * self._discharge_violation_price))
        if self._above_slack is not None and self._charge_violation_price is not None:
            cost_terms.append(Highs.qsum(self._above_slack * self._charge_violation_price))

        has_movement = False
        if self._below_enter is not None and self._discharge_movement_price is not None:
            cost_terms.append(Highs.qsum(self._below_enter * self._discharge_movement_price))
            has_movement = True
        if self._below_recover is not None and self._charge_movement_price is not None:
            cost_terms.append(Highs.qsum(self._below_recover * self._charge_movement_price))
            has_movement = True
        if self._above_enter is not None and self._charge_movement_price is not None:
            cost_terms.append(Highs.qsum(self._above_enter * self._charge_movement_price))
            has_movement = True
        if self._above_recover is not None and self._discharge_movement_price is not None:
            cost_terms.append(Highs.qsum(self._above_recover * self._discharge_movement_price))
            has_movement = True

        if has_movement:
            # Keep slacks tight when movement pricing is enabled.
            if self._below_slack is not None:
                cost_terms.append(SLACK_REGULARIZATION * Highs.qsum(self._below_slack))
            if self._above_slack is not None:
                cost_terms.append(SLACK_REGULARIZATION * Highs.qsum(self._above_slack))

        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)


__all__ = ["SocPricingSegment", "SocPricingSegmentSpec"]
