"""Tests for forecast time generation utilities."""

from datetime import UTC, datetime
from typing import TypedDict
from unittest.mock import patch

from freezegun import freeze_time
import pytest

from custom_components.haeo.util.forecast_times import (
    calculate_aligned_tier_counts,
    calculate_total_steps,
    generate_forecast_timestamps,
    generate_forecast_timestamps_from_config,
    minutes_to_next_boundary,
    tiers_to_periods_seconds,
)


class TierTestCase(TypedDict):
    """Test case for tiers_to_periods_seconds."""

    description: str
    config: dict[str, int]
    expected: list[int]


TIER_TEST_CASES: dict[str, TierTestCase] = {
    "single_tier": {
        "description": "single tier with 3 intervals of 60 seconds",
        "config": {
            "tier_1_count": 3,
            "tier_1_duration": 1,  # 1 minute = 60 seconds
            "tier_2_count": 0,
            "tier_2_duration": 5,
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        "expected": [60, 60, 60],
    },
    "multiple_tiers": {
        "description": "multiple tiers with different intervals",
        "config": {
            "tier_1_count": 2,
            "tier_1_duration": 1,  # 60 seconds each
            "tier_2_count": 1,
            "tier_2_duration": 5,  # 300 seconds
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        "expected": [60, 60, 300],
    },
    "all_tiers": {
        "description": "all four tiers populated",
        "config": {
            "tier_1_count": 1,
            "tier_1_duration": 1,  # 60s
            "tier_2_count": 1,
            "tier_2_duration": 5,  # 300s
            "tier_3_count": 1,
            "tier_3_duration": 30,  # 1800s
            "tier_4_count": 1,
            "tier_4_duration": 60,  # 3600s
        },
        "expected": [60, 300, 1800, 3600],
    },
    "empty_tiers": {
        "description": "all tiers with zero count",
        "config": {
            "tier_1_count": 0,
            "tier_1_duration": 1,
            "tier_2_count": 0,
            "tier_2_duration": 5,
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        "expected": [],
    },
}


@pytest.mark.parametrize("case_id", TIER_TEST_CASES.keys())
def test_tiers_to_periods_seconds(case_id: str) -> None:
    """Verify tier configuration converts to correct period durations."""
    case = TIER_TEST_CASES[case_id]
    result = tiers_to_periods_seconds(case["config"])
    assert result == case["expected"], case["description"]


class TimestampTestCase(TypedDict):
    """Test case for generate_forecast_timestamps."""

    description: str
    periods_seconds: list[int]
    start_time: float
    expected: tuple[float, ...]


TIMESTAMP_TEST_CASES: dict[str, TimestampTestCase] = {
    "single_period": {
        "description": "single period generates two boundaries",
        "periods_seconds": [60],
        "start_time": 0.0,
        "expected": (0.0, 60.0),
    },
    "multiple_periods": {
        "description": "multiple periods generate n+1 boundaries",
        "periods_seconds": [60, 60, 300],
        "start_time": 0.0,
        "expected": (0.0, 60.0, 120.0, 420.0),
    },
    "empty_periods": {
        "description": "empty periods generate single boundary at start",
        "periods_seconds": [],
        "start_time": 100.0,
        "expected": (100.0,),
    },
    "nonzero_start": {
        "description": "boundaries are relative to start time",
        "periods_seconds": [60, 120],
        "start_time": 1000.0,
        "expected": (1000.0, 1060.0, 1180.0),
    },
    "float_start": {
        "description": "float start time preserved",
        "periods_seconds": [60],
        "start_time": 1000.5,
        "expected": (1000.5, 1060.5),
    },
}


@pytest.mark.parametrize("case_id", TIMESTAMP_TEST_CASES.keys())
def test_generate_forecast_timestamps(case_id: str) -> None:
    """Verify forecast timestamp generation."""
    case = TIMESTAMP_TEST_CASES[case_id]
    timestamps, start_time = generate_forecast_timestamps(case["periods_seconds"], case["start_time"])
    assert start_time == case["start_time"]
    assert timestamps == case["expected"], case["description"]


def test_generate_forecast_timestamps_default_start_time() -> None:
    """Verify default start_time uses current time with rounding."""
    periods_seconds = [60, 60]

    # Mock utcnow to return a known time
    mock_time = datetime(2025, 1, 1, 12, 0, 30, tzinfo=UTC)
    expected_start = 1735732800.0  # 2025-01-01 12:00:00 UTC (rounded from 12:00:30)

    with patch("custom_components.haeo.util.forecast_times.dt_util.utcnow", return_value=mock_time):
        timestamps, start_time = generate_forecast_timestamps(periods_seconds)

    assert start_time == expected_start
    assert timestamps[0] == expected_start
    assert len(timestamps) == 3  # 2 periods + 1 = 3 boundaries
    assert timestamps[1] == expected_start + 60.0
    assert timestamps[2] == expected_start + 120.0


def test_generate_forecast_timestamps_from_config() -> None:
    """Verify timestamps generated from config use proper rounding."""
    config = {
        "tier_1_count": 2,
        "tier_1_duration": 1,  # 60 seconds each
        "tier_2_count": 0,
        "tier_2_duration": 5,
        "tier_3_count": 0,
        "tier_3_duration": 30,
        "tier_4_count": 0,
        "tier_4_duration": 60,
    }

    # Mock utcnow to return a known time
    mock_time = datetime(2025, 1, 1, 12, 0, 30, tzinfo=UTC)
    expected_start = 1735732800.0  # 2025-01-01 12:00:00 UTC (rounded from 12:00:30)

    with patch("custom_components.haeo.util.forecast_times.dt_util.utcnow", return_value=mock_time):
        timestamps, start_time = generate_forecast_timestamps_from_config(config)

    assert start_time == expected_start
    assert timestamps[0] == expected_start
    assert len(timestamps) == 3  # 2 periods + 1 = 3 boundaries
    assert timestamps[1] == expected_start + 60.0
    assert timestamps[2] == expected_start + 120.0


# ============================================================================
# Time alignment tests (for preset configurations)
# ============================================================================


def test_alignment_tier_counts_aligned_start() -> None:
    """Verify tier counts are correctly calculated when starting on the hour."""
    start_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    tier_durations = (1, 5, 30, 60)  # Standard tier durations
    min_counts = (5, 6, 4)  # Standard minimums
    horizon_minutes = 5 * 24 * 60  # 5 days

    total_steps = calculate_total_steps(min_counts, horizon_minutes)

    periods_seconds, tier_counts = calculate_aligned_tier_counts(
        start_time=start_time,
        tier_durations=tier_durations,
        min_counts=min_counts,
        total_steps=total_steps,
        horizon_minutes=horizon_minutes,
    )

    # T1 should respect minimum and align to 5-min boundary
    assert tier_counts[0] >= min_counts[0], "T1 should have at least minimum count"
    # T2 should respect minimum and align to 30-min boundary
    assert tier_counts[1] >= min_counts[1], "T2 should have at least minimum count"
    # T3 should respect minimum
    assert tier_counts[2] >= min_counts[2], "T3 should have at least minimum count"
    # Verify total periods matches periods_seconds length
    assert len(periods_seconds) == sum(tier_counts)
    # Verify total step count is consistent
    assert sum(tier_counts) == total_steps


def test_alignment_tier_counts_mid_hour_start() -> None:
    """Verify tier counts when starting at an odd minute."""
    start_time = datetime(2025, 1, 1, 12, 43, 0, tzinfo=UTC)
    tier_durations = (1, 5, 30, 60)
    min_counts = (5, 6, 4)
    horizon_minutes = 5 * 24 * 60

    total_steps = calculate_total_steps(min_counts, horizon_minutes)

    periods_seconds, tier_counts = calculate_aligned_tier_counts(
        start_time=start_time,
        tier_durations=tier_durations,
        min_counts=min_counts,
        total_steps=total_steps,
        horizon_minutes=horizon_minutes,
    )

    # T1 ends on a 5-min boundary - from :43, T1 should end on :50 or later
    t1_end_minute = (start_time.minute + tier_counts[0] * tier_durations[0]) % 60
    assert t1_end_minute % 5 == 0, "T1 should end on 5-min boundary"

    # T2 ends on a 30-min boundary
    t2_end_minute = (t1_end_minute + tier_counts[1] * tier_durations[1]) % 60
    assert t2_end_minute % 30 == 0, "T2 should end on 30-min boundary"

    # Total steps preserved
    assert sum(tier_counts) == total_steps
    assert len(periods_seconds) == sum(tier_counts)


def test_minutes_to_next_boundary() -> None:
    """Test minutes_to_next_boundary helper function."""
    # Already on boundary - returns full interval
    assert minutes_to_next_boundary(0, 5) == 5
    assert minutes_to_next_boundary(30, 30) == 30

    # Near boundary
    assert minutes_to_next_boundary(43, 5) == 2  # 43 -> 45
    assert minutes_to_next_boundary(28, 30) == 2  # 28 -> 30
    assert minutes_to_next_boundary(59, 60) == 1  # 59 -> 60

    # Various positions
    assert minutes_to_next_boundary(17, 5) == 3  # 17 -> 20
    assert minutes_to_next_boundary(45, 30) == 15  # 45 -> 60


def test_calculate_total_steps() -> None:
    """Test total step calculation with alignment buffer."""
    min_counts = (5, 6, 4)
    horizon_minutes = 5 * 24 * 60  # 5 days

    total_steps = calculate_total_steps(min_counts, horizon_minutes)

    # Should be deterministic for given inputs
    assert total_steps > 0
    # Sanity check: should cover the horizon
    # With mostly 60-min steps, 5 days = 120 hours = ~120 steps at least
    assert total_steps >= 100

    # Verify the formula: sum(min_counts) + base_t4_steps + 12
    min_t1_t3_minutes = 5 * 1 + 6 * 5 + 4 * 30  # 5 + 30 + 120 = 155
    remaining_minutes = horizon_minutes - min_t1_t3_minutes  # 7200 - 155 = 7045
    expected_base_t4 = remaining_minutes // 60  # 117
    expected_total = 5 + 6 + 4 + expected_base_t4 + 12  # 15 + 117 + 12 = 144
    assert total_steps == expected_total


def test_alignment_no_extra_steps() -> None:
    """Test alignment when extra_steps <= 0 (no variance absorption needed).

    This tests the case where remaining_steps <= base_t4_steps, meaning
    T4 can be covered entirely with 60-min periods without needing 30-min
    variance absorption.
    """
    # Start aligned on the hour for predictable T1/T2/T3 counts
    start_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    tier_durations = (1, 5, 30, 60)
    min_counts = (5, 6, 4)
    horizon_minutes = 2 * 24 * 60  # 2 days

    # With alignment at :00, T1=5, T2=11, T3=4 (used_steps=20).
    # Remaining duration is 2700 min, needing 45 base T4 steps.
    # Setting total_steps=65 gives remaining_steps=45, so extra_steps=0.
    total_steps = 65

    periods_seconds, tier_counts = calculate_aligned_tier_counts(
        start_time=start_time,
        tier_durations=tier_durations,
        min_counts=min_counts,
        total_steps=total_steps,
        horizon_minutes=horizon_minutes,
    )

    # Verify we got results
    assert len(periods_seconds) == sum(tier_counts)
    # T4 count should be exactly remaining_steps (no variance absorption)
    assert tier_counts[3] == total_steps - (tier_counts[0] + tier_counts[1] + tier_counts[2])


def test_tiers_to_periods_with_preset() -> None:
    """Test that tiers_to_periods_seconds uses alignment for presets."""
    config = {
        "horizon_preset": "5_days",
        "tier_1_duration": 1,
        "tier_2_duration": 5,
        "tier_3_duration": 30,
        "tier_4_duration": 60,
    }

    # Mock utcnow to return a known time
    mock_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    with patch("custom_components.haeo.util.forecast_times.dt_util.utcnow", return_value=mock_time):
        periods = tiers_to_periods_seconds(config)

    # Should have periods
    assert len(periods) > 0
    # First periods should be 60 seconds (tier 1)
    assert periods[0] == 60


def test_tiers_to_periods_with_custom() -> None:
    """Test that tiers_to_periods_seconds uses fixed counts for custom preset."""
    config = {
        "horizon_preset": "custom",
        "tier_1_count": 5,
        "tier_1_duration": 1,
        "tier_2_count": 11,
        "tier_2_duration": 5,
        "tier_3_count": 46,
        "tier_3_duration": 30,
        "tier_4_count": 48,
        "tier_4_duration": 60,
    }

    periods = tiers_to_periods_seconds(config)

    # Should have exactly the specified number of periods
    assert len(periods) == 5 + 11 + 46 + 48  # 110 periods
    # Verify the pattern: 5x60s, 11x300s, 46x1800s, 48x3600s
    assert periods[:5] == [60] * 5
    assert periods[5:16] == [300] * 11


def test_tiers_to_periods_with_missing_tiers() -> None:
    """Test that tiers_to_periods_seconds handles missing tier configs gracefully."""
    # Config with only T1 and T2, missing T3 and T4
    config = {
        "horizon_preset": "custom",
        "tier_1_count": 3,
        "tier_1_duration": 1,
        "tier_2_count": 2,
        "tier_2_duration": 5,
        # tier_3 and tier_4 deliberately omitted
    }

    periods = tiers_to_periods_seconds(config)

    # Should have only the specified tiers
    assert len(periods) == 3 + 2  # 5 periods total
    assert periods[:3] == [60] * 3  # T1: 3x60s
    assert periods[3:5] == [300] * 2  # T2: 2x300s


@pytest.mark.parametrize("preset", ["2_days", "3_days", "5_days", "7_days"])
def test_preset_produces_constant_step_count_for_all_minutes(preset: str) -> None:
    """Verify each preset produces the same step count regardless of starting minute.

    The time alignment algorithm adjusts tier counts to align with forecast boundaries,
    but the total number of steps must remain constant for a given preset. This ensures
    consistent solver performance regardless of when optimization starts.
    """
    config = {
        "horizon_preset": preset,
        "tier_1_duration": 1,
        "tier_2_duration": 5,
        "tier_3_duration": 30,
        "tier_4_duration": 60,
    }

    step_counts: list[int] = []

    for minute in range(60):
        with freeze_time(datetime(2025, 1, 1, 12, minute, 0, tzinfo=UTC)):
            periods = tiers_to_periods_seconds(config)
            step_counts.append(len(periods))

    # All minutes should produce the same step count
    expected_count = step_counts[0]
    for minute, count in enumerate(step_counts):
        assert count == expected_count, (
            f"Preset {preset}: minute {minute} produced {count} steps, expected {expected_count}"
        )


PRESET_HORIZON_MINUTES = {
    "2_days": 2 * 24 * 60,
    "3_days": 3 * 24 * 60,
    "5_days": 5 * 24 * 60,
    "7_days": 7 * 24 * 60,
}


@pytest.mark.parametrize("preset", ["2_days", "3_days", "5_days", "7_days"])
def test_preset_produces_exact_horizon_duration(preset: str) -> None:
    """Verify total period duration exactly matches horizon minutes.

    The trailing step ensures that for N whole-day horizons, the optimization
    ends at the same minute of the hour it started.
    """
    config = {
        "horizon_preset": preset,
        "tier_1_duration": 1,
        "tier_2_duration": 5,
        "tier_3_duration": 30,
        "tier_4_duration": 60,
    }
    expected_seconds = PRESET_HORIZON_MINUTES[preset] * 60

    # Test all 60 possible start minutes
    for minute in range(60):
        with freeze_time(datetime(2025, 1, 1, 12, minute, 0, tzinfo=UTC)):
            periods = tiers_to_periods_seconds(config)
            total_seconds = sum(periods)
            assert total_seconds == expected_seconds, (
                f"Preset {preset}: minute {minute} produced {total_seconds}s, expected {expected_seconds}s"
            )
