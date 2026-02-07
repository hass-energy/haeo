"""Unit tests for reactive warm start optimization functionality.

With the reactive pattern, parameters are updated directly on elements via TrackedParam,
and the caching system automatically invalidates and rebuilds only the affected constraints.
"""

import numpy as np
import pytest

from custom_components.haeo.coordinator.network import update_element
from custom_components.haeo.elements.connection import (
    SECTION_COMMON,
    SECTION_DEMAND_PRICING,
    SECTION_EFFICIENCY,
    SECTION_ENDPOINTS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
)
from custom_components.haeo.model.elements.battery import Battery
from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.elements.segments import PowerLimitSegment, PricingSegment
from custom_components.haeo.schema import as_connection_target

# Battery reactive update tests


def test_battery_update_capacity_modifies_soc_constraints() -> None:
    """Test that setting capacity directly invalidates and rebuilds SOC constraints."""
    network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

    # Add battery and run initial optimization
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
            "name": "battery_grid",
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
                    "price_source_target": -0.10,  # Export pays
                    "price_target_source": 0.15,  # Import costs
                },
            },
        }
    )

    # First optimization
    cost1 = network.optimize()

    # Update battery capacity via TrackedParam (must be sequence for T+1 boundaries)
    battery = network.elements["battery"]
    assert isinstance(battery, Battery)
    battery.capacity = np.array([20.0, 20.0, 20.0, 20.0])

    # Second optimization should use updated capacity
    cost2 = network.optimize()

    # Verify battery capacity was updated
    assert np.all(np.array(battery.capacity) == 20.0)

    # Cost should be different with larger capacity (more flexibility)
    # Both optimizations should succeed
    assert cost1 is not None
    assert cost2 is not None


def test_battery_update_initial_charge_modifies_constraint() -> None:
    """Test that setting initial_charge invalidates the initial state constraint."""
    network = Network(name="test", periods=np.array([1.0]))

    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": 10.0,
            "initial_charge": 2.0,
        }
    )
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power_source_target": 10.0},
                "pricing": {"segment_type": "pricing", "price_source_target": -0.10},
            },
        }
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


def test_battery_update_with_sequence_capacity() -> None:
    """Test setting capacity with a sequence value."""
    network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]))

    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": 10.0,
            "initial_charge": 5.0,
        }
    )
    network.optimize()

    battery = network.elements["battery"]
    assert isinstance(battery, Battery)

    # Update with sequence (varying capacity per period boundary)
    battery.capacity = np.array([8.0, 9.0, 10.0, 11.0])  # 4 values for 3 periods + 1

    assert len(battery.capacity) == 4
    np.testing.assert_array_equal(battery.capacity, [8.0, 9.0, 10.0, 11.0])


# PowerConnection reactive update tests


def test_connection_update_max_power_source_target() -> None:
    """Test setting max_power_source_target invalidates constraint bounds."""
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
                },
                "pricing": {"segment_type": "pricing", "price_source_target": 0.10},
            },
        }
    )

    # First optimization
    network.optimize()

    connection = network.elements["conn"]
    assert isinstance(connection, Connection)

    # Update max power via TrackedParam
    power_limit = connection.segments["power_limit"]
    assert isinstance(power_limit, PowerLimitSegment)
    power_limit.max_power_source_target = np.array([10.0, 10.0, 10.0])

    # Verify max power was updated
    np.testing.assert_array_equal(power_limit.max_power_source_target, [10.0, 10.0, 10.0])

    # Second optimization should work with new bounds
    cost2 = network.optimize()
    assert cost2 is not None


def test_connection_update_price_source_target() -> None:
    """Test setting price_source_target invalidates objective coefficients."""
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
                    "fixed": True,  # Force flow to happen
                },
                "pricing": {"segment_type": "pricing", "price_source_target": 0.10},
            },
        }
    )

    # First optimization - cost = 5 kW * 3 hours * $0.10/kWh = $1.50
    cost1 = network.optimize()

    connection = network.elements["conn"]
    assert isinstance(connection, Connection)

    # Update price via TrackedParam
    pricing = connection.segments["pricing"]
    assert isinstance(pricing, PricingSegment)
    pricing.price_source_target = np.array([0.20, 0.20, 0.20])

    # Second optimization - cost = 5 kW * 3 hours * $0.20/kWh = $3.00
    cost2 = network.optimize()

    # Cost should be doubled
    assert pytest.approx(cost2 / cost1, rel=1e-6) == 2.0


def test_connection_update_max_power_target_source() -> None:
    """Test setting max_power_target_source invalidates constraint bounds."""
    network = Network(name="test", periods=np.array([1.0]))

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": True})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": True, "is_sink": True})
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
                    "max_power_target_source": 3.0,
                }
            },
        }
    )

    network.optimize()

    connection = network.elements["conn"]
    assert isinstance(connection, Connection)

    power_limit = connection.segments["power_limit"]
    assert isinstance(power_limit, PowerLimitSegment)
    power_limit.max_power_target_source = np.array([7.0])
    np.testing.assert_array_equal(power_limit.max_power_target_source, [7.0])


def test_connection_update_price_target_source() -> None:
    """Test setting price_target_source invalidates objective coefficients."""
    network = Network(name="test", periods=np.array([1.0]))

    # Battery starts empty, needs to charge from grid
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": 10.0,
            "initial_charge": 0.0,
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
                    "price_source_target": 0.0,
                    "price_target_source": 0.15,  # Cost to import from grid to battery
                },
            },
        }
    )

    # With no incentive to charge and a cost to charge, optimizer won't charge
    cost1 = network.optimize()
    # No flow = no cost
    assert pytest.approx(cost1) == 0.0

    connection = network.elements["conn"]
    assert isinstance(connection, Connection)

    # Double the import price via TrackedParam
    pricing = connection.segments["pricing"]
    assert isinstance(pricing, PricingSegment)
    pricing.price_target_source = np.array([0.30])

    cost2 = network.optimize()
    # Still no incentive to charge, so no cost
    assert pytest.approx(cost2) == 0.0

    # Verify the price was updated
    np.testing.assert_array_equal(pricing.price_target_source, [0.30])


def test_connection_update_with_sequence_values() -> None:
    """Test setting connection parameters with sequence values."""
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
                },
                "pricing": {"segment_type": "pricing", "price_source_target": 0.10},
            },
        }
    )

    network.optimize()

    connection = network.elements["conn"]
    assert isinstance(connection, Connection)

    # Update with varying prices per period via TrackedParam
    pricing = connection.segments["pricing"]
    assert isinstance(pricing, PricingSegment)
    pricing.price_source_target = np.array([0.05, 0.10, 0.15])
    np.testing.assert_array_equal(pricing.price_source_target, [0.05, 0.10, 0.15])


# Network warm start tests


def test_warm_start_produces_same_result() -> None:
    """Test that warm start optimization produces same result as cold start."""
    # Create first network (cold start)
    network1 = Network(name="test1", periods=np.array([1.0, 1.0, 1.0]))
    network1.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": 10.0,
            "initial_charge": 5.0,
        }
    )
    network1.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network1.add(
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
    cost1 = network1.optimize()

    # Create second network (warm start simulation)
    network2 = Network(name="test2", periods=np.array([1.0, 1.0, 1.0]))
    # First add with initial parameters
    network2.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": 5.0,
            "initial_charge": 2.0,
        }
    )
    network2.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network2.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": 2.0,
                    "max_power_target_source": 2.0,
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": -0.05,
                    "price_target_source": 0.08,
                },
            },
        }
    )
    # First optimization
    network2.optimize()

    # Update to same parameters as network1 via TrackedParam
    # (capacity must be sequence for T+1 boundaries)
    battery = network2.elements["battery"]
    assert isinstance(battery, Battery)
    battery.capacity = np.array([10.0, 10.0, 10.0, 10.0])
    battery.initial_charge = 5.0

    connection = network2.elements["conn"]
    assert isinstance(connection, Connection)
    power_limit = connection.segments["power_limit"]
    pricing = connection.segments["pricing"]
    assert isinstance(power_limit, PowerLimitSegment)
    assert isinstance(pricing, PricingSegment)
    power_limit.max_power_source_target = np.array([5.0, 5.0, 5.0])
    power_limit.max_power_target_source = np.array([5.0, 5.0, 5.0])
    pricing.price_source_target = np.array([-0.10, -0.10, -0.10])
    pricing.price_target_source = np.array([0.15, 0.15, 0.15])

    # Second optimization (warm start)
    cost2 = network2.optimize()

    # Should produce same result
    assert pytest.approx(cost1, rel=1e-6) == cost2


def test_network_add_connection_updates_prices() -> None:
    """Test that updating connection via network.add updates prices correctly."""
    network = Network(name="test", periods=np.array([1.0]))

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "sink",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power_source_target": 5.0},
                "pricing": {"segment_type": "pricing", "price_source_target": -0.10},
            },
        }
    )

    cost1 = network.optimize()

    # Update via update_element (simulating coordinator flow)
    update_element(
        network,
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            SECTION_COMMON: {"name": "conn"},
            SECTION_ENDPOINTS: {
                "source": as_connection_target("source"),
                "target": as_connection_target("sink"),
            },
            SECTION_POWER_LIMITS: {"max_power_source_target": 5.0},
            SECTION_PRICING: {"price_source_target": -0.20},
            SECTION_DEMAND_PRICING: {},
            SECTION_EFFICIENCY: {},
        },
    )

    cost2 = network.optimize()

    # Price doubled, cost should double
    assert pytest.approx(cost2 / cost1, rel=1e-6) == 2.0


def test_solver_structure_unchanged_after_update() -> None:
    """Test that updating parameters doesn't grow solver structure.

    The number of constraints and variables should remain constant
    across multiple optimizations with parameter updates.
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

    # First optimization - establish baseline structure
    network.optimize()
    num_vars_1 = network._solver.numVariables
    num_cons_1 = network._solver.numConstrs

    # Update parameters and optimize again
    battery = network.elements["battery"]
    assert isinstance(battery, Battery)
    battery.capacity = np.array([20.0, 20.0, 20.0, 20.0])
    battery.initial_charge = 8.0

    connection = network.elements["conn"]
    assert isinstance(connection, Connection)
    pricing = connection.segments["pricing"]
    assert isinstance(pricing, PricingSegment)
    pricing.price_source_target = np.array([-0.20, -0.20, -0.20])

    network.optimize()
    num_vars_2 = network._solver.numVariables
    num_cons_2 = network._solver.numConstrs

    # Structure should be identical
    assert num_vars_1 == num_vars_2, f"Variables grew from {num_vars_1} to {num_vars_2}"
    assert num_cons_1 == num_cons_2, f"Constraints grew from {num_cons_1} to {num_cons_2}"

    # Update again and optimize a third time
    battery.capacity = np.array([15.0, 15.0, 15.0, 15.0])
    power_limit = connection.segments["power_limit"]
    assert isinstance(power_limit, PowerLimitSegment)
    power_limit.max_power_source_target = np.array([10.0, 10.0, 10.0])

    network.optimize()
    num_vars_3 = network._solver.numVariables
    num_cons_3 = network._solver.numConstrs

    # Structure should still be identical
    assert num_vars_1 == num_vars_3, f"Variables grew from {num_vars_1} to {num_vars_3}"
    assert num_cons_1 == num_cons_3, f"Constraints grew from {num_cons_1} to {num_cons_3}"
