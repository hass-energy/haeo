"""Unit tests for reactive warm start optimization functionality.

With the reactive pattern, parameters are updated directly on elements via TrackedParam,
and the caching system automatically invalidates and rebuilds only the affected constraints.
"""

import numpy as np
import pytest

from custom_components.haeo.model import Network
from custom_components.haeo.model.battery import Battery
from custom_components.haeo.model.power_connection import PowerConnection


class TestBatteryReactiveUpdate:
    """Tests for Battery parameter updates via TrackedParam."""

    def test_update_capacity_modifies_soc_constraints(self) -> None:
        """Test that setting capacity directly invalidates and rebuilds SOC constraints."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        # Add battery and run initial optimization
        network.add("battery", "battery", capacity=10.0, initial_charge=5.0)
        network.add("node", "grid", is_source=True, is_sink=True)
        network.add(
            "connection",
            "battery_grid",
            source="battery",
            target="grid",
            max_power_source_target=5.0,
            max_power_target_source=5.0,
            price_source_target=-0.10,  # Export pays
            price_target_source=0.15,  # Import costs
        )

        # First optimization
        cost1 = network.optimize()

        # Update battery capacity via TrackedParam (must be sequence for T+1 boundaries)
        battery = network.elements["battery"]
        assert isinstance(battery, Battery)
        battery.capacity = (20.0, 20.0, 20.0, 20.0)

        # Second optimization should use updated capacity
        cost2 = network.optimize()

        # Verify battery capacity was updated
        assert np.all(np.array(battery.capacity) == 20.0)

        # Cost should be different with larger capacity (more flexibility)
        # Both optimizations should succeed
        assert cost1 is not None
        assert cost2 is not None

    def test_update_initial_charge_modifies_constraint(self) -> None:
        """Test that setting initial_charge invalidates the initial state constraint."""
        network = Network(name="test", periods=[1.0])

        network.add("battery", "battery", capacity=10.0, initial_charge=2.0)
        network.add("node", "grid", is_source=True, is_sink=True)
        network.add(
            "connection",
            "battery_grid",
            source="battery",
            target="grid",
            max_power_source_target=10.0,
            price_source_target=-0.10,
        )

        # First optimization
        cost1 = network.optimize()

        # Update initial charge via TrackedParam
        battery = network.elements["battery"]
        assert isinstance(battery, Battery)
        old_initial_charge = battery.initial_charge
        battery.initial_charge = 8.0

        # Verify initial charge was updated in the element
        assert battery.initial_charge == 8.0
        assert battery.initial_charge != old_initial_charge

        # Second optimization should work with updated initial charge
        cost2 = network.optimize()

        # Both optimizations should succeed
        assert cost1 is not None
        assert cost2 is not None

    def test_update_with_sequence_capacity(self) -> None:
        """Test setting capacity with a sequence value."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("battery", "battery", capacity=10.0, initial_charge=5.0)
        network.optimize()

        battery = network.elements["battery"]
        assert isinstance(battery, Battery)

        # Update with sequence (varying capacity per period boundary)
        battery.capacity = [8.0, 9.0, 10.0, 11.0]  # 4 values for 3 periods + 1

        assert len(battery.capacity) == 4
        np.testing.assert_array_equal(battery.capacity, [8.0, 9.0, 10.0, 11.0])


class TestConnectionReactiveUpdate:
    """Tests for PowerConnection parameter updates via TrackedParam."""

    def test_update_max_power_source_target(self) -> None:
        """Test setting max_power_source_target invalidates constraint bounds."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("node", "source", is_source=True, is_sink=False)
        network.add("node", "sink", is_source=False, is_sink=True)
        network.add(
            "connection",
            "conn",
            source="source",
            target="sink",
            max_power_source_target=5.0,
            price_source_target=0.10,
        )

        # First optimization
        network.optimize()

        connection = network.elements["conn"]
        assert isinstance(connection, PowerConnection)

        # Update max power via TrackedParam
        connection.max_power_source_target = 10.0

        # Verify max power was updated
        np.testing.assert_array_equal(connection.max_power_source_target, [10.0, 10.0, 10.0])

        # Second optimization should work with new bounds
        cost2 = network.optimize()
        assert cost2 is not None

    def test_update_price_source_target(self) -> None:
        """Test setting price_source_target invalidates objective coefficients."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("node", "source", is_source=True, is_sink=False)
        network.add("node", "sink", is_source=False, is_sink=True)
        network.add(
            "connection",
            "conn",
            source="source",
            target="sink",
            max_power_source_target=5.0,
            fixed_power=True,  # Force flow to happen
            price_source_target=0.10,
        )

        # First optimization - cost = 5 kW * 3 hours * $0.10/kWh = $1.50
        cost1 = network.optimize()

        connection = network.elements["conn"]
        assert isinstance(connection, PowerConnection)

        # Update price via TrackedParam
        connection.price_source_target = 0.20

        # Second optimization - cost = 5 kW * 3 hours * $0.20/kWh = $3.00
        cost2 = network.optimize()

        # Cost should be doubled
        assert pytest.approx(cost2 / cost1, rel=1e-6) == 2.0

    def test_update_max_power_target_source(self) -> None:
        """Test setting max_power_target_source invalidates constraint bounds."""
        network = Network(name="test", periods=[1.0])

        network.add("node", "source", is_source=True, is_sink=True)
        network.add("node", "sink", is_source=True, is_sink=True)
        network.add(
            "connection",
            "conn",
            source="source",
            target="sink",
            max_power_source_target=5.0,
            max_power_target_source=3.0,
        )

        network.optimize()

        connection = network.elements["conn"]
        assert isinstance(connection, PowerConnection)

        connection.max_power_target_source = 7.0
        np.testing.assert_array_equal(connection.max_power_target_source, [7.0])

    def test_update_price_target_source(self) -> None:
        """Test setting price_target_source invalidates objective coefficients."""
        network = Network(name="test", periods=[1.0])

        # Battery starts empty, needs to charge from grid
        network.add("battery", "battery", capacity=10.0, initial_charge=0.0)
        network.add("node", "grid", is_source=True, is_sink=True)
        network.add(
            "connection",
            "conn",
            source="battery",
            target="grid",
            max_power_source_target=5.0,
            max_power_target_source=5.0,
            price_source_target=0.0,
            price_target_source=0.15,  # Cost to import from grid to battery
        )

        # With no incentive to charge and a cost to charge, optimizer won't charge
        cost1 = network.optimize()
        # No flow = no cost
        assert pytest.approx(cost1) == 0.0

        connection = network.elements["conn"]
        assert isinstance(connection, PowerConnection)

        # Double the import price via TrackedParam
        connection.price_target_source = 0.30

        cost2 = network.optimize()
        # Still no incentive to charge, so no cost
        assert pytest.approx(cost2) == 0.0

        # Verify the price was updated
        np.testing.assert_array_equal(connection.price_target_source, [0.30])

    def test_update_with_sequence_values(self) -> None:
        """Test setting connection parameters with sequence values."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("node", "source", is_source=True, is_sink=False)
        network.add("node", "sink", is_source=False, is_sink=True)
        network.add(
            "connection",
            "conn",
            source="source",
            target="sink",
            max_power_source_target=5.0,
            price_source_target=0.10,
        )

        network.optimize()

        connection = network.elements["conn"]
        assert isinstance(connection, PowerConnection)

        # Update with varying prices per period via TrackedParam
        connection.price_source_target = [0.05, 0.10, 0.15]
        np.testing.assert_array_equal(connection.price_source_target, [0.05, 0.10, 0.15])


class TestNetworkWarmStart:
    """Tests for Network warm start behavior with reactive pattern."""

    def test_warm_start_produces_same_result(self) -> None:
        """Test that warm start optimization produces same result as cold start."""
        # Create first network (cold start)
        network1 = Network(name="test1", periods=[1.0, 1.0, 1.0])
        network1.add("battery", "battery", capacity=10.0, initial_charge=5.0)
        network1.add("node", "grid", is_source=True, is_sink=True)
        network1.add(
            "connection",
            "conn",
            source="battery",
            target="grid",
            max_power_source_target=5.0,
            max_power_target_source=5.0,
            price_source_target=-0.10,
            price_target_source=0.15,
        )
        cost1 = network1.optimize()

        # Create second network (warm start simulation)
        network2 = Network(name="test2", periods=[1.0, 1.0, 1.0])
        # First add with initial parameters
        network2.add("battery", "battery", capacity=5.0, initial_charge=2.0)
        network2.add("node", "grid", is_source=True, is_sink=True)
        network2.add(
            "connection",
            "conn",
            source="battery",
            target="grid",
            max_power_source_target=2.0,
            max_power_target_source=2.0,
            price_source_target=-0.05,
            price_target_source=0.08,
        )
        # First optimization
        network2.optimize()

        # Update to same parameters as network1 via TrackedParam
        # (capacity must be sequence for T+1 boundaries)
        battery = network2.elements["battery"]
        assert isinstance(battery, Battery)
        battery.capacity = (10.0, 10.0, 10.0, 10.0)
        battery.initial_charge = 5.0

        connection = network2.elements["conn"]
        assert isinstance(connection, PowerConnection)
        connection.max_power_source_target = (5.0, 5.0, 5.0)
        connection.max_power_target_source = (5.0, 5.0, 5.0)
        connection.price_source_target = (-0.10, -0.10, -0.10)
        connection.price_target_source = (0.15, 0.15, 0.15)

        # Second optimization (warm start)
        cost2 = network2.optimize()

        # Should produce same result
        assert pytest.approx(cost1, rel=1e-6) == cost2

    def test_network_add_connection_updates_prices(self) -> None:
        """Test that updating connection via network.add updates prices correctly."""
        network = Network(name="test", periods=[1.0])

        network.add("node", "source", is_source=True, is_sink=False)
        network.add("node", "sink", is_source=False, is_sink=True)
        network.add(
            "connection",
            "conn",
            source="source",
            target="sink",
            max_power_source_target=5.0,
            fixed_power=True,
            price_source_target=0.10,
        )

        cost1 = network.optimize()

        # Update via network.add (simulating coordinator flow)
        network.add(
            "connection",
            "conn",
            source="source",
            target="sink",
            max_power_source_target=5.0,
            fixed_power=True,
            price_source_target=0.20,
        )

        cost2 = network.optimize()

        # Price doubled, cost should double
        assert pytest.approx(cost2 / cost1, rel=1e-6) == 2.0
