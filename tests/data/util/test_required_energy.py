"""Unit tests for required energy calculation.

The required energy represents the maximum battery capacity needed at each
timestep to survive until solar (or other uncontrollable generation) recharges
the battery.

The calculation uses a "maximum drawdown" approach:
1. Aggregates all load forecasts
2. Aggregates all uncontrollable generation (solar)
3. Computes net energy = (solar - load) * period (can be positive or negative)
4. For each timestep, finds the maximum drawdown from that point forward
   (the deepest point the battery would drain to before being recharged)
"""

from collections.abc import Mapping
from typing import cast

import pytest

from custom_components.haeo.data import calculate_required_energy
from custom_components.haeo.elements import ElementConfigData


def test_empty_participants_returns_zero() -> None:
    """Test that empty participants returns a single zero value."""
    result = calculate_required_energy({}, [1.0, 1.0, 1.0])
    # n_periods + 1 values, all zeros since no load or solar
    assert result == [0.0, 0.0, 0.0, 0.0]


def test_empty_periods_returns_single_zero() -> None:
    """Test that empty periods returns a single zero value."""
    result = calculate_required_energy({}, [])
    assert result == [0.0]


def test_load_only_no_solar() -> None:
    """Test with load only, no solar - all load becomes required energy."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [2.0, 1.0, 0.5],  # kW
            }
        },
    )
    periods_hours = [1.0, 1.0, 1.0]  # 1 hour each

    result = calculate_required_energy(participants, periods_hours)

    # Net energy = -load = [-2.0, -1.0, -0.5] kWh (all deficit, no solar)
    # From t=0: running balance = [-2, -3, -3.5], max drawdown = 3.5
    # From t=1: running balance = [-1, -1.5], max drawdown = 1.5
    # From t=2: running balance = [-0.5], max drawdown = 0.5
    assert result == pytest.approx([3.5, 1.5, 0.5, 0.0])


def test_solar_covers_all_load() -> None:
    """Test with solar exceeding load - no required energy."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [1.0, 1.0, 1.0],  # kW
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [2.0, 2.0, 2.0],  # kW (exceeds load)
            },
        },
    )
    periods_hours = [1.0, 1.0, 1.0]

    result = calculate_required_energy(participants, periods_hours)

    # Solar exceeds load in all periods, so no required energy
    assert result == pytest.approx([0.0, 0.0, 0.0, 0.0])


def test_solar_partially_covers_load() -> None:
    """Test with solar partially covering load."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [3.0, 2.0, 1.0],  # kW
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [1.0, 1.0, 2.0],  # kW
            },
        },
    )
    periods_hours = [1.0, 1.0, 1.0]

    result = calculate_required_energy(participants, periods_hours)

    # Net energy = (solar - load) * period = [-2.0, -1.0, +1.0] kWh
    # From t=0: running balance = [-2, -3, -2], max drawdown = 3
    # From t=1: running balance = [-1, 0], max drawdown = 1
    # From t=2: running balance = [+1], max drawdown = 0
    assert result == pytest.approx([3.0, 1.0, 0.0, 0.0])


def test_overnight_scenario() -> None:
    """Test realistic overnight scenario where solar drops to zero."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [2.0, 1.0, 0.5, 1.0, 1.0],  # Evening to morning
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [0.0, 0.0, 0.0, 2.0, 5.0],  # No solar until morning
            },
        },
    )
    periods_hours = [2.0, 4.0, 6.0, 4.0, 4.0]  # Variable length periods

    result = calculate_required_energy(participants, periods_hours)

    # Net power = solar - load = [-2.0, -1.0, -0.5, +1.0, +4.0]
    # Net energy = net_power * period = [-4.0, -4.0, -3.0, +4.0, +16.0] kWh
    # From t=0: running balance = [-4, -8, -11, -7, +9], max drawdown = 11
    # From t=1: running balance = [-4, -7, -3, +13], max drawdown = 7
    # From t=2: running balance = [-3, +1, +17], max drawdown = 3
    # From t=3: running balance = [+4, +20], max drawdown = 0
    # From t=4: running balance = [+16], max drawdown = 0
    assert result == pytest.approx([11.0, 7.0, 3.0, 0.0, 0.0, 0.0])


def test_multiple_loads_and_solar() -> None:
    """Test with multiple load and solar elements - they should aggregate."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "load_1": {
                "element_type": "load",
                "forecast": [1.0, 1.0],
            },
            "load_2": {
                "element_type": "load",
                "forecast": [2.0, 1.0],
            },
            "solar_1": {
                "element_type": "solar",
                "forecast": [0.5, 0.5],
            },
            "solar_2": {
                "element_type": "solar",
                "forecast": [0.5, 0.5],
            },
        },
    )
    periods_hours = [1.0, 1.0]

    result = calculate_required_energy(participants, periods_hours)

    # Total load = [3.0, 2.0], Total solar = [1.0, 1.0]
    # Net energy = (solar - load) * period = [-2.0, -1.0] kWh
    # From t=0: running balance = [-2, -3], max drawdown = 3
    # From t=1: running balance = [-1], max drawdown = 1
    assert result == pytest.approx([3.0, 1.0, 0.0])


def test_ignores_non_load_solar_elements() -> None:
    """Test that battery, grid, and other elements are ignored."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [2.0, 2.0],
            },
            "my_battery": {
                "element_type": "battery",
                "capacity": [10.0, 10.0],  # Should be ignored
            },
            "my_grid": {
                "element_type": "grid",
                "import_price": [0.30, 0.30],  # Should be ignored
            },
        },
    )
    periods_hours = [1.0, 1.0]

    result = calculate_required_energy(participants, periods_hours)

    # Only load counts, no solar
    # Net energy = [-2.0, -2.0] kWh
    # From t=0: running balance = [-2, -4], max drawdown = 4
    # From t=1: running balance = [-2], max drawdown = 2
    assert result == pytest.approx([4.0, 2.0, 0.0])


def test_variable_period_lengths() -> None:
    """Test with variable-length periods (like the tier system)."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [1.0, 1.0, 1.0],  # 1 kW constant
            },
        },
    )
    # Tier-like periods: 5 min, 30 min, 60 min (in hours)
    periods_hours = [5 / 60, 30 / 60, 60 / 60]

    result = calculate_required_energy(participants, periods_hours)

    # Net energy = -1 kW * period = [-0.0833, -0.5, -1.0] kWh
    # From t=0: running balance = [-0.0833, -0.5833, -1.5833], max drawdown = 1.5833
    # From t=1: running balance = [-0.5, -1.5], max drawdown = 1.5
    # From t=2: running balance = [-1.0], max drawdown = 1.0
    expected = [
        5 / 60 + 30 / 60 + 60 / 60,  # 1.5833...
        30 / 60 + 60 / 60,  # 1.5
        60 / 60,  # 1.0
        0.0,
    ]
    assert result == pytest.approx(expected)


def test_terminal_value_is_zero() -> None:
    """Test that the last value (end of horizon) is always zero."""
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [10.0, 10.0, 10.0],
            },
        },
    )
    periods_hours = [1.0, 1.0, 1.0]

    result = calculate_required_energy(participants, periods_hours)

    # The last value should always be 0 (no future requirement at end of horizon)
    assert result[-1] == 0.0
    # Should have n_periods + 1 values
    assert len(result) == 4


def test_solar_recharge_in_middle_reduces_requirement() -> None:
    """Test that solar surplus in the middle recharges the battery.

    This is the key test for the maximum drawdown algorithm:
    - Evening: 2kW load, no solar = -2 kWh deficit
    - Midday: 1kW load, 3kW solar = +2 kWh surplus (recharges battery)
    - Night: 1kW load, no solar = -1 kWh deficit

    Old algorithm (sum of deficits) would give [3, 1, 1, 0] - wrong!
    New algorithm (max drawdown) gives [2, 0, 1, 0] - correct!

    At t=0, the battery only needs 2 kWh to survive until midday solar,
    which then recharges it. The night deficit requires a fresh 1 kWh.
    """
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [2.0, 1.0, 1.0],  # kW
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [0.0, 3.0, 0.0],  # Midday solar burst
            },
        },
    )
    periods_hours = [1.0, 1.0, 1.0]

    result = calculate_required_energy(participants, periods_hours)

    # Net energy = (solar - load) * period = [-2.0, +2.0, -1.0] kWh
    # From t=0: running balance = [-2, 0, -1], max drawdown = 2 (not 3!)
    # From t=1: running balance = [+2, +1], max drawdown = 0 (surplus)
    # From t=2: running balance = [-1], max drawdown = 1
    assert result == pytest.approx([2.0, 0.0, 1.0, 0.0])


def test_multiple_drawdown_peaks() -> None:
    """Test scenario with multiple deficit peaks separated by solar surplus.

    Pattern: deficit -> surplus -> deeper deficit -> surplus
    The algorithm should find the deepest drawdown from each starting point.
    """
    participants = cast(
        "Mapping[str, ElementConfigData]",
        {
            "my_load": {
                "element_type": "load",
                "forecast": [1.0, 0.5, 3.0, 0.5],  # kW
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [0.0, 2.0, 0.0, 3.0],  # kW
            },
        },
    )
    periods_hours = [1.0, 1.0, 1.0, 1.0]

    result = calculate_required_energy(participants, periods_hours)

    # Net energy = [-1.0, +1.5, -3.0, +2.5] kWh
    # From t=0: running balance = [-1, +0.5, -2.5, 0], max drawdown = 2.5
    # From t=1: running balance = [+1.5, -1.5, +1], max drawdown = 1.5
    # From t=2: running balance = [-3, -0.5], max drawdown = 3
    # From t=3: running balance = [+2.5], max drawdown = 0
    assert result == pytest.approx([2.5, 1.5, 3.0, 0.0, 0.0])
