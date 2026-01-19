"""Power limit segment that constrains maximum power flow.

Limits power flow in each direction and optionally prevents simultaneous
bidirectional flow at full capacity (time-slice constraint).
"""

from typing import Any, Final, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.model.reactive import TrackedParam, constraint
from custom_components.haeo.model.util import broadcast_to_sequence

from .segment import Segment

type PowerLimitOutputName = Literal["source_target", "target_source", "time_slice"]

POWER_LIMIT_SOURCE_TARGET: Final = "source_target"
POWER_LIMIT_TARGET_SOURCE: Final = "target_source"
POWER_LIMIT_TIME_SLICE: Final = "time_slice"


class PowerLimitSegmentSpec(TypedDict):
    """Specification for creating a PowerLimitSegment."""

    segment_type: Literal["power_limit"]
    max_power_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    max_power_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]
    fixed: NotRequired[bool | None]


class PowerLimitSegment(Segment):
    """Segment that limits maximum power flow.

    Creates single power variables for each direction (no losses, so in == out).

    Constraints:
        power_st <= max_power_source_target  (or == if fixed)
        power_ts <= max_power_target_source  (or == if fixed)

    Time-slice constraint (when both limits set):
        (power_st / max_power_source_target) + (power_ts / max_power_target_source) <= 1

    This prevents simultaneous bidirectional flow at full capacity.

    Uses TrackedParam for max_power values to enable warm-start optimization.
    """

    # TrackedParams for warm-start support
    max_power_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    max_power_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: PowerLimitSegmentSpec,
    ) -> None:
        """Initialize power limit segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            spec: Power limit segment specification.

        """
        super().__init__(segment_id, n_periods, periods, solver)
        self._fixed = spec.get("fixed", False)

        # Create single power variable per direction (lossless segment, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        # Set tracked params (these trigger reactive infrastructure)
        self.max_power_source_target = broadcast_to_sequence(spec.get("max_power_source_target"), self._n_periods)
        self.max_power_target_source = broadcast_to_sequence(spec.get("max_power_target_source"), self._n_periods)

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_st

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction (same as in, lossless)."""
        return self._power_st

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_ts

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction (same as in, lossless)."""
        return self._power_ts

    @constraint(output=True, unit="$/kW")
    def source_target(self) -> list[highs_linear_expression] | None:
        """Power limit constraint for source→target direction."""
        if self.max_power_source_target is None:
            return None

        if self._fixed:
            return list(self._power_st == self.max_power_source_target)
        return list(self._power_st <= self.max_power_source_target)

    @constraint(output=True, unit="$/kW")
    def target_source(self) -> list[highs_linear_expression] | None:
        """Power limit constraint for target→source direction."""
        if self.max_power_target_source is None:
            return None

        if self._fixed:
            return list(self._power_ts == self.max_power_target_source)
        return list(self._power_ts <= self.max_power_target_source)

    @constraint(output=True, unit="$/kW")
    def time_slice(self) -> list[highs_linear_expression] | None:
        """Time-slice constraint: prevent simultaneous bidirectional flow at capacity.

        Constraint: (power_st / max_power_source_target) + (power_ts / max_power_target_source) <= 1
        """
        if self.max_power_source_target is None or self.max_power_target_source is None:
            return None

        # Normalize power to [0, 1] range based on capacity
        # Handle zero capacity by setting coefficient to 0
        coeff_st = np.divide(
            1.0,
            self.max_power_source_target,
            out=np.zeros(self._n_periods),
            where=self.max_power_source_target > 0,
        )
        coeff_ts = np.divide(
            1.0,
            self.max_power_target_source,
            out=np.zeros(self._n_periods),
            where=self.max_power_target_source > 0,
        )

        normalized_st = self._power_st * coeff_st
        normalized_ts = self._power_ts * coeff_ts
        return list(normalized_st + normalized_ts <= 1.0)


__all__ = [
    "POWER_LIMIT_SOURCE_TARGET",
    "POWER_LIMIT_TARGET_SOURCE",
    "POWER_LIMIT_TIME_SLICE",
    "PowerLimitOutputName",
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
]
