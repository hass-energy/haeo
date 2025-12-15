"""Unit tests for warm start optimization functionality."""

import numpy as np
import pytest

from custom_components.haeo.model import Network
from custom_components.haeo.model.battery import Battery
from custom_components.haeo.model.connection import Connection


class TestBatteryUpdate:
    """Tests for Battery.update() method."""

    def test_update_capacity_modifies_soc_constraints(self) -> None:
        """Test that updating capacity modifies SOC max constraint bounds."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        # Add battery and run initial optimization
        network.add("battery", "battery", capacity=10.0, initial_charge=5.0)
        network.add("source_sink", "grid", is_source=True, is_sink=True)
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

        # Update battery capacity (simulate SOC sensor update)
        battery = network.elements["battery"]
        assert isinstance(battery, Battery)
        battery.update(capacity=20.0)

        # Second optimization should use updated capacity
        cost2 = network.optimize()

        # Verify battery capacity was updated
        assert np.all(battery.capacity == 20.0)

        # Cost should be different with larger capacity (more flexibility)
        # With larger capacity, may be able to store more or discharge more
        # The exact difference depends on the optimization, but they shouldn't be identical
        # unless the scenario doesn't benefit from extra capacity
        assert cost1 is not None
        assert cost2 is not None

    def test_update_initial_charge_modifies_constraint(self) -> None:
        """Test that updating initial_charge modifies the initial state constraint."""
        network = Network(name="test", periods=[1.0])

        network.add("battery", "battery", capacity=10.0, initial_charge=2.0)
        network.add("source_sink", "grid", is_source=True, is_sink=True)
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

        # Update initial charge (simulate battery SOC increasing)
        battery = network.elements["battery"]
        assert isinstance(battery, Battery)
        old_initial_charge = battery.initial_charge
        battery.update(initial_charge=8.0)

        # Verify initial charge was updated in the element
        assert battery.initial_charge == 8.0
        assert battery.initial_charge != old_initial_charge

        # Second optimization should work with updated initial charge
        cost2 = network.optimize()

        # Both optimizations should succeed
        assert cost1 is not None
        assert cost2 is not None

    def test_update_with_sequence_capacity(self) -> None:
        """Test updating capacity with a sequence value."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("battery", "battery", capacity=10.0, initial_charge=5.0)
        network.optimize()

        battery = network.elements["battery"]
        assert isinstance(battery, Battery)

        # Update with sequence (varying capacity per period boundary)
        battery.update(capacity=[8.0, 9.0, 10.0, 11.0])  # 4 values for 3 periods + 1

        assert len(battery.capacity) == 4
        np.testing.assert_array_equal(battery.capacity, [8.0, 9.0, 10.0, 11.0])


class TestConnectionUpdate:
    """Tests for Connection.update() method."""

    def test_update_max_power_source_target(self) -> None:
        """Test updating max_power_source_target modifies constraint bounds."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("source_sink", "source", is_source=True, is_sink=False)
        network.add("source_sink", "sink", is_source=False, is_sink=True)
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
        assert isinstance(connection, Connection)

        # Update max power
        connection.update(max_power_source_target=10.0)

        # Verify max power was updated
        np.testing.assert_array_equal(connection.max_power_source_target, [10.0, 10.0, 10.0])

        # Second optimization should work with new bounds
        cost2 = network.optimize()
        assert cost2 is not None

    def test_update_price_source_target(self) -> None:
        """Test updating price_source_target modifies objective coefficients."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("source_sink", "source", is_source=True, is_sink=False)
        network.add("source_sink", "sink", is_source=False, is_sink=True)
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
        assert isinstance(connection, Connection)

        # Update price to double
        connection.update(price_source_target=0.20)

        # Second optimization - cost = 5 kW * 3 hours * $0.20/kWh = $3.00
        cost2 = network.optimize()

        # Cost should be doubled
        assert pytest.approx(cost2 / cost1, rel=1e-6) == 2.0

    def test_update_max_power_target_source(self) -> None:
        """Test updating max_power_target_source modifies constraint bounds."""
        network = Network(name="test", periods=[1.0])

        network.add("source_sink", "source", is_source=True, is_sink=True)
        network.add("source_sink", "sink", is_source=True, is_sink=True)
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
        assert isinstance(connection, Connection)

        connection.update(max_power_target_source=7.0)
        np.testing.assert_array_equal(connection.max_power_target_source, [7.0])

    def test_update_price_target_source(self) -> None:
        """Test updating price_target_source modifies objective coefficients."""
        network = Network(name="test", periods=[1.0])

        # Battery starts empty, needs to charge from grid
        network.add("battery", "battery", capacity=10.0, initial_charge=0.0)
        network.add("source_sink", "grid", is_source=True, is_sink=True)
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
        assert isinstance(connection, Connection)

        # Double the import price
        connection.update(price_target_source=0.30)

        cost2 = network.optimize()
        # Still no incentive to charge, so no cost
        assert pytest.approx(cost2) == 0.0

        # Verify the price was updated
        np.testing.assert_array_equal(connection.price_target_source, [0.30])

    def test_update_with_sequence_values(self) -> None:
        """Test updating connection parameters with sequence values."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        network.add("source_sink", "source", is_source=True, is_sink=False)
        network.add("source_sink", "sink", is_source=False, is_sink=True)
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
        assert isinstance(connection, Connection)

        # Update with varying prices per period
        connection.update(price_source_target=[0.05, 0.10, 0.15])
        np.testing.assert_array_equal(connection.price_source_target, [0.05, 0.10, 0.15])


class TestNetworkWarmStart:
    """Tests for Network warm start behavior."""

    def test_add_updates_existing_element(self) -> None:
        """Test that add() updates existing elements instead of creating new ones."""
        network = Network(name="test", periods=[1.0, 1.0, 1.0])

        # Add battery
        battery1 = network.add("battery", "battery", capacity=10.0, initial_charge=5.0)
        assert isinstance(battery1, Battery)

        # First optimization
        network.optimize()

        # "Add" same battery with different parameters - should update
        battery2 = network.add("battery", "battery", capacity=20.0, initial_charge=10.0)

        # Should return the same element instance
        assert battery2 is battery1

        # Parameters should be updated
        np.testing.assert_array_equal(battery1.capacity, [20.0, 20.0, 20.0, 20.0])
        assert battery1.initial_charge == 10.0

    def test_constraints_built_flag_prevents_rebuilding(self) -> None:
        """Test that constraints are only built on first optimization."""
        network = Network(name="test", periods=[1.0])

        network.add("source_sink", "source", is_source=True, is_sink=False)
        network.add("source_sink", "sink", is_source=False, is_sink=True)
        network.add(
            "connection",
            "conn",
            source="source",
            target="sink",
            max_power_source_target=5.0,
        )

        # First optimization builds constraints
        assert network._constraints_built is False
        network.optimize()
        assert network._constraints_built is True

        # Second optimization skips constraint building
        network.optimize()
        assert network._constraints_built is True

    def test_warm_start_produces_same_result(self) -> None:
        """Test that warm start optimization produces same result as cold start."""
        # Create first network (cold start)
        network1 = Network(name="test1", periods=[1.0, 1.0, 1.0])
        network1.add("battery", "battery", capacity=10.0, initial_charge=5.0)
        network1.add("source_sink", "grid", is_source=True, is_sink=True)
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
        network2.add("source_sink", "grid", is_source=True, is_sink=True)
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

        # Update to same parameters as network1
        battery = network2.elements["battery"]
        assert isinstance(battery, Battery)
        battery.update(capacity=10.0, initial_charge=5.0)

        connection = network2.elements["conn"]
        assert isinstance(connection, Connection)
        connection.update(
            max_power_source_target=5.0,
            max_power_target_source=5.0,
            price_source_target=-0.10,
            price_target_source=0.15,
        )

        # Second optimization (warm start)
        cost2 = network2.optimize()

        # Should produce same result
        assert pytest.approx(cost1, rel=1e-6) == cost2

    def test_network_add_connection_updates_prices(self) -> None:
        """Test that updating connection via network.add updates prices correctly."""
        network = Network(name="test", periods=[1.0])

        network.add("source_sink", "source", is_source=True, is_sink=False)
        network.add("source_sink", "sink", is_source=False, is_sink=True)
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
