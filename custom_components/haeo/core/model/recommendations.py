"""Connection control recommendations from LP ranging.

Uses HiGHS column ranging on connection power_in variables to derive
hardware control signals: whether a device should be unlimited or
capped, and the safe operating band.

Decision rule:
  - bup ≥ UB (forecast max) AND RC ≤ 0 → UNLIMIT
  - Otherwise → SET limit to bup
  - Band [bdn, bup] is the flexibility range at same cost

Special case: UB = 0 (zero forecast) → no model information,
recommendation is "unknown" (adapter decides based on context).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from highspy import Highs


class RecommendationType(StrEnum):
    """Type of control recommendation."""

    UNLIMIT = "unlimit"
    """Hardware can run free — any output up to physical max is acceptable."""

    SET = "set"
    """Hardware should be actively limited to the recommended value."""

    UNKNOWN = "unknown"
    """Zero forecast — model has no information, adapter should decide."""


@dataclass(frozen=True)
class ControlRecommendation:
    """Per-period control recommendation for a connection variable."""

    type: RecommendationType
    """Whether to unlimit, set a limit, or unknown."""

    optimal: float
    """The LP-optimal value (kW)."""

    limit: float | None
    """Recommended limit (kW). None for UNLIMIT/UNKNOWN."""

    band_min: float
    """Lower end of safe operating band (kW)."""

    band_max: float
    """Upper end of safe operating band (kW)."""

    reduced_cost: float
    """Marginal cost gradient ($/kWh). >0 = lower is better, <0 = higher is better."""

    forecast_max: float
    """The forecast/physical upper bound (kW)."""


def compute_recommendations(
    solver: Highs,
    variables: Sequence[object],
    forecast_max: Sequence[float],
    periods: Sequence[float],
    *,
    tolerance: float = 0.01,
) -> list[ControlRecommendation]:
    """Compute per-period control recommendations from LP ranging.

    Args:
        solver: HiGHS solver instance (post-solve).
        variables: Per-period power_in variables (must have .index).
        forecast_max: Per-period forecast upper bound (kW).
        periods: Per-period duration (hours).
        tolerance: Numerical tolerance for comparisons.

    Returns:
        List of ControlRecommendation, one per period.

    """
    sol = solver.getSolution()
    _status, rng = solver.getRanging()

    recommendations: list[ControlRecommendation] = []
    for t, var in enumerate(variables):
        idx = var.index  # type: ignore[union-attr]
        val = sol.col_value[idx]
        rc = sol.col_dual[idx]
        bdn = rng.col_bound_dn.value_[idx]
        bup = rng.col_bound_up.value_[idx]
        ub = forecast_max[t]
        dt = periods[t]

        # Convert RC from objective units to $/kWh
        rc_kwh = rc / dt if dt > 0 else 0.0

        band_min = max(0.0, bdn)
        band_max = max(0.0, bup)

        if ub < tolerance:
            # Zero forecast — model has no information
            rec_type = RecommendationType.UNKNOWN
            limit = None
        elif bup >= ub - tolerance and rc_kwh <= tolerance:
            # Range reaches forecast max AND gradient is non-positive
            rec_type = RecommendationType.UNLIMIT
            limit = None
        else:
            # Need to actively limit
            rec_type = RecommendationType.SET
            limit = band_max

        recommendations.append(
            ControlRecommendation(
                type=rec_type,
                optimal=val,
                limit=limit,
                band_min=band_min,
                band_max=band_max,
                reduced_cost=rc_kwh,
                forecast_max=ub,
            )
        )

    return recommendations
