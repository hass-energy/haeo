"""Tests for forecast time generation utilities."""

from datetime import UTC, datetime
from typing import TypedDict
from unittest.mock import patch

import pytest

from custom_components.haeo.util.forecast_times import (
    calculate_aligned_tier_counts,
    calculate_worst_case_total_steps,
    generate_forecast_timestamps,
    generate_forecast_timestamps_from_config,
    minutes_to_next_boundary,
    tiers_to_periods_seconds,
)


class TierTestCase(TypedDict):
    """Test case for tiers_to_periods_seconds (legacy config)."""

    description: str
    config: dict[str, int]
    expected: list[int]


# Legacy tier test cases (without horizon_duration_minutes)
LEGACY_TIER_TEST_CASES: dict[str, TierTestCase] = {
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


@pytest.mark.parametrize("case_id", LEGACY_TIER_TEST_CASES.keys())
def test_tiers_to_periods_seconds_legacy(case_id: str) -> None:
    """Verify legacy tier configuration converts to correct period durations."""
    case = LEGACY_TIER_TEST_CASES[case_id]
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
    result = generate_forecast_timestamps(case["periods_seconds"], case["start_time"])
    assert result == case["expected"], case["description"]


def test_generate_forecast_timestamps_default_start_time() -> None:
    """Verify default start_time uses current time with rounding."""
    periods_seconds = [60, 60]

    # Mock utcnow to return a known time
    mock_time = datetime(2025, 1, 1, 12, 0, 30, tzinfo=UTC)
    expected_start = 1735732800.0  # 2025-01-01 12:00:00 UTC (rounded from 12:00:30)

    with patch("custom_components.haeo.util.forecast_times.dt_util.utcnow", return_value=mock_time):
        result = generate_forecast_timestamps(periods_seconds)

    assert result[0] == expected_start
    assert len(result) == 3  # 2 periods + 1 = 3 boundaries
    assert result[1] == expected_start + 60.0
    assert result[2] == expected_start + 120.0


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
        result = generate_forecast_timestamps_from_config(config)

    assert result[0] == expected_start
    assert len(result) == 3  # 2 periods + 1 = 3 boundaries
    assert result[1] == expected_start + 60.0
    assert result[2] == expected_start + 120.0


# ==================== Alignment Tests ====================


class BoundaryTestCase(TypedDict):
    """Test case for minutes_to_next_boundary."""

    current_minute: int
    boundary_interval: int
    expected: int


BOUNDARY_TEST_CASES: dict[str, BoundaryTestCase] = {
    "at_boundary_5min": {
        "current_minute": 0,
        "boundary_interval": 5,
        "expected": 5,  # Next boundary is 5 minutes away
    },
    "just_past_5min_boundary": {
        "current_minute": 1,
        "boundary_interval": 5,
        "expected": 4,  # 1 -> 5
    },
    "mid_5min_interval": {
        "current_minute": 43,
        "boundary_interval": 5,
        "expected": 2,  # 43 -> 45
    },
    "at_boundary_30min": {
        "current_minute": 30,
        "boundary_interval": 30,
        "expected": 30,  # Next boundary is 30 minutes away
    },
    "mid_30min_interval": {
        "current_minute": 45,
        "boundary_interval": 30,
        "expected": 15,  # 45 -> 60
    },
    "at_hour_boundary": {
        "current_minute": 0,
        "boundary_interval": 60,
        "expected": 60,  # Next boundary is 60 minutes away
    },
}


@pytest.mark.parametrize("case_id", BOUNDARY_TEST_CASES.keys())
def test_minutes_to_next_boundary(case_id: str) -> None:
    """Verify boundary calculation for different intervals."""
    case = BOUNDARY_TEST_CASES[case_id]
    result = minutes_to_next_boundary(case["current_minute"], case["boundary_interval"])
    assert result == case["expected"]


class AlignmentTestCase(TypedDict):
    """Test case for calculate_aligned_tier_counts."""

    description: str
    start_minute: int
    expected_t1_min: int  # Minimum expected T1 count
    expected_t2_min: int  # Minimum expected T2 count
    expected_t3_min: int  # Minimum expected T3 count


ALIGNMENT_TEST_CASES: dict[str, AlignmentTestCase] = {
    "aligned_to_hour": {
        "description": "Start at :00 - all tiers use minimum counts",
        "start_minute": 0,
        "expected_t1_min": 5,  # min_t1
        "expected_t2_min": 6,  # min_t2
        "expected_t3_min": 4,  # min_t3
    },
    "worst_case_t1": {
        "description": "Start at :26 - 4 min to :30, T1 expands",
        "start_minute": 26,
        "expected_t1_min": 5,  # Uses minimum since 4 < 5
        "expected_t2_min": 6,  # T1 ends at :31 -> need 4 steps (20 min) to get to :51, then 2 more (10 min) to :01?
        "expected_t3_min": 4,
    },
    "mid_interval": {
        "description": "Start at :43 - 2 min to :45",
        "start_minute": 43,
        "expected_t1_min": 5,  # min(5, 2) = 5
        "expected_t2_min": 6,
        "expected_t3_min": 4,
    },
}


@pytest.mark.parametrize("case_id", ALIGNMENT_TEST_CASES.keys())
def test_calculate_aligned_tier_counts(case_id: str) -> None:
    """Verify aligned tier counts meet minimum requirements."""
    case = ALIGNMENT_TEST_CASES[case_id]

    # Create datetime with specified minute
    start_time = datetime(2025, 1, 1, 12, case["start_minute"], 0, tzinfo=UTC)

    tier_durations = (1, 5, 30, 60)  # Standard tier durations in minutes
    min_counts = (5, 6, 4)  # Default minimums
    horizon_minutes = 5 * 24 * 60  # 5 days
    total_steps = calculate_worst_case_total_steps(min_counts, tier_durations, horizon_minutes)

    periods_seconds, tier_counts = calculate_aligned_tier_counts(
        start_time=start_time,
        tier_durations=tier_durations,
        min_counts=min_counts,
        total_steps=total_steps,
        horizon_minutes=horizon_minutes,
    )

    t1_count, t2_count, t3_count, _t4_count = tier_counts

    # Verify minimum counts are respected
    assert t1_count >= case["expected_t1_min"], f"{case['description']}: T1 count below minimum"
    assert t2_count >= case["expected_t2_min"], f"{case['description']}: T2 count below minimum"
    assert t3_count >= case["expected_t3_min"], f"{case['description']}: T3 count below minimum"

    # Verify total steps match
    assert sum(tier_counts) == total_steps, f"{case['description']}: Total steps mismatch"

    # Verify periods match tier counts
    assert len(periods_seconds) == sum(tier_counts), f"{case['description']}: Periods length mismatch"


def test_calculate_worst_case_total_steps() -> None:
    """Verify worst-case step calculation."""
    tier_durations = (1, 5, 30, 60)
    min_counts = (5, 6, 4)
    horizon_minutes = 5 * 24 * 60  # 5 days = 7200 minutes

    total_steps = calculate_worst_case_total_steps(min_counts, tier_durations, horizon_minutes)

    # Worst case:
    # T1: max(5, 5-1) = 5 steps * 1 min = 5 min
    # T2: max(6, (30-5)/5) = max(6, 5) = 6 steps * 5 min = 30 min
    # T3: max(4, (60-30)/30) = max(4, 1) = 4 steps * 30 min = 120 min
    # Total T1-T3: 155 minutes
    # Remaining: 7200 - 155 = 7045 minutes
    # T4 at 30-min granularity: ceil(7045/30) = 235 steps

    assert total_steps > 0
    assert total_steps == 5 + 6 + 4 + 235  # 250 total steps


def test_aligned_config_uses_alignment() -> None:
    """Verify tiers_to_periods_seconds uses alignment for new-style config."""
    config = {
        "tier_1_count": 5,
        "tier_1_duration": 1,
        "tier_2_count": 6,
        "tier_2_duration": 5,
        "tier_3_count": 4,
        "tier_3_duration": 30,
        "tier_4_duration": 60,
        "horizon_duration_minutes": 5 * 24 * 60,  # 5 days
    }

    # Mock time to a specific minute
    mock_time = datetime(2025, 1, 1, 12, 15, 0, tzinfo=UTC)

    with patch("custom_components.haeo.util.forecast_times.dt_util.utcnow", return_value=mock_time):
        periods = tiers_to_periods_seconds(config)

    # Should have periods for all tiers
    assert len(periods) > 0

    # Verify T1 periods are 60 seconds (1 minute)
    assert all(p == 60 for p in periods[:5])  # At least 5 T1 steps

    # Verify some T2 periods are 300 seconds (5 minutes)
    t2_start = 5  # After T1
    assert any(p == 300 for p in periods[t2_start : t2_start + 10])


def test_tier_boundaries_align_to_forecast_intervals() -> None:
    """Verify that tier transitions align with forecast data boundaries."""
    # Start at :43 - should align T2 to :45 boundary
    start_time = datetime(2025, 1, 1, 12, 43, 0, tzinfo=UTC)

    tier_durations = (1, 5, 30, 60)
    min_counts = (5, 6, 4)
    horizon_minutes = 2 * 24 * 60  # 2 days
    total_steps = calculate_worst_case_total_steps(min_counts, tier_durations, horizon_minutes)

    _periods_seconds, tier_counts = calculate_aligned_tier_counts(
        start_time=start_time,
        tier_durations=tier_durations,
        min_counts=min_counts,
        total_steps=total_steps,
        horizon_minutes=horizon_minutes,
    )

    t1_count = tier_counts[0]
    t1_minutes = t1_count * 1  # T1 duration is 1 minute

    # T1 should end at a 5-minute boundary
    t1_end_minute = (43 + t1_minutes) % 60
    assert t1_end_minute % 5 == 0, f"T1 end ({t1_end_minute}) should be on 5-min boundary"

    # T2 should end at a 30-minute boundary
    t2_count = tier_counts[1]
    t2_minutes = t2_count * 5
    t2_end_minute = (t1_end_minute + t2_minutes) % 60
    assert t2_end_minute % 30 == 0, f"T2 end ({t2_end_minute}) should be on 30-min boundary"
