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
    Extra steps from alignment are absorbed by extending T3. A variable-sized trailing
    step is added to T4 to ensure the total duration exactly matches horizon_minutes.

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

    # Calculate remaining steps and initial duration for T4
    used_steps = t1_count + t2_count + t3_count
    remaining_steps = total_steps - used_steps

    # Duration covered by T1-T3 (before any extra T3 steps)
    t1_minutes = t1_count * t1_dur
    t2_minutes = t2_count * t2_dur
    t3_minutes = t3_count * t3_dur
    covered_minutes = t1_minutes + t2_minutes + t3_minutes

    # Initial remaining duration for T4
    remaining_duration = horizon_minutes - covered_minutes

    # Calculate extra T3 steps to absorb into total_steps while respecting duration.
    # The formula balances step count and duration by converting T4 60-min slots
    # to pairs of T3 30-min slots, accounting for the trailing step if present.
    if remaining_duration % t4_dur == 0:
        extra_t3 = 2 * remaining_steps - remaining_duration // t3_dur
    else:
        extra_t3 = 2 * remaining_steps - 1 - remaining_duration // t3_dur

    extra_t3 = max(0, extra_t3)
    t3_count += extra_t3

    # Recalculate remaining duration after T3 extension
    covered_minutes = t1_minutes + t2_minutes + t3_count * t3_dur
    remaining_duration = horizon_minutes - covered_minutes

    # Calculate T4 with trailing step to hit exact horizon end
    trailing_minutes = remaining_duration % t4_dur
    t4_60min_count = remaining_duration // t4_dur
    t4_count = t4_60min_count + (1 if trailing_minutes > 0 else 0)

    # Build period durations in seconds
    periods_seconds: list[int] = []
    periods_seconds.extend([t1_dur * 60] * t1_count)
    periods_seconds.extend([t2_dur * 60] * t2_count)
    periods_seconds.extend([t3_dur * 60] * t3_count)
    periods_seconds.extend([t4_dur * 60] * t4_60min_count)
    if trailing_minutes > 0:
        periods_seconds.append(trailing_minutes * 60)

    tier_counts = [t1_count, t2_count, t3_count, t4_count]

    return periods_seconds, tier_counts


def calculate_total_steps(
    min_counts: tuple[int, int, int],
    horizon_minutes: int,
) -> int:
    """Calculate total step count for preset configurations.

    Since presets use fixed tier durations (1, 5, 30, 60 minutes), we know
    the worst-case alignment overhead is at most 10 steps (4 for T1, 5 for T2,
    1 for T3). We add 12 steps as a buffer for alignment variance absorption,
    chosen for its high divisibility (1, 2, 3, 4, 6, 12).

    Args:
        min_counts: Minimum step counts for tiers 1-3.
        horizon_minutes: Total horizon duration in minutes.

    Returns:
        Total number of steps for the optimization horizon.

    """
    # Fixed tier durations for presets: 1, 5, 30, 60 minutes
    # 12-step buffer covers worst-case alignment (10 steps) with room for flexibility
    alignment_buffer = 12

    # T1-T3 cover this many minutes at minimum counts
    min_t1_t3_minutes = min_counts[0] * 1 + min_counts[1] * 5 + min_counts[2] * 30

    # Remaining minutes for T4 at 60-min granularity
    remaining_minutes = horizon_minutes - min_t1_t3_minutes
    base_t4_steps = remaining_minutes // 60

    return sum(min_counts) + base_t4_steps + alignment_buffer


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
        # Preset mode: use dynamic time alignment with fixed tier configuration
        days = _PRESET_DAYS[horizon_preset]
        horizon_minutes = days * 24 * 60

        # Presets use fixed tier durations and minimum counts
        tier_durations = (1, 5, 30, 60)
        min_counts = (5, 6, 4)

        now = dt_util.utcnow()
        total_steps = calculate_total_steps(min_counts, horizon_minutes)

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
