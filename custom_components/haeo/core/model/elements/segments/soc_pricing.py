"""SOC-based pricing segment — identity transform with slack variable penalties."""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import constraint, cost
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment, TagPowerMap


class SocPricingSegmentSpec(TypedDict):
    segment_type: Literal["soc_pricing"]
    discharge_energy_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    charge_capacity_threshold: NotRequired[NDArray[np.floating[Any]] | float | None]
    discharge_energy_price: NotRequired[NDArray[np.floating[Any]] | float | None]
    charge_capacity_price: NotRequired[NDArray[np.floating[Any]] | float | None]


class SocPricingSegment(Segment):
    """Identity transform with slack variables for SOC penalty computation."""

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
        super().__init__(
            segment_id, n_periods, periods, solver, source_element=source_element, target_element=target_element
        )
        self._battery = self._get_battery()

        self._discharge_energy_threshold = broadcast_to_sequence(spec.get("discharge_energy_threshold"), n_periods)
        self._charge_capacity_threshold = broadcast_to_sequence(spec.get("charge_capacity_threshold"), n_periods)
        self._discharge_energy_price = broadcast_to_sequence(spec.get("discharge_energy_price"), n_periods)
        self._charge_capacity_price = broadcast_to_sequence(spec.get("charge_capacity_price"), n_periods)

        self._discharge_energy_slack: HighspyArray | None = None
        if self._discharge_energy_price is not None:
            if self._discharge_energy_threshold is None:
                msg = "discharge_energy_threshold is required when discharge_energy_price is set"
                raise ValueError(msg)
            self._discharge_energy_slack = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_discharge_energy_", out_array=True
            )

        self._charge_capacity_slack: HighspyArray | None = None
        if self._charge_capacity_price is not None:
            if self._charge_capacity_threshold is None:
                msg = "charge_capacity_threshold is required when charge_capacity_price is set"
                raise ValueError(msg)
            self._charge_capacity_slack = solver.addVariables(
                n_periods, lb=0, name_prefix=f"{segment_id}_charge_capacity_", out_array=True
            )

    def _get_battery(self) -> Any:
        for element in (self.source_element, self.target_element):
            if hasattr(element, "stored_energy"):
                return element
        msg = "SOC pricing segment requires a battery element endpoint"
        raise TypeError(msg)

    @property
    def discharge_energy_slack(self) -> HighspyArray | None:
        return self._discharge_energy_slack

    @property
    def charge_capacity_slack(self) -> HighspyArray | None:
        return self._charge_capacity_slack

    def apply(self, power_st: TagPowerMap, power_ts: TagPowerMap) -> tuple[TagPowerMap, TagPowerMap]:
        self._power_in_st = self._power_out_st = power_st
        self._power_in_ts = self._power_out_ts = power_ts
        return power_st, power_ts

    @constraint
    def discharge_energy_slack_bound(self) -> list[highs_linear_expression] | None:
        if self._discharge_energy_slack is None or self._discharge_energy_threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._discharge_energy_slack >= self._discharge_energy_threshold - stored_energy[1:])

    @constraint
    def charge_capacity_slack_bound(self) -> list[highs_linear_expression] | None:
        if self._charge_capacity_slack is None or self._charge_capacity_threshold is None:
            return None
        stored_energy = np.asarray(self._battery.stored_energy, dtype=object)
        return list(self._charge_capacity_slack >= stored_energy[1:] - self._charge_capacity_threshold)

    @cost
    def soc_pricing_cost(self) -> highs_linear_expression | None:
        cost_terms = []
        if self._discharge_energy_slack is not None and self._discharge_energy_price is not None:
            cost_terms.append(Highs.qsum(self._discharge_energy_slack * self._discharge_energy_price))
        if self._charge_capacity_slack is not None and self._charge_capacity_price is not None:
            cost_terms.append(Highs.qsum(self._charge_capacity_slack * self._charge_capacity_price))
        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)


__all__ = ["SocPricingSegment", "SocPricingSegmentSpec"]
