"""Tests for forecast previews."""

import pytest

from custom_components.haeo.core.data.util.forecast_preview import forecast_preview

SERIES = [(0.0, 0.0), (10.0, 10.0), (20.0, 0.0)]


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        pytest.param(10.0, (10.0, 5.0, 0.0), id="from_now"),
        pytest.param(-5.0, (0.0, 10.0, 0.0), id="not_started"),
        pytest.param(30.0, (0.0, 10.0, 0.0), id="ended"),
    ],
)
def test_preview_samples_from_now_to_the_end(now: float, expected: tuple[float, ...]) -> None:
    """A preview spans now to the forecast's end, or the whole forecast when now is outside it."""
    assert forecast_preview(SERIES, now, points=3) == expected


def test_preview_rounds_to_four_significant_figures() -> None:
    """Values are rounded to keep the preview small."""
    assert forecast_preview([(0.0, 1.23456), (1.0, 1.23456)], 0.0, points=2) == (1.235, 1.235)


@pytest.mark.parametrize(
    "series",
    [pytest.param([(0.0, 1.0)], id="one_point"), pytest.param([(0.0, 1.0), (1.0, float("inf"))], id="one_finite")],
)
def test_fewer_than_two_points_have_no_preview(series: list[tuple[float, float]]) -> None:
    """A line needs two points."""
    assert forecast_preview(series, 0.0) == ()


def test_points_that_are_not_finite_are_left_out() -> None:
    """A missing value read as NaN does not reach the preview."""
    assert forecast_preview([(0.0, 0.0), (5.0, float("nan")), (10.0, 10.0)], 0.0, points=3) == (0.0, 5.0, 10.0)
