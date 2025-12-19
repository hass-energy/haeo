"""Forecast time generation utilities."""

from collections.abc import Mapping, Sequence

from homeassistant.util import dt as dt_util


def tiers_to_periods_seconds(config: Mapping[str, int]) -> list[int]:
    """Convert tier configuration to list of period durations in seconds.

    Each tier specifies:
    - duration: minutes per interval
    - until: cumulative time in minutes at end of this tier

    The count for each tier is calculated as:
    - Tier 1: until / duration
    - Tier N: (until - previous_until) / duration

    """
    periods: list[int] = []
    previous_until = 0
    for tier in [1, 2, 3, 4]:
        duration_minutes = config[f"tier_{tier}_duration"]
        until_minutes = config[f"tier_{tier}_until"]
        duration_seconds = duration_minutes * 60
        # Calculate count from (until - previous_until) / duration
        tier_span = until_minutes - previous_until
        count = tier_span // duration_minutes
        periods.extend([duration_seconds] * count)
        previous_until = until_minutes
    return periods


def generate_forecast_timestamps(periods_seconds: Sequence[int], start_time: float | None = None) -> tuple[float, ...]:
    """Generate forecast timestamps as fence posts (period boundaries).

    Creates n_periods+1 timestamps representing the start of each period plus
    the end of the final period.

    Args:
        periods_seconds: Duration of each period in seconds.
        start_time: Starting timestamp in epoch seconds. If None, uses current
            time rounded down to the smallest period boundary.

    Returns:
        Tuple of timestamps for each fence post.

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


def generate_forecast_timestamps_from_config(config: Mapping[str, int]) -> tuple[float, ...]:
    """Generate forecast timestamps from tier configuration.

    Converts tier config to period durations and generates fence post timestamps
    starting from the current time rounded to the smallest period boundary.

    Args:
        config: Tier configuration with tier_N_duration and tier_N_until keys.

    Returns:
        Tuple of timestamps for each fence post.

    """
    periods_seconds = tiers_to_periods_seconds(config)
    return generate_forecast_timestamps(periods_seconds)
