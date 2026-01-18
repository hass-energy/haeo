"""Forecast time generation utilities."""

from collections.abc import Mapping, Sequence
from datetime import datetime

from homeassistant.util import dt as dt_util

# Preset name to days mapping for aligned mode
_PRESET_DAYS: dict[str, int] = {
    "2_days": 2,
    "3_days": 3,
    "5_days": 5,
    "7_days": 7,
}


def minutes_to_next_boundary(current_minute: int, boundary_interval: int) -> int:
    """Calculate minutes until the next boundary of the given interval.

    Args:
        current_minute: Current minute within the hour (0-59).
        boundary_interval: The interval to align to (e.g., 5, 30, 60).

    Returns:
        Number of minutes until the next boundary.

    Example:
        >>> minutes_to_next_boundary(43, 5)
        2  # 43 -> 45
        >>> minutes_to_next_boundary(45, 30)
        15  # 45 -> 60 (next 30-min boundary)

    """
    remainder = current_minute % boundary_interval
    if remainder == 0:
        return boundary_interval
    return boundary_interval - remainder


def _calculate_aligned_count(
    current_minute: int,
    step_duration: int,
    boundary_interval: int,
    min_count: int,
) -> int:
    """Calculate the number of steps needed to reach a boundary, respecting minimum.

    The function ensures the tier ends exactly on a boundary of the next tier.
    If the minimum count would overshoot the nearest boundary, it extends to
    the next valid boundary that maintains alignment.

    Args:
        current_minute: Current minute within the hour.
        step_duration: Duration of each step in minutes.
        boundary_interval: The boundary interval to align to in minutes.
        min_count: Minimum number of steps required.

    Returns:
        Number of steps that ensures alignment to boundary.

    """
    # Calculate steps needed to reach the next boundary
    minutes_to_boundary = minutes_to_next_boundary(current_minute, boundary_interval)
    steps_to_boundary = minutes_to_boundary // step_duration

    if steps_to_boundary >= min_count:
        # We can reach the boundary with fewer than or equal to min steps
        return steps_to_boundary

    # We need more than steps_to_boundary, so we overshoot
    # Find the next boundary after min_count steps
    end_minute_with_min = (current_minute + min_count * step_duration) % 60

    if end_minute_with_min % boundary_interval == 0:
        # Lucky: min_count lands on a boundary
        return min_count

    # Need to extend past min_count to reach next boundary
    minutes_past_min = minutes_to_next_boundary(end_minute_with_min, boundary_interval)
    additional_steps = minutes_past_min // step_duration

    return min_count + additional_steps


def calculate_aligned_tier_counts(
    start_time: datetime,
    tier_durations: tuple[int, int, int, int],
    min_counts: tuple[int, int, int],
    total_steps: int,
    horizon_minutes: int,
) -> tuple[list[int], list[int]]:
    """Calculate tier step counts aligned to forecast boundaries.

    This function dynamically adjusts tier counts based on the start time to ensure
    that tier boundaries align with forecast data boundaries (5-min, 30-min, 60-min).
    Extra steps from alignment are absorbed by extending T3 or adding a trailing
    30-min step to T4.

    Args:
        start_time: The optimization start time.
        tier_durations: Duration of each tier in minutes (1, 5, 30, 60).
        min_counts: Minimum step counts for tiers 1-3 (T4 count is computed).
        total_steps: Total number of steps to distribute across all tiers.
        horizon_minutes: Total horizon duration in minutes.

    Returns:
        Tuple of (period_durations_seconds, tier_counts).
        period_durations_seconds: List of duration in seconds for each period.
        tier_counts: List of [t1_count, t2_count, t3_count, t4_count].

    """
    t1_dur, t2_dur, t3_dur, t4_dur = tier_durations
    min_t1, min_t2, min_t3 = min_counts

    # Get current minute within the hour
    current_minute = start_time.minute

    # T1 alignment: must end on 5-minute boundary
    t1_count = _calculate_aligned_count(current_minute, t1_dur, t2_dur, min_t1)

    # T2 alignment: must end on 30-minute boundary
    t1_end_minute = (current_minute + t1_count * t1_dur) % 60
    t2_count = _calculate_aligned_count(t1_end_minute, t2_dur, t3_dur, min_t2)

    # T3 alignment: must end on 60-minute boundary
    t2_end_minute = (t1_end_minute + t2_count * t2_dur) % 60
    t3_count = _calculate_aligned_count(t2_end_minute, t3_dur, t4_dur, min_t3)

    # Calculate remaining steps and duration for T4
    used_steps = t1_count + t2_count + t3_count
    remaining_steps = total_steps - used_steps

    # Duration covered by T1-T3
    t1_minutes = t1_count * t1_dur
    t2_minutes = t2_count * t2_dur
    t3_minutes = t3_count * t3_dur
    covered_minutes = t1_minutes + t2_minutes + t3_minutes

    # Remaining duration for T4
    remaining_duration = horizon_minutes - covered_minutes

    # How many steps would T4 need if purely 60-min?
    base_t4_steps = remaining_duration // t4_dur

    # Extra steps that must be 30-min instead of 60-min
    extra_steps = remaining_steps - base_t4_steps

    # Variance absorption strategy
    t4_trailing_30 = False
    if extra_steps > 0:
        if extra_steps % 2 == 0:
            # Even: add all extra steps as 30-min to T3
            t3_count += extra_steps
            t4_count = base_t4_steps
        else:
            # Odd: add (extra-1) 30-min steps to T3, one 30-min at end of T4
            t3_count += extra_steps - 1
            t4_count = base_t4_steps
            t4_trailing_30 = True
    else:
        t4_count = remaining_steps

    # Build period durations in seconds
    periods_seconds: list[int] = []
    periods_seconds.extend([t1_dur * 60] * t1_count)
    periods_seconds.extend([t2_dur * 60] * t2_count)
    periods_seconds.extend([t3_dur * 60] * t3_count)
    if t4_trailing_30:
        # All but last T4 step are 60-min, last is 30-min
        periods_seconds.extend([t4_dur * 60] * t4_count)
        periods_seconds.append(t3_dur * 60)  # Trailing 30-min step
    else:
        periods_seconds.extend([t4_dur * 60] * t4_count)

    tier_counts = [t1_count, t2_count, t3_count, t4_count + (1 if t4_trailing_30 else 0)]

    return periods_seconds, tier_counts


def calculate_worst_case_total_steps(
    min_counts: tuple[int, int, int],
    tier_durations: tuple[int, int, int, int],
    horizon_minutes: int,
) -> int:
    """Calculate total step count based on worst-case alignment.

    The worst case is when T1 and T2 expand to their maximum possible counts
    due to unfavorable start time alignment.

    Args:
        min_counts: Minimum step counts for tiers 1-3.
        tier_durations: Duration of each tier in minutes (1, 5, 30, 60).
        horizon_minutes: Total horizon duration in minutes.

    Returns:
        Total number of steps needed for worst-case alignment.

    """
    t1_dur, t2_dur, t3_dur, t4_dur = tier_durations
    min_t1, min_t2, min_t3 = min_counts

    # Worst case for T1: start 1 minute after 5-min boundary (need 4 extra steps)
    # Maximum T1 = max(min_t1, t2_dur - 1) when starting at :X1, :X6, etc.
    max_t1 = max(min_t1, t2_dur - 1)

    # Worst case for T2: T1 ends 1 minute after 30-min boundary
    # Maximum T2 = max(min_t2, (t3_dur - t2_dur) / t2_dur) = max(min_t2, 5)
    max_t2 = max(min_t2, (t3_dur - t2_dur) // t2_dur)

    # Worst case for T3: T2 ends 1 minute after 60-min boundary
    # Maximum T3 = max(min_t3, (t4_dur - t3_dur) / t3_dur) = max(min_t3, 1)
    max_t3 = max(min_t3, (t4_dur - t3_dur) // t3_dur)

    # T1-T3 cover this many minutes in worst case
    worst_case_t1_t3_minutes = max_t1 * t1_dur + max_t2 * t2_dur + max_t3 * t3_dur

    # Remaining minutes for T4
    remaining_minutes = horizon_minutes - worst_case_t1_t3_minutes

    # T4 needs enough steps to cover remaining minutes
    # We add steps as 60-min, but might need 30-min steps for variance
    # Use 30-min granularity to ensure we have enough steps
    t4_steps = (remaining_minutes + t3_dur - 1) // t3_dur  # Round up at 30-min granularity

    return max_t1 + max_t2 + max_t3 + t4_steps


def tiers_to_periods_seconds(config: Mapping[str, int | str]) -> list[int]:
    """Convert tier configuration to list of period durations in seconds.

    Uses dynamic time alignment when a preset is selected (2/3/5/7 days).
    Falls back to fixed tier counts when using custom configuration.

    Args:
        config: Tier configuration dictionary with tier_N_count and tier_N_duration keys,
            plus optional horizon_preset key.

    Returns:
        List of period durations in seconds.

    """
    # Check if using a preset (enables time alignment)
    horizon_preset = config.get("horizon_preset")

    if horizon_preset and horizon_preset in _PRESET_DAYS:
        # Preset mode: use dynamic time alignment
        days = _PRESET_DAYS[horizon_preset]
        horizon_minutes = days * 24 * 60

        tier_durations = (
            int(config.get("tier_1_duration", 1)),
            int(config.get("tier_2_duration", 5)),
            int(config.get("tier_3_duration", 30)),
            int(config.get("tier_4_duration", 60)),
        )
        # For presets, use standard minimum counts for alignment
        min_counts = (5, 6, 4)

        now = dt_util.utcnow()

        # Calculate total steps based on worst-case for consistent solver size
        total_steps = calculate_worst_case_total_steps(min_counts, tier_durations, horizon_minutes)

        periods_seconds, _ = calculate_aligned_tier_counts(
            start_time=now,
            tier_durations=tier_durations,
            min_counts=min_counts,
            total_steps=total_steps,
            horizon_minutes=horizon_minutes,
        )
        return periods_seconds

    # Custom/legacy mode: use fixed tier counts from config
    periods: list[int] = []
    for tier in [1, 2, 3, 4]:
        count_key = f"tier_{tier}_count"
        duration_key = f"tier_{tier}_duration"
        if count_key in config:
            count = int(config[count_key])
            duration_seconds = int(config[duration_key]) * 60
            periods.extend([duration_seconds] * count)
    return periods


def generate_forecast_timestamps(periods_seconds: Sequence[int], start_time: float | None = None) -> tuple[float, ...]:
    """Generate forecast timestamps as period boundaries.

    Creates n_periods+1 timestamps representing the start of each period plus
    the end of the final period.

    Args:
        periods_seconds: Duration of each period in seconds.
        start_time: Starting timestamp in epoch seconds. If None, uses current
            time rounded down to the smallest period boundary.

    Returns:
        Tuple of timestamps for each boundary.

    Example:
        >>> generate_forecast_timestamps([60, 60, 300], 0.0)
        (0.0, 60.0, 120.0, 420.0)

    """
    if start_time is None:
        epoch_seconds = dt_util.utcnow().timestamp()
        smallest_period = min(periods_seconds) if periods_seconds else 60
        start_time = epoch_seconds // smallest_period * smallest_period

    timestamps: list[float] = [start_time]
    for period in periods_seconds:
        timestamps.append(timestamps[-1] + period)
    return tuple(timestamps)


def generate_forecast_timestamps_from_config(config: Mapping[str, int | str]) -> tuple[float, ...]:
    """Generate forecast timestamps from tier configuration.

    Converts tier config to period durations and generates boundary timestamps
    starting from the current time rounded to the smallest period boundary.

    Args:
        config: Tier configuration with tier_N_count and tier_N_duration keys.

    Returns:
        Tuple of timestamps for each boundary.

    """
    periods_seconds = tiers_to_periods_seconds(config)
    return generate_forecast_timestamps(periods_seconds)
