"""Integration tests for Network optimization scenarios."""

import pytest

from custom_components.haeo.elements import ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model import Network


def test_simple_optimization() -> None:
    """Test a simple optimization scenario with basic network setup."""
    network = Network(name="test_network", period=1.0, n_periods=3)

    # Add a simple grid and load
    network.add("source_sink", "grid", is_source=True, is_sink=True)
    network.add("source_sink", "net", is_source=False, is_sink=False)
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "grid_connection",
        source="grid",
        target="net",
        max_power_source_target=10000,
        max_power_target_source=5000,
        price_source_target=[0.1, 0.2, 0.15],
        price_target_source=[0.05, 0.08, 0.06],
    )
    network.add("source_sink", "load", is_source=False, is_sink=True)
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "load_connection",
        source="net",
        target="load",
        max_power_source_target=[1000, 1500, 2000],
        fixed_power=True,
    )

    # Run optimization
    cost = network.optimize()

    assert isinstance(cost, (int, float))


def test_network_validation() -> None:
    """Test that network validation catches invalid configurations."""
    network = Network(name="test_network", period=1.0, n_periods=3)

    # Add entities
    network.add("source_sink", "source", is_source=True, is_sink=False)
    network.add("source_sink", "sink", is_source=False, is_sink=True)

    # Create valid connection
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "valid_connection",
        source="source",
        target="sink",
        max_power_source_target=1000,
    )

    # Should validate successfully
    network.validate()

    # Run optimization to ensure it completes
    cost = network.optimize()
    assert isinstance(cost, (int, float))
