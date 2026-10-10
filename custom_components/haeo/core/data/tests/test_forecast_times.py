"""Tests for forecast time generation utilities."""

from datetime import UTC, datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

from freezegun import freeze_time
import pytest

from conftest import FakeEntityState
from custom_components.haeo.core.data.forecast_times import (
    calculate_aligned_tier_counts,
    calculate_total_steps,
    forecast_boundaries,
    generate_forecast_timestamps,
    minutes_to_next_boundary,
    periods_seconds_from_boundaries,
    preset_periods_seconds,
)


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


@freeze_time(datetime(2025, 1, 1, 12, 0, 30, tzinfo=UTC))
def test_generate_forecast_timestamps_default_start_time() -> None:
    """Verify default start_time uses current time with rounding."""
    periods_seconds = [60, 60]
    expected_start = 1735732800.0  # 2025-01-01 12:00:00 UTC (rounded from 12:00:30)

    result = generate_forecast_timestamps(periods_seconds)

    assert result[0] == expected_start
    assert len(result) == 3  # 2 periods + 1 = 3 boundaries
    assert result[1] == expected_start + 60.0
    assert result[2] == expected_start + 120.0


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


@pytest.mark.parametrize("preset", ["2_days", "3_days", "5_days", "7_days"])
def test_preset_produces_constant_step_count_for_all_minutes(preset: str) -> None:
    """Verify each preset produces the same step count regardless of starting minute.

    The time alignment algorithm adjusts tier counts to align with forecast boundaries,
    but the total number of steps must remain constant for a given preset. This ensures
    consistent solver performance regardless of when optimization starts.
    """

    with freeze_time(datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)):
        periods = preset_periods_seconds(preset)
        assert len(periods) > 0
        assert periods[0] == 60

    step_counts: list[int] = []

    for minute in range(60):
        with freeze_time(datetime(2025, 1, 1, 12, minute, 0, tzinfo=UTC)):
            periods = preset_periods_seconds(preset)
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


ADELAIDE = ZoneInfo("Australia/Adelaide")


def _t4_boundary_local_minutes(
    periods_seconds: list[int],
    start_ts: float,
    tz: ZoneInfo,
) -> list[int]:
    """Return local minutes-of-hour for each end-of-period T4 (3600s) boundary."""
    timestamps = generate_forecast_timestamps(periods_seconds, start_ts)
    minutes: list[int] = []
    for index, period in enumerate(periods_seconds):
        if period == 3600:
            local_dt = datetime.fromtimestamp(timestamps[index + 1], tz=tz)
            minutes.append(local_dt.minute)
    return minutes


def test_adelaide_utc_start_time_misaligns_t4_to_half_hour() -> None:
    """UTC start_time at Adelaide noon aligns T4 to :30 local (issue #457 bug)."""
    local_noon = datetime(2025, 6, 2, 12, 0, 0, tzinfo=ADELAIDE)
    utc_start = local_noon.astimezone(UTC)

    periods = preset_periods_seconds("5_days", start_time=utc_start)
    t4_minutes = _t4_boundary_local_minutes(periods, utc_start.timestamp(), ADELAIDE)

    assert t4_minutes, "expected at least one T4 boundary"
    assert t4_minutes[0] == 30, "UTC alignment should place first T4 boundary at :30 local"


def test_adelaide_local_start_time_aligns_t4_to_hour() -> None:
    """Local start_time at Adelaide noon aligns T4 to :00 local."""
    local_noon = datetime(2025, 6, 2, 12, 0, 0, tzinfo=ADELAIDE)

    periods = preset_periods_seconds("5_days", start_time=local_noon)
    t4_minutes = _t4_boundary_local_minutes(periods, local_noon.timestamp(), ADELAIDE)

    assert t4_minutes, "expected at least one T4 boundary"
    assert t4_minutes[0] == 0, "local alignment should place first T4 boundary at :00 local"
    assert all(minute == 0 for minute in t4_minutes), "all T4 boundaries should fall on local hour"


@pytest.mark.parametrize("preset", ["2_days", "3_days", "5_days", "7_days"])
def test_preset_produces_exact_horizon_duration(preset: str) -> None:
    """Verify total period duration exactly matches horizon minutes.

    The trailing step ensures that for N whole-day horizons, the optimization
    ends at the same minute of the hour it started.
    """
    expected_seconds = PRESET_HORIZON_MINUTES[preset] * 60

    # Test all 60 possible start minutes
    for minute in range(60):
        with freeze_time(datetime(2025, 1, 1, 12, minute, 0, tzinfo=UTC)):
            periods = preset_periods_seconds(preset)
            total_seconds = sum(periods)
            assert total_seconds == expected_seconds, (
                f"Preset {preset}: minute {minute} produced {total_seconds}s, expected {expected_seconds}s"
            )


def _forecast_state(forecast: object) -> FakeEntityState:
    """Return an entity state with the given forecast attribute."""
    return FakeEntityState(entity_id="sensor.horizon", state="0", attributes={"forecast": forecast})


@pytest.mark.parametrize(
    ("forecast", "expected"),
    [
        pytest.param(
            [
                {"time": "2025-01-01T12:00:00+00:00", "value": 0},
                {"time": "2025-01-01T12:30:00+00:00", "value": 1},
                {"time": "2025-01-01T13:30:00+00:00", "value": 2.5},
            ],
            (1735732800.0, 1735734600.0, 1735738200.0),
            id="iso_strings",
        ),
        pytest.param(
            [
                {"time": datetime(2025, 1, 1, 12, 0, tzinfo=UTC), "value": 0},
                {"time": datetime(2025, 1, 1, 12, 5, tzinfo=UTC), "value": 0},
            ],
            (1735732800.0, 1735733100.0),
            id="datetimes",
        ),
        pytest.param(
            [{"time": datetime(2025, 1, 1, 12, 0, tzinfo=UTC)}, {"time": datetime(2025, 1, 1, 13, 0, tzinfo=UTC)}],
            (1735732800.0, 1735736400.0),
            id="horizon_sensor_times_only",
        ),
    ],
)
def test_forecast_boundaries_reads_forecast_times(forecast: object, expected: tuple[float, ...]) -> None:
    """Each forecast point's time is a period boundary."""
    assert forecast_boundaries(_forecast_state(forecast)) == expected


@pytest.mark.parametrize(
    ("state", "match"),
    [
        pytest.param(
            FakeEntityState(entity_id="sensor.horizon", state="0", attributes={}),
            "has no forecast of times",
            id="no_forecast",
        ),
        pytest.param(_forecast_state("2025-01-01T12:00:00+00:00"), "has no forecast of times", id="string_forecast"),
        pytest.param(
            _forecast_state([{"time": "2025-01-01T12:00:00+00:00"}, {"value": 0}]),
            "has no forecast of times",
            id="point_without_time",
        ),
        pytest.param(
            _forecast_state([{"time": "2025-01-01T12:00:00+00:00", "value": 0}]),
            "at least two increasing times",
            id="single_point",
        ),
        pytest.param(
            _forecast_state(
                [
                    {"time": "2025-01-01T12:00:00+00:00", "value": 0},
                    {"time": "2025-01-01T12:00:00+00:00", "value": 0},
                ]
            ),
            "at least two increasing times",
            id="repeated_time",
        ),
        pytest.param(
            _forecast_state(
                [
                    {"time": "2025-01-01T13:00:00+00:00", "value": 0},
                    {"time": "2025-01-01T12:00:00+00:00", "value": 0},
                ]
            ),
            "at least two increasing times",
            id="decreasing_times",
        ),
    ],
)
def test_forecast_boundaries_rejects_unusable_forecasts(state: FakeEntityState, match: str) -> None:
    """A state without a usable forecast of times raises ValueError naming the entity."""
    with pytest.raises(ValueError, match=f"sensor.horizon .*{match}"):
        forecast_boundaries(state)


@pytest.mark.parametrize(
    ("boundaries", "expected"),
    [
        pytest.param((0.0, 60.0), [60], id="single_period"),
        pytest.param((1000.0, 1300.0, 3100.0, 6700.0), [300, 1800, 3600], id="mixed_periods"),
        pytest.param((0.0,), [], id="single_boundary"),
    ],
)
def test_periods_seconds_from_boundaries(boundaries: tuple[float, ...], expected: list[int]) -> None:
    """Periods are the gaps between consecutive boundaries."""
    assert periods_seconds_from_boundaries(boundaries) == expected


@pytest.mark.parametrize("preset", ["2_days", "3_days", "5_days", "7_days"])
def test_preset_periods_seconds_defaults_to_now(preset: str) -> None:
    """Without a start time the preset aligns to the current time."""
    now = datetime(2025, 1, 1, 12, 17, 0, tzinfo=UTC)
    with freeze_time(now):
        assert preset_periods_seconds(preset) == preset_periods_seconds(preset, start_time=now)
