"""Tests for network utility functions and edge cases."""

from highspy import Highs

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.coordinator.network import update_element
from custom_components.haeo.elements import ElementConfigData
from custom_components.haeo.elements.connection import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
)
from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE


def test_update_element_updates_tracked_params() -> None:
    """Test update_element updates TrackedParams on existing elements."""
    # Create network with nodes and connection
    network = Network(name="test", periods=[1.0, 1.0])
    network.add(MODEL_ELEMENT_TYPE_NODE, "source", is_source=True, is_sink=False)
    network.add(MODEL_ELEMENT_TYPE_NODE, "target", is_source=False, is_sink=True)
    network.add(
        MODEL_ELEMENT_TYPE_CONNECTION,
        "conn",
        source="source",
        target="target",
        max_power_source_target=10.0,
        max_power_target_source=5.0,
    )
    
    # Verify initial state
    conn = network.elements["conn"]
    assert conn.max_power_source_target[0] == 10.0
    assert conn.max_power_target_source[0] == 5.0
    
    # Update via element config
    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: MODEL_ELEMENT_TYPE_CONNECTION,
        CONF_NAME: "conn",
        CONF_SOURCE: "source",
        CONF_TARGET: "target",
        CONF_MAX_POWER_SOURCE_TARGET: [20.0, 20.0],
        CONF_MAX_POWER_TARGET_SOURCE: [15.0, 15.0],
    }
    update_element(network, config)
    
    # Verify updated state - TrackedParams should be updated
    assert conn.max_power_source_target[0] == 20.0
    assert conn.max_power_target_source[0] == 15.0


def test_network_cost_with_multiple_elements() -> None:
    """Test Network.cost() aggregates costs from multiple elements."""
    network = Network(name="test", periods=[1.0, 1.0])
    
    # Add two nodes
    network.add(MODEL_ELEMENT_TYPE_NODE, "source", is_source=True, is_sink=False)
    network.add(MODEL_ELEMENT_TYPE_NODE, "target", is_source=False, is_sink=True)
    
    # Add two connections with pricing (each creates costs)
    network.add(
        MODEL_ELEMENT_TYPE_CONNECTION,
        "conn1",
        source="source",
        target="target",
        price_source_target=[10.0, 20.0],
    )
    network.add(
        MODEL_ELEMENT_TYPE_CONNECTION,
        "conn2",
        source="target",
        target="source",
        price_source_target=[5.0, 10.0],
    )
    
    # Get aggregated cost - should use Highs.qsum for multiple costs
    cost = network.cost()
    
    # Should return a single expression (tests line 144 in network.py)
    assert cost is not None


def test_constraint_without_output() -> None:
    """Test that constraints without output=True don't return OutputData."""
    from custom_components.haeo.model.elements.battery import Battery
    
    h = Highs()
    h.setOptionValue("output_flag", False)
    
    # Use 2 periods since battery constraints use slices [1:]
    battery = Battery(
        name="test",
        periods=[1.0, 1.0],
        solver=h,
        capacity=[10.0, 10.0, 10.0],
        initial_charge=5.0,
    )
    
    # Trigger constraint creation
    battery.constraints()
    
    # Get outputs - should not include constraints without output=True
    outputs = battery.outputs()
    
    # Battery has @constraint decorators without output=True (energy_balance)
    # These should not appear in outputs (tests line 125 in decorators.py)
    assert "energy_balance" not in outputs
    
    # But should include constraints with output=True
    assert "battery_soc_max" in outputs
    assert "battery_soc_min" in outputs


def test_network_constraints_empty_when_no_elements() -> None:
    """Test Network.constraints() returns empty dict with no elements."""
    network = Network(name="test", periods=[1.0])
    
    # No elements added - should return empty dict (tests line 212-213 in network.py)
    constraints = network.constraints()
    assert constraints == {}


def test_network_cost_returns_none_when_no_costs() -> None:
    """Test Network.cost() returns None when network has no cost terms."""
    network = Network(name="test", periods=[1.0])
    
    # Add a node (has no costs)
    network.add(MODEL_ELEMENT_TYPE_NODE, "node", is_source=True, is_sink=True)
    
    # Should return None when no costs (tests line 140 in network.py)
    cost = network.cost()
    assert cost is None
