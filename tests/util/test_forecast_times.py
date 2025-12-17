"""Tests for forecast time generation utilities."""

from datetime import UTC, datetime
from typing import TypedDict
from unittest.mock import patch

import pytest

from custom_components.haeo.util.forecast_times import (
    generate_forecast_timestamps,
    generate_forecast_timestamps_from_config,
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
        "description": "single period generates two fence posts",
        "periods_seconds": [60],
        "start_time": 0.0,
        "expected": (0.0, 60.0),
    },
    "multiple_periods": {
        "description": "multiple periods generate n+1 fence posts",
        "periods_seconds": [60, 60, 300],
        "start_time": 0.0,
        "expected": (0.0, 60.0, 120.0, 420.0),
    },
    "empty_periods": {
        "description": "empty periods generate single fence post at start",
        "periods_seconds": [],
        "start_time": 100.0,
        "expected": (100.0,),
    },
    "nonzero_start": {
        "description": "fence posts are relative to start time",
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
    assert len(result) == 3  # 2 periods + 1 = 3 fence posts
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
    assert len(result) == 3  # 2 periods + 1 = 3 fence posts
    assert result[1] == expected_start + 60.0
    assert result[2] == expected_start + 120.0
