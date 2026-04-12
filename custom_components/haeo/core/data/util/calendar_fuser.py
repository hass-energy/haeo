"""Fuse calendar trip windows into horizon-aligned time-series arrays."""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from datetime import datetime

from custom_components.haeo.core.data.loader.calendar import TripWindow


def fuse_trips_to_boundaries(
    trips: list[TripWindow],
    horizon_times: Sequence[datetime],
) -> tuple[list[float], list[float]]:
    """Convert trip windows into boundary-aligned time-series arrays.

    Produces two arrays aligned to the optimization horizon boundaries:
    - connected_flag: 1.0 when the vehicle is at home, 0.0 when away
    - trip_capacity: trip battery capacity (kWh) at each boundary

    Aliasing rules:
    - Trip start snaps to the start of the containing period (floor)
    - Trip end snaps to the end of the containing period (ceiling)
    - This ensures no overlap between charging and driving in a single period

    Args:
        trips: Sorted list of trip windows (non-overlapping).
        horizon_times: n+1 boundary timestamps defining n periods.

    Returns:
        Tuple of (connected_flag, trip_capacity), each with n+1 values.

    """
    n_boundaries = len(horizon_times)
    if n_boundaries == 0:
        return ([], [])

    connected = [1.0] * n_boundaries
    capacity = [0.0] * n_boundaries

    for trip in trips:
        # Find the period boundaries that the trip spans
        # Trip start floors to the start of its containing period
        start_idx = _floor_boundary_index(trip.start, horizon_times)
        # Trip end ceils to the end of its containing period
        end_idx = _ceil_boundary_index(trip.end, horizon_times)

        if start_idx >= n_boundaries or end_idx <= 0:
            continue

        # Clamp to horizon range
        start_idx = max(start_idx, 0)
        end_idx = min(end_idx, n_boundaries)

        # Set disconnected and trip capacity for boundaries in the trip range
        for i in range(start_idx, end_idx):
            connected[i] = 0.0
            capacity[i] = trip.energy_kwh

    return (connected, capacity)


def compute_mid_trip_energy(
    current_odometer: float,
    disconnect_odometer: float,
    energy_per_distance: float,
    total_trip_energy: float,
) -> tuple[float, float]:
    """Compute remaining trip energy and initial charge for mid-trip tracking.

    Uses the odometer delta to estimate energy consumed so far.
    If no odometer update is available (delta=0), conservatively assumes
    no progress has been made — full trip energy is still required.

    Args:
        current_odometer: Current odometer reading.
        disconnect_odometer: Odometer reading when vehicle was disconnected.
        energy_per_distance: Energy consumption per unit distance (kWh/unit).
        total_trip_energy: Total expected energy for the full trip (kWh).

    Returns:
        Tuple of (remaining_capacity_kwh, initial_charge_percentage)
        where initial_charge_percentage is 0-100.

    """
    distance_traveled = max(0.0, current_odometer - disconnect_odometer)
    energy_consumed = distance_traveled * energy_per_distance
    remaining = max(0.0, total_trip_energy - energy_consumed)

    initial_charge_pct = min(100.0, (energy_consumed / total_trip_energy) * 100.0) if total_trip_energy > 0.0 else 100.0

    return (remaining, initial_charge_pct)


def _floor_boundary_index(dt: datetime, boundaries: Sequence[datetime]) -> int:
    """Find the boundary index at or before dt (floor to period start).

    Returns the index of the last boundary that is <= dt.
    """
    idx = bisect.bisect_right(boundaries, dt) - 1
    return max(idx, 0)


def _ceil_boundary_index(dt: datetime, boundaries: Sequence[datetime]) -> int:
    """Find the boundary index at or after dt (ceil to period end).

    Returns the index of the first boundary that is >= dt.
    """
    idx = bisect.bisect_left(boundaries, dt)
    return min(idx, len(boundaries))
