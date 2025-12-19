"""Unit tests for required energy calculation.

The required energy represents the total future energy that must come from
dispatchable sources (battery, grid, generator) to meet load that exceeds
uncontrollable generation (solar, wind).

The calculation:
1. Aggregates all load forecasts
2. Aggregates all uncontrollable generation (solar)
3. Computes net power = uncontrollable - load
4. Extracts only the deficit (where load > generation)
5. Performs a reverse cumulative sum to get "energy required from now to horizon end"
"""

import pytest

from custom_components.haeo.data import calculate_required_energy


class TestCalculateRequiredEnergy:
    """Tests for calculate_required_energy function."""

    def test_empty_participants_returns_zero(self) -> None:
        """Test that empty participants returns a single zero value."""
        result = calculate_required_energy({}, [1.0, 1.0, 1.0])
        # n_periods + 1 values, all zeros since no load or solar
        assert result == [0.0, 0.0, 0.0, 0.0]

    def test_empty_periods_returns_single_zero(self) -> None:
        """Test that empty periods returns a single zero value."""
        result = calculate_required_energy({}, [])
        assert result == [0.0]

    def test_load_only_no_solar(self) -> None:
        """Test with load only, no solar - all load becomes required energy."""
        participants = {
            "my_load": {
                "element_type": "load",
                "forecast": [2.0, 1.0, 0.5],  # kW
            }
        }
        periods_hours = [1.0, 1.0, 1.0]  # 1 hour each

        result = calculate_required_energy(participants, periods_hours)

        # Interval energies: [2.0, 1.0, 0.5] kWh
        # Reverse cumsum: [3.5, 1.5, 0.5, 0.0]
        assert result == pytest.approx([3.5, 1.5, 0.5, 0.0])

    def test_solar_covers_all_load(self) -> None:
        """Test with solar exceeding load - no required energy."""
        participants = {
            "my_load": {
                "element_type": "load",
                "forecast": [1.0, 1.0, 1.0],  # kW
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [2.0, 2.0, 2.0],  # kW (exceeds load)
            },
        }
        periods_hours = [1.0, 1.0, 1.0]

        result = calculate_required_energy(participants, periods_hours)

        # Solar exceeds load in all periods, so no required energy
        assert result == pytest.approx([0.0, 0.0, 0.0, 0.0])

    def test_solar_partially_covers_load(self) -> None:
        """Test with solar partially covering load."""
        participants = {
            "my_load": {
                "element_type": "load",
                "forecast": [3.0, 2.0, 1.0],  # kW
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [1.0, 1.0, 2.0],  # kW
            },
        }
        periods_hours = [1.0, 1.0, 1.0]

        result = calculate_required_energy(participants, periods_hours)

        # Net power = solar - load = [-2.0, -1.0, +1.0]
        # Required power (deficit only) = [2.0, 1.0, 0.0]
        # Required energy = required_power * period = [2.0, 1.0, 0.0]
        # Reverse cumsum = [3.0, 1.0, 0.0, 0.0]
        assert result == pytest.approx([3.0, 1.0, 0.0, 0.0])

    def test_overnight_scenario(self) -> None:
        """Test realistic overnight scenario where solar drops to zero."""
        participants = {
            "my_load": {
                "element_type": "load",
                "forecast": [2.0, 1.0, 0.5, 1.0, 1.0],  # Evening to morning
            },
            "my_solar": {
                "element_type": "solar",
                "forecast": [0.0, 0.0, 0.0, 2.0, 5.0],  # No solar until morning
            },
        }
        periods_hours = [2.0, 4.0, 6.0, 4.0, 4.0]  # Variable length periods

        result = calculate_required_energy(participants, periods_hours)

        # Net power = solar - load = [-2.0, -1.0, -0.5, +1.0, +4.0]
        # Required power = [2.0, 1.0, 0.5, 0.0, 0.0]
        # Required energy = [4.0, 4.0, 3.0, 0.0, 0.0] (power * period)
        # Reverse cumsum = [11.0, 7.0, 3.0, 0.0, 0.0, 0.0]
        assert result == pytest.approx([11.0, 7.0, 3.0, 0.0, 0.0, 0.0])

    def test_multiple_loads_and_solar(self) -> None:
        """Test with multiple load and solar elements - they should aggregate."""
        participants = {
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
        }
        periods_hours = [1.0, 1.0]

        result = calculate_required_energy(participants, periods_hours)

        # Total load = [3.0, 2.0]
        # Total solar = [1.0, 1.0]
        # Net power = solar - load = [-2.0, -1.0]
        # Required power = [2.0, 1.0]
        # Required energy = [2.0, 1.0]
        # Reverse cumsum = [3.0, 1.0, 0.0]
        assert result == pytest.approx([3.0, 1.0, 0.0])

    def test_ignores_non_load_solar_elements(self) -> None:
        """Test that battery, grid, and other elements are ignored."""
        participants = {
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
        }
        periods_hours = [1.0, 1.0]

        result = calculate_required_energy(participants, periods_hours)

        # Only load counts, no solar
        # Required energy = [2.0, 2.0]
        # Reverse cumsum = [4.0, 2.0, 0.0]
        assert result == pytest.approx([4.0, 2.0, 0.0])

    def test_variable_period_lengths(self) -> None:
        """Test with variable-length periods (like the tier system)."""
        participants = {
            "my_load": {
                "element_type": "load",
                "forecast": [1.0, 1.0, 1.0],  # 1 kW constant
            },
        }
        # Tier-like periods: 5 min, 30 min, 60 min (in hours)
        periods_hours = [5 / 60, 30 / 60, 60 / 60]

        result = calculate_required_energy(participants, periods_hours)

        # Required energy per interval = 1 kW * period
        # = [0.0833..., 0.5, 1.0] kWh
        # Reverse cumsum = [1.5833..., 1.5, 1.0, 0.0]
        expected = [
            5 / 60 + 30 / 60 + 60 / 60,  # 1.5833...
            30 / 60 + 60 / 60,  # 1.5
            60 / 60,  # 1.0
            0.0,
        ]
        assert result == pytest.approx(expected)

    def test_terminal_value_is_zero(self) -> None:
        """Test that the last value (end of horizon) is always zero."""
        participants = {
            "my_load": {
                "element_type": "load",
                "forecast": [10.0, 10.0, 10.0],
            },
        }
        periods_hours = [1.0, 1.0, 1.0]

        result = calculate_required_energy(participants, periods_hours)

        # The last value should always be 0 (no future requirement at end of horizon)
        assert result[-1] == 0.0
        # Should have n_periods + 1 values
        assert len(result) == 4

    def test_missing_forecast_key_handled(self) -> None:
        """Test that elements without forecast key are handled gracefully."""
        participants = {
            "my_load": {
                "element_type": "load",
                # No "forecast" key
            },
        }
        periods_hours = [1.0, 1.0]

        result = calculate_required_energy(participants, periods_hours)

        # Should return zeros since no forecast data
        assert result == pytest.approx([0.0, 0.0, 0.0])
