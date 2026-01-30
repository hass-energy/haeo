"""Tests for apply_interpolation_mode utility."""

import numpy as np
import pytest

from custom_components.haeo.data.loader.extractors.utils.apply_interpolation_mode import (
    EPSILON,
    apply_interpolation_mode,
)
from custom_components.haeo.data.util import InterpolationMode


class TestLinearMode:
    """Tests for LINEAR interpolation mode."""

    def test_returns_copy_of_original_data(self) -> None:
        """Linear mode returns the original data unchanged."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.LINEAR)
        assert result == data

    def test_empty_data_returns_empty(self) -> None:
        """Empty input returns empty output."""
        result = apply_interpolation_mode([], InterpolationMode.LINEAR)
        assert result == []

    def test_single_point_returns_unchanged(self) -> None:
        """Single point input returns unchanged."""
        data = [(0.0, 100.0)]
        result = apply_interpolation_mode(data, InterpolationMode.LINEAR)
        assert result == [(0.0, 100.0)]


class TestPreviousMode:
    """Tests for PREVIOUS interpolation mode (step function, hold previous value)."""

    def test_two_points_adds_synthetic_before_second(self) -> None:
        """Two points with previous mode adds synthetic point before second."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.PREVIOUS)

        # Expected: original first, synthetic just before second, original second
        assert len(result) == 3
        assert result[0] == (0.0, 100.0)
        assert result[1] == (3600.0 - EPSILON, 100.0)  # Synthetic with previous value
        assert result[2] == (3600.0, 200.0)

    def test_three_points_adds_synthetic_before_each_transition(self) -> None:
        """Three points with previous mode adds synthetic before each transition."""
        data = [(0.0, 100.0), (3600.0, 200.0), (7200.0, 300.0)]
        result = apply_interpolation_mode(data, InterpolationMode.PREVIOUS)

        assert len(result) == 5
        assert result[0] == (0.0, 100.0)
        assert result[1] == (3600.0 - EPSILON, 100.0)
        assert result[2] == (3600.0, 200.0)
        assert result[3] == (7200.0 - EPSILON, 200.0)
        assert result[4] == (7200.0, 300.0)

    def test_single_point_returns_unchanged(self) -> None:
        """Single point input returns unchanged for previous mode."""
        data = [(0.0, 100.0)]
        result = apply_interpolation_mode(data, InterpolationMode.PREVIOUS)
        assert result == [(0.0, 100.0)]

    def test_interpolation_at_midpoint_gives_previous_value(self) -> None:
        """Verify linear interpolation on the result gives step behavior."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.PREVIOUS)

        timestamps = [t for t, _ in result]
        values = [v for _, v in result]

        # Interpolate at midpoint (1800 seconds)
        midpoint_value = np.interp(1800.0, timestamps, values)
        assert midpoint_value == pytest.approx(100.0, abs=0.01)

        # Interpolate just before transition
        before_transition = np.interp(3599.0, timestamps, values)
        assert before_transition == pytest.approx(100.0, abs=0.01)

        # Interpolate at transition
        at_transition = np.interp(3600.0, timestamps, values)
        assert at_transition == pytest.approx(200.0, abs=0.01)


class TestNextMode:
    """Tests for NEXT interpolation mode (step function, jump to next value)."""

    def test_two_points_adds_synthetic_after_first(self) -> None:
        """Two points with next mode adds synthetic point after first."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.NEXT)

        # Expected: original first, synthetic just after first, original second
        assert len(result) == 3
        assert result[0] == (0.0, 100.0)
        assert result[1] == (0.0 + EPSILON, 200.0)  # Synthetic with next value
        assert result[2] == (3600.0, 200.0)

    def test_three_points_adds_synthetic_after_each(self) -> None:
        """Three points with next mode adds synthetic after each except last."""
        data = [(0.0, 100.0), (3600.0, 200.0), (7200.0, 300.0)]
        result = apply_interpolation_mode(data, InterpolationMode.NEXT)

        assert len(result) == 5
        assert result[0] == (0.0, 100.0)
        assert result[1] == (0.0 + EPSILON, 200.0)
        assert result[2] == (3600.0, 200.0)
        assert result[3] == (3600.0 + EPSILON, 300.0)
        assert result[4] == (7200.0, 300.0)

    def test_interpolation_at_midpoint_gives_next_value(self) -> None:
        """Verify linear interpolation on the result gives forward step behavior."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.NEXT)

        timestamps = [t for t, _ in result]
        values = [v for _, v in result]

        # Interpolate at midpoint (1800 seconds) - should be 200 (next value)
        midpoint_value = np.interp(1800.0, timestamps, values)
        assert midpoint_value == pytest.approx(200.0, abs=0.01)

        # Interpolate at start
        at_start = np.interp(0.0, timestamps, values)
        assert at_start == pytest.approx(100.0, abs=0.01)

        # Interpolate just after start
        after_start = np.interp(0.01, timestamps, values)
        assert after_start == pytest.approx(200.0, abs=0.01)


class TestNearestMode:
    """Tests for NEAREST interpolation mode (use closest point's value)."""

    def test_two_points_adds_transition_at_midpoint(self) -> None:
        """Two points with nearest mode adds transition at midpoint."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.NEAREST)

        midpoint = 1800.0
        # Expected: original, synthetic before midpoint, synthetic at midpoint, original
        assert len(result) == 4
        assert result[0] == (0.0, 100.0)
        assert result[1] == (midpoint - EPSILON, 100.0)
        assert result[2] == (midpoint, 200.0)
        assert result[3] == (3600.0, 200.0)

    def test_interpolation_before_midpoint_gives_previous_value(self) -> None:
        """Before midpoint, should use previous point's value."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.NEAREST)

        timestamps = [t for t, _ in result]
        values = [v for _, v in result]

        # Interpolate before midpoint (900 seconds)
        value = np.interp(900.0, timestamps, values)
        assert value == pytest.approx(100.0, abs=0.01)

    def test_interpolation_after_midpoint_gives_next_value(self) -> None:
        """After midpoint, should use next point's value."""
        data = [(0.0, 100.0), (3600.0, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.NEAREST)

        timestamps = [t for t, _ in result]
        values = [v for _, v in result]

        # Interpolate after midpoint (2700 seconds)
        value = np.interp(2700.0, timestamps, values)
        assert value == pytest.approx(200.0, abs=0.01)

    def test_three_points_adds_transitions_at_each_midpoint(self) -> None:
        """Three points with nearest mode adds transitions at each midpoint."""
        data = [(0.0, 100.0), (3600.0, 200.0), (7200.0, 300.0)]
        result = apply_interpolation_mode(data, InterpolationMode.NEAREST)

        # Midpoints are at 1800 and 5400
        assert len(result) == 7
        assert result[0] == (0.0, 100.0)
        assert result[1] == (1800.0 - EPSILON, 100.0)
        assert result[2] == (1800.0, 200.0)
        assert result[3] == (3600.0, 200.0)
        assert result[4] == (5400.0 - EPSILON, 200.0)
        assert result[5] == (5400.0, 300.0)
        assert result[6] == (7200.0, 300.0)


class TestEdgeCases:
    """Edge case tests for apply_interpolation_mode."""

    def test_empty_data_all_modes(self) -> None:
        """Empty input returns empty output for all modes."""
        for mode in InterpolationMode:
            result = apply_interpolation_mode([], mode)
            assert result == []

    def test_single_point_all_modes(self) -> None:
        """Single point input returns unchanged for all modes."""
        data = [(0.0, 100.0)]
        for mode in InterpolationMode:
            result = apply_interpolation_mode(data, mode)
            assert result == [(0.0, 100.0)]

    def test_same_value_points(self) -> None:
        """Points with same value should still get synthetic points."""
        data = [(0.0, 100.0), (3600.0, 100.0)]

        result = apply_interpolation_mode(data, InterpolationMode.PREVIOUS)
        assert len(result) == 3  # Synthetic point still added

        result = apply_interpolation_mode(data, InterpolationMode.NEXT)
        assert len(result) == 3

    def test_negative_values(self) -> None:
        """Negative values are handled correctly."""
        data = [(0.0, -100.0), (3600.0, -200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.PREVIOUS)
        assert result[1] == (3600.0 - EPSILON, -100.0)

    def test_very_close_timestamps(self) -> None:
        """Timestamps closer than EPSILON should still work."""
        data = [(0.0, 100.0), (0.0001, 200.0)]
        result = apply_interpolation_mode(data, InterpolationMode.PREVIOUS)
        # Should still add synthetic points even if very close
        assert len(result) == 3
