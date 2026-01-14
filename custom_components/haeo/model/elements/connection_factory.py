"""Factory functions for building CompositeConnections from configuration.

These factories provide backward-compatible interfaces that construct
CompositeConnections with the appropriate segments based on configuration.
"""

from collections.abc import Sequence

from highspy import Highs
import numpy as np
from numpy.typing import NDArray

from .composite_connection import CompositeConnection
from .segments import (
    ConnectionSegment,
    EfficiencySegment,
    PassthroughSegment,
    PowerLimitSegment,
    PricingSegment,
    TimeSliceSegment,
)


def create_power_connection(
    name: str,
    periods: Sequence[float],
    *,
    solver: Highs,
    source: str,
    target: str,
    max_power_source_target: float | Sequence[float] | None = None,
    max_power_target_source: float | Sequence[float] | None = None,
    fixed_power: bool = False,
    efficiency_source_target: float | Sequence[float] | None = None,
    efficiency_target_source: float | Sequence[float] | None = None,
    price_source_target: float | Sequence[float] | None = None,
    price_target_source: float | Sequence[float] | None = None,
) -> CompositeConnection:
    """Create a CompositeConnection with PowerConnection-equivalent behavior.

    This factory constructs a chain of segments that replicate the behavior
    of the original PowerConnection class:
    - Efficiency losses (if specified)
    - Power limits (if specified)
    - Transfer pricing (if specified)
    - Time slice constraint (if both directions have limits)

    Segments are ordered as:
    1. EfficiencySegment (if efficiency specified)
    2. PowerLimitSegment (if limits specified)
    3. PricingSegment (if prices specified)
    4. TimeSliceSegment (if both directions have limits)

    If no modifiers are specified, a single PassthroughSegment is used.

    Args:
        name: Name of the connection
        periods: Sequence of time period durations in hours
        solver: The HiGHS solver instance
        source: Name of the source element
        target: Name of the target element
        max_power_source_target: Maximum power flow source→target (kW)
        max_power_target_source: Maximum power flow target→source (kW)
        fixed_power: If True, power is fixed to max values
        efficiency_source_target: Efficiency percentage (0-100) for source→target
        efficiency_target_source: Efficiency percentage (0-100) for target→source
        price_source_target: Price in $/kWh for source→target flow
        price_target_source: Price in $/kWh for target→source flow

    Returns:
        CompositeConnection with appropriate segments

    """
    periods_arr: NDArray[np.floating] = np.asarray(periods)
    n_periods = len(periods_arr)
    segments: list[ConnectionSegment] = []
    segment_counter = 0

    def next_segment_id() -> str:
        nonlocal segment_counter
        seg_id = f"{name}_seg{segment_counter}"
        segment_counter += 1
        return seg_id

    # Efficiency segment (convert percentage to fraction)
    has_efficiency = efficiency_source_target is not None or efficiency_target_source is not None
    if has_efficiency:
        # Convert percentage (0-100) to fraction (0-1)
        eff_st = _to_fraction(efficiency_source_target, n_periods)
        eff_ts = _to_fraction(efficiency_target_source, n_periods)
        segments.append(
            EfficiencySegment(
                next_segment_id(),
                periods_arr,
                solver,
                efficiency_st=eff_st,
                efficiency_ts=eff_ts,
            )
        )

    # Power limit segment
    has_limits = max_power_source_target is not None or max_power_target_source is not None
    if has_limits:
        segments.append(
            PowerLimitSegment(
                next_segment_id(),
                periods_arr,
                solver,
                max_power_st=max_power_source_target,
                max_power_ts=max_power_target_source,
                fixed_power=fixed_power,
            )
        )

    # Pricing segment
    has_pricing = price_source_target is not None or price_target_source is not None
    if has_pricing:
        segments.append(
            PricingSegment(
                next_segment_id(),
                periods_arr,
                solver,
                price_st=price_source_target,
                price_ts=price_target_source,
            )
        )

    # Time slice segment (only if both directions have limits)
    if max_power_source_target is not None and max_power_target_source is not None:
        # Use the power limits as capacities for normalization
        segments.append(
            TimeSliceSegment(
                next_segment_id(),
                periods_arr,
                solver,
                capacity_st=max_power_source_target,
                capacity_ts=max_power_target_source,
            )
        )

    # If no modifiers, add a passthrough segment
    if not segments:
        segments.append(PassthroughSegment(next_segment_id(), periods_arr, solver))

    return CompositeConnection(
        name=name,
        periods=periods,
        solver=solver,
        source=source,
        target=target,
        segments=segments,
    )


def _to_fraction(
    efficiency: float | Sequence[float] | None,
    n_periods: int,
) -> NDArray[np.floating]:
    """Convert efficiency percentage to fraction, defaulting to 100%."""
    if efficiency is None:
        return np.ones(n_periods)

    if isinstance(efficiency, (int, float)):
        return np.full(n_periods, efficiency / 100.0)

    return np.asarray(efficiency) / 100.0


__all__ = [
    "create_power_connection",
]
