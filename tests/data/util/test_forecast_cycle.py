"""Tests for forecast cycle normalisation."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from custom_components.haeo.data.util.forecast_cycle import normalize_forecast_cycle

SECONDS_PER_HOUR = 3600


@dataclass(slots=True)
class ForecastCycleTestCase:
    """Container describing a forecast cycling scenario."""

    description: str
    expectation: str
    now: int
    forecast: list[tuple[int, float]]
    expected: list[tuple[int, float]]
    expected_cycle_length: int


def _block(*, time_range: tuple[int, int], start_value: float) -> list[tuple[int, float]]:
    return [(hour, start_value + (hour - time_range[0])) for hour in range(time_range[0], time_range[1])]


test_cases = [
    ForecastCycleTestCase(
        description="24 hour forecast starting from now",
        expectation="Same forecast returned",
        now=0,
        forecast=_block(time_range=(0, 24), start_value=0.0),
        expected=_block(time_range=(0, 24), start_value=0.0),
        expected_cycle_length=24,
    ),
    ForecastCycleTestCase(
        description="24 hour forecast starting mid way through",
        expectation="Times earlier than now are wrapped to the end",
        now=6,
        forecast=_block(time_range=(0, 24), start_value=0.0),
        expected=[
            *_block(time_range=(6 + 0, 6 + 18), start_value=6.0),
            *_block(time_range=(6 + 18, 6 + 24), start_value=0.0),
        ],
        expected_cycle_length=24,
    ),
    ForecastCycleTestCase(
        description="48 hour forecast starting from now",
        expectation="First 48 hours are identical",
        now=0,
        forecast=_block(time_range=(0, 48), start_value=0.0),
        expected=_block(time_range=(0, 48), start_value=0.0),
        expected_cycle_length=48,
    ),
    ForecastCycleTestCase(
        description="48 hour forecast starting mid way through",
        expectation="Use the forecast, then wrap to the beginning to fill 48 hours",
        now=18,
        forecast=_block(time_range=(0, 48), start_value=0.0),
        expected=[
            *_block(time_range=(18 + 0, 18 + 30), start_value=18.0),
            *_block(time_range=(18 + 30, 18 + 48), start_value=0.0),
        ],
        expected_cycle_length=48,
    ),
    ForecastCycleTestCase(
        description="Single value forecast starting at now",
        expectation="Same value returned for this 24 hour block",
        now=12,
        forecast=[(12, 1337)],
        expected=[(12, 1337)],
        expected_cycle_length=24,
    ),
    ForecastCycleTestCase(
        description="Single value forecast starting at a different time",
        expectation="Single value placed at the next valid occurrence in the cycle",
        now=24,
        forecast=[(12, 1337)],
        expected=[(36, 1337)],
        expected_cycle_length=24,
    ),
    ForecastCycleTestCase(
        description="12 hour forecast starting from now",
        expectation="Same forecast returned",
        now=0,
        forecast=_block(time_range=(0, 12), start_value=0.0),
        expected=_block(time_range=(0, 12), start_value=0.0),
        expected_cycle_length=24,
    ),
    ForecastCycleTestCase(
        description="12 hour forecast starting mid way through",
        expectation="Times earlier than now are wrapped to the end at their same time of day",
        now=6,
        forecast=_block(time_range=(0, 12), start_value=0.0),
        expected=[
            *_block(time_range=(6 + 0, 6 + 6), start_value=6.0),
            *_block(time_range=(6 + 18, 6 + 24), start_value=0.0),
        ],
        expected_cycle_length=24,
    ),
    ForecastCycleTestCase(
        description="36 hour forecast starting from now",
        expectation="First 36 hours are identical, then repeat the earliest matching 12 hours to fill 48 hours",
        now=0,
        forecast=_block(time_range=(0, 36), start_value=0.0),
        expected=[
            *_block(time_range=(0, 36), start_value=0.0),
            *_block(time_range=(36, 48), start_value=12.0),
        ],
        expected_cycle_length=48,
    ),
    ForecastCycleTestCase(
        description="36 hour forecast starting mid way through",
        expectation="Use the forecast, then wrap to the earliest matching timestamp and repeat to fill 48 hours",
        now=18,
        forecast=_block(time_range=(0, 36), start_value=0.0),
        expected=[
            *_block(time_range=(18 + 0, 18 + 18), start_value=18.0),  # To the end of the original forecast
            *_block(time_range=(18 + 18, 18 + 30), start_value=12.0),  # Cycle to complete the 48 original hours
            *_block(time_range=(18 + 30, 18 + 48), start_value=0.0),  # Start from the beginning
        ],
        expected_cycle_length=48,
    ),
    ForecastCycleTestCase(
        description="37 hour forecast starting from now",
        expectation="First 37 hours are identical, then repeat from earliest matching hour to fill 48 hours",
        now=0,
        forecast=_block(time_range=(0, 37), start_value=0.0),
        expected=[
            *_block(time_range=(0, 37), start_value=0.0),
            *_block(time_range=(37, 48), start_value=13.0),
        ],
        expected_cycle_length=48,
    ),
    ForecastCycleTestCase(
        description="37 hour forecast starting mid way through",
        expectation="Use the forecast, then wrap to the earliest matching timestamp and repeat to fill 48 hours",
        now=18,
        forecast=_block(time_range=(0, 37), start_value=0.0),
        expected=[
            *_block(time_range=(18 + 0, 18 + 19), start_value=18.0),
            *_block(time_range=(18 + 19, 18 + 30), start_value=13.0),
            *_block(time_range=(18 + 30, 18 + 48), start_value=0.0),
        ],
        expected_cycle_length=48,
    ),
    ForecastCycleTestCase(
        description="85 hour forecast starting mid way through",
        expectation=(
            "Use the forecast, then wrap to the earliest matching timestamp and repeat to fill the rounding days"
        ),
        now=54,
        forecast=_block(time_range=(0, 87), start_value=0.0),
        expected=[
            *_block(time_range=(54 + 0, 54 + 33), start_value=54.0),
            *_block(time_range=(54 + 33, 54 + 42), start_value=15.0),
            *_block(time_range=(54 + 42, 54 + 96), start_value=0.0),
        ],
        expected_cycle_length=96,
    ),
]

offset_hours_cases = [0, 1, 24, 39]
offset_cycles_cases = [0, 5, -5]


@pytest.mark.parametrize("offset_cycles", offset_cycles_cases, ids=lambda case: f"offset_cycles={case}")
@pytest.mark.parametrize("offset_hours", offset_hours_cases, ids=lambda oh: f"offset_hours={oh}")
@pytest.mark.parametrize("case", test_cases, ids=lambda case: case.description)
def test_normalize_forecast_cycle(offset_hours: int, offset_cycles: int, case: ForecastCycleTestCase) -> None:
    """Ensure the normalised forecast reproduces the expected horizon."""

    cycle_offset = offset_cycles * case.expected_cycle_length

    # For offset cycles, we shift the current time forward/backwards by full cycle lengths
    current_time = SECONDS_PER_HOUR * (case.now + offset_hours + cycle_offset)
    forecast = [((hour + offset_hours) * SECONDS_PER_HOUR, value) for hour, value in case.forecast]

    cycle, cycle_length = normalize_forecast_cycle(forecast, current_time)

    expected = [((hour + offset_hours + cycle_offset) * SECONDS_PER_HOUR, value) for hour, value in case.expected]
    expected_cycle_length = case.expected_cycle_length * SECONDS_PER_HOUR

    assert cycle == expected
    assert cycle_length == expected_cycle_length
