"""Integration tests for Network optimization scenarios."""

import numpy as np

from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE


def test_simple_optimization() -> None:
    """Test a simple optimization scenario with basic network setup."""
    network = Network(name="test_network", periods=[1.0] * 3)

    # Add a simple grid and load
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "net", "is_source": False, "is_sink": False})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "grid_connection",
            "source": "grid",
            "target": "net",
            "segments": [
                {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10000.0, 10000.0, 10000.0]),
                    "max_power_target_source": np.array([5000.0, 5000.0, 5000.0]),
                },
                {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.1, 0.2, 0.15]),
                    "price_target_source": np.array([0.05, 0.08, 0.06]),
                },
            ],
        }
    )
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "load_connection",
            "source": "net",
            "target": "load",
            "segments": [
                {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([1000.0, 1500.0, 2000.0]),
                    "fixed": True,
                }
            ],
        }
    )

    # Run optimization
    cost = network.optimize()

    assert isinstance(cost, (int, float))


def test_network_validation() -> None:
    """Test that network validation catches invalid configurations."""
    network = Network(name="test_network", periods=[1.0] * 3)

    # Add entities
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})

    # Create valid connection
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "valid_connection",
            "source": "source",
            "target": "sink",
            "segments": [
                {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([1000.0, 1000.0, 1000.0]),
                }
            ],
        }
    )

    # Should validate successfully
    network.validate()

    # Run optimization to ensure it completes
    cost = network.optimize()
    assert isinstance(cost, (int, float))
