"""Tests for calendar fuser - converting trip windows to boundary-aligned arrays."""

from datetime import UTC, datetime

import pytest

from custom_components.haeo.core.data.loader.calendar import TripWindow
from custom_components.haeo.core.data.util.calendar_fuser import compute_mid_trip_energy, fuse_trips_to_boundaries


def _dt(hour: int, minute: int = 0) -> datetime:
    """Create a UTC datetime on a fixed date for testing."""
    return datetime(2024, 1, 15, hour, minute, tzinfo=UTC)


# --- fuse_trips_to_boundaries tests ---


def test_fuse_no_trips() -> None:
    """No trips means all connected, zero capacity."""
    boundaries = [_dt(0), _dt(1), _dt(2), _dt(3)]
    connected, capacity = fuse_trips_to_boundaries([], boundaries)
    assert connected == [1.0, 1.0, 1.0, 1.0]
    assert capacity == [0.0, 0.0, 0.0, 0.0]


def test_fuse_empty_boundaries() -> None:
    """Empty horizon returns empty arrays."""
    connected, capacity = fuse_trips_to_boundaries([], [])
    assert connected == []
    assert capacity == []


def test_fuse_single_trip_aligned() -> None:
    """Trip aligned exactly to boundary times."""
    boundaries = [_dt(0), _dt(1), _dt(2), _dt(3), _dt(4)]
    trips = [TripWindow(start=_dt(1), end=_dt(3), distance=50.0, energy_kwh=10.0)]

    connected, capacity = fuse_trips_to_boundaries(trips, boundaries)

    # Trip from hour 1 to hour 3: boundaries 1,2 are disconnected
    assert connected == [1.0, 0.0, 0.0, 1.0, 1.0]
    assert capacity == [0.0, 10.0, 10.0, 0.0, 0.0]


def test_fuse_single_trip_mid_period() -> None:
    """Trip starting mid-period floors to period start."""
    boundaries = [_dt(0), _dt(1), _dt(2), _dt(3)]
    # Trip starts at 0:30, end at 1:30
    # Start floors to boundary 0 (period 0-1)
    # End ceils to boundary 2 (period 1-2)
    trips = [TripWindow(start=_dt(0, 30), end=_dt(1, 30), distance=30.0, energy_kwh=6.0)]

    connected, capacity = fuse_trips_to_boundaries(trips, boundaries)

    assert connected == [0.0, 0.0, 1.0, 1.0]
    assert capacity == [6.0, 6.0, 0.0, 0.0]


def test_fuse_multiple_trips() -> None:
    """Multiple non-overlapping trips."""
    boundaries = [_dt(0), _dt(1), _dt(2), _dt(3), _dt(4), _dt(5), _dt(6)]
    trips = [
        TripWindow(start=_dt(1), end=_dt(2), distance=20.0, energy_kwh=4.0),
        TripWindow(start=_dt(4), end=_dt(5), distance=30.0, energy_kwh=6.0),
    ]

    connected, capacity = fuse_trips_to_boundaries(trips, boundaries)

    assert connected == [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    assert capacity == [0.0, 4.0, 0.0, 0.0, 6.0, 0.0, 0.0]


def test_fuse_trip_outside_horizon() -> None:
    """Trip entirely outside the horizon is ignored."""
    boundaries = [_dt(2), _dt(3), _dt(4)]
    trips = [TripWindow(start=_dt(0), end=_dt(1), distance=50.0, energy_kwh=10.0)]

    connected, capacity = fuse_trips_to_boundaries(trips, boundaries)

    assert connected == [1.0, 1.0, 1.0]
    assert capacity == [0.0, 0.0, 0.0]


def test_fuse_trip_partially_overlaps_horizon_start() -> None:
    """Trip that starts before the horizon but ends within it."""
    boundaries = [_dt(2), _dt(3), _dt(4), _dt(5)]
    trips = [TripWindow(start=_dt(1), end=_dt(3), distance=50.0, energy_kwh=10.0)]

    connected, capacity = fuse_trips_to_boundaries(trips, boundaries)

    # Trip ends at hour 3 = boundary index 1, start clamped to 0
    # Range [0, 1) so only boundary 0 is disconnected
    assert connected == [0.0, 1.0, 1.0, 1.0]
    assert capacity == [10.0, 0.0, 0.0, 0.0]


# --- compute_mid_trip_energy tests ---


def test_mid_trip_no_progress() -> None:
    """No odometer update means full energy remaining (conservative)."""
    remaining, initial_pct = compute_mid_trip_energy(
        current_odometer=1000.0,
        disconnect_odometer=1000.0,
        energy_per_distance=0.2,
        total_trip_energy=10.0,
    )
    assert remaining == 10.0
    assert initial_pct == 0.0


def test_mid_trip_partial_progress() -> None:
    """Odometer shows partial progress, energy partially consumed."""
    remaining, initial_pct = compute_mid_trip_energy(
        current_odometer=1025.0,
        disconnect_odometer=1000.0,
        energy_per_distance=0.2,
        total_trip_energy=10.0,
    )
    # 25 km * 0.2 kWh/km = 5.0 kWh consumed
    assert remaining == pytest.approx(5.0)
    assert initial_pct == pytest.approx(50.0)


def test_mid_trip_complete() -> None:
    """Odometer shows trip distance met or exceeded."""
    remaining, initial_pct = compute_mid_trip_energy(
        current_odometer=1050.0,
        disconnect_odometer=1000.0,
        energy_per_distance=0.2,
        total_trip_energy=10.0,
    )
    assert remaining == 0.0
    assert initial_pct == 100.0


def test_mid_trip_exceeds_total() -> None:
    """Odometer shows more distance than expected - capped at 100%."""
    remaining, initial_pct = compute_mid_trip_energy(
        current_odometer=1100.0,
        disconnect_odometer=1000.0,
        energy_per_distance=0.2,
        total_trip_energy=10.0,
    )
    assert remaining == 0.0
    assert initial_pct == 100.0


def test_mid_trip_zero_total_energy() -> None:
    """Zero trip energy means already complete (100%)."""
    remaining, initial_pct = compute_mid_trip_energy(
        current_odometer=1000.0,
        disconnect_odometer=1000.0,
        energy_per_distance=0.2,
        total_trip_energy=0.0,
    )
    assert remaining == 0.0
    assert initial_pct == 100.0


def test_mid_trip_negative_odometer_delta() -> None:
    """Negative odometer delta treated as zero progress."""
    remaining, initial_pct = compute_mid_trip_energy(
        current_odometer=990.0,
        disconnect_odometer=1000.0,
        energy_per_distance=0.2,
        total_trip_energy=10.0,
    )
    assert remaining == 10.0
    assert initial_pct == 0.0
