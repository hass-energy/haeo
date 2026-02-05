"""Unit tests for period update functionality.

Tests that updating network periods propagates to all elements and segments,
invalidating dependent constraints and costs correctly.
"""

import numpy as np
import pytest

from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
)
from custom_components.haeo.model.elements.battery import Battery
from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.elements.segments import PricingSegment


class TestNetworkUpdatePeriods:
    """Tests for Network.update_periods() method."""

    def test_update_periods_updates_network(self) -> None:
        """Test that update_periods updates the network's periods array."""
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        new_periods = np.array([0.5, 1.0, 1.5])
        network.update_periods(new_periods)

        np.testing.assert_array_almost_equal(network.periods, [0.5, 1.0, 1.5])

    def test_update_periods_propagates_to_elements(self) -> None:
        """Test that update_periods propagates to all elements."""
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery",
                "capacity": 10.0,
                "initial_charge": 5.0,
            }
        )
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})

        # Update periods
        new_periods = np.array([0.5, 1.0, 1.5])
        network.update_periods(new_periods)

        # Check element periods were updated
        battery = network.elements["battery"]
        assert isinstance(battery, Battery)
        np.testing.assert_array_almost_equal(battery.periods, [0.5, 1.0, 1.5])

        grid = network.elements["grid"]
        np.testing.assert_array_almost_equal(grid.periods, [0.5, 1.0, 1.5])

    def test_update_periods_propagates_to_segments(self) -> None:
        """Test that update_periods propagates to connection segments."""
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "source",
                "target": "sink",
                "segments": {
                    "pricing": {"segment_type": "pricing", "price_source_target": 0.10},
                },
            }
        )

        # Update periods
        new_periods = np.array([0.5, 1.0, 1.5])
        network.update_periods(new_periods)

        # Check segment periods were updated
        connection = network.elements["conn"]
        assert isinstance(connection, Connection)

        pricing = connection.segments["pricing"]
        assert isinstance(pricing, PricingSegment)
        np.testing.assert_array_almost_equal(pricing.periods, [0.5, 1.0, 1.5])


class TestPeriodUpdateInvalidation:
    """Tests for constraint/cost invalidation on period updates."""

    def test_battery_constraint_rebuilt_after_period_update(self) -> None:
        """Test that battery power balance constraint is rebuilt when periods change."""
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery",
                "capacity": 10.0,
                "initial_charge": 5.0,
            }
        )
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "battery",
                "target": "grid",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 5.0,
                        "max_power_target_source": 5.0,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": -0.10,
                        "price_target_source": 0.15,
                    },
                },
            }
        )

        # First optimization
        cost1 = network.optimize()
        assert cost1 is not None

        # Update periods - this should invalidate battery power balance constraint
        new_periods = np.array([0.5, 1.0, 1.5])
        network.update_periods(new_periods)

        # Second optimization should work with new periods
        cost2 = network.optimize()
        assert cost2 is not None

        # Costs should differ due to different period durations
        # With shorter first period, optimization may produce different result
        # We just verify both optimizations succeed

    def test_pricing_cost_rebuilt_after_period_update(self) -> None:
        """Test that pricing segment cost is rebuilt when periods change.

        Cost = power * price * period_duration
        Changing periods should change the cost calculation.
        """
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "source",
                "target": "sink",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 5.0,
                        "fixed": True,  # Force max flow
                    },
                    "pricing": {"segment_type": "pricing", "price_source_target": 0.10},
                },
            }
        )

        # First optimization with uniform 1-hour periods
        # Cost = 5 kW * $0.10/kWh * (1 + 1 + 1) hours = $1.50
        cost1 = network.optimize()
        assert pytest.approx(cost1) == 1.50

        # Update periods to different durations (same total: 3 hours)
        new_periods = np.array([0.5, 1.0, 1.5])
        network.update_periods(new_periods)

        # Second optimization with varied periods
        # Cost = 5 kW * $0.10/kWh * (0.5 + 1.0 + 1.5) hours = $1.50
        cost2 = network.optimize()
        assert pytest.approx(cost2) == 1.50

        # Now change to shorter total duration
        shorter_periods = np.array([0.5, 0.5, 0.5])
        network.update_periods(shorter_periods)

        # Cost = 5 kW * $0.10/kWh * (0.5 + 0.5 + 0.5) hours = $0.75
        cost3 = network.optimize()
        assert pytest.approx(cost3) == 0.75

    def test_solver_structure_unchanged_after_period_update(self) -> None:
        """Test that period updates don't grow solver structure.

        The number of constraints and variables should remain constant
        across multiple optimizations with period updates.
        """
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery",
                "capacity": 10.0,
                "initial_charge": 5.0,
            }
        )
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "battery",
                "target": "grid",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 5.0,
                        "max_power_target_source": 5.0,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": -0.10,
                        "price_target_source": 0.15,
                    },
                },
            }
        )

        # First optimization - establish baseline
        network.optimize()
        num_vars_1 = network._solver.numVariables
        num_cons_1 = network._solver.numConstrs

        # Update periods and optimize again
        network.update_periods(np.array([0.5, 1.0, 1.5]))
        network.optimize()
        num_vars_2 = network._solver.numVariables
        num_cons_2 = network._solver.numConstrs

        # Structure should be identical
        assert num_vars_1 == num_vars_2, f"Variables grew from {num_vars_1} to {num_vars_2}"
        assert num_cons_1 == num_cons_2, f"Constraints grew from {num_cons_1} to {num_cons_2}"

        # Update periods again
        network.update_periods(np.array([2.0, 2.0, 2.0]))
        network.optimize()
        num_vars_3 = network._solver.numVariables
        num_cons_3 = network._solver.numConstrs

        # Structure should still be identical
        assert num_vars_1 == num_vars_3, f"Variables grew from {num_vars_1} to {num_vars_3}"
        assert num_cons_1 == num_cons_3, f"Constraints grew from {num_cons_1} to {num_cons_3}"


class TestPeriodUpdateWithOtherParams:
    """Tests for period updates combined with other parameter updates."""

    def test_period_update_with_price_update(self) -> None:
        """Test that period updates work correctly alongside price updates."""
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "source",
                "target": "sink",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 5.0,
                        "fixed": True,
                    },
                    "pricing": {"segment_type": "pricing", "price_source_target": 0.10},
                },
            }
        )

        # Initial: 5 kW * 3 hours * $0.10 = $1.50
        cost1 = network.optimize()
        assert pytest.approx(cost1) == 1.50

        # Update both periods and prices
        network.update_periods(np.array([0.5, 0.5, 0.5]))  # Total 1.5 hours

        connection = network.elements["conn"]
        assert isinstance(connection, Connection)
        pricing = connection.segments["pricing"]
        assert isinstance(pricing, PricingSegment)
        pricing.price_source_target = np.array([0.20, 0.20, 0.20])

        # New: 5 kW * 1.5 hours * $0.20 = $1.50
        cost2 = network.optimize()
        assert pytest.approx(cost2) == 1.50

    def test_period_update_with_capacity_update(self) -> None:
        """Test that period updates work correctly alongside battery capacity updates."""
        network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery",
                "capacity": 10.0,
                "initial_charge": 5.0,
            }
        )
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "battery",
                "target": "grid",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 5.0,
                        "max_power_target_source": 5.0,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": -0.10,
                        "price_target_source": 0.15,
                    },
                },
            }
        )

        # First optimization
        cost1 = network.optimize()
        assert cost1 is not None

        # Update both periods and capacity
        network.update_periods(np.array([0.5, 1.0, 1.5]))

        battery = network.elements["battery"]
        assert isinstance(battery, Battery)
        battery.capacity = np.array([20.0, 20.0, 20.0, 20.0])

        # Second optimization should work
        cost2 = network.optimize()
        assert cost2 is not None
