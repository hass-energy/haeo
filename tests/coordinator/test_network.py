"""Tests for coordinator network utilities."""

import numpy as np
import pytest

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.coordinator.network import update_element
from custom_components.haeo.elements import ElementConfigData
from custom_components.haeo.elements.connection import CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE
from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.elements.segments import PowerLimitSegment


def test_update_element_updates_tracked_params() -> None:
    """Test update_element updates TrackedParams on existing elements."""
    # Create network with nodes and connection
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "target", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "target",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0, 10.0]),
                    "max_power_target_source": np.array([5.0, 5.0]),
                }
            },
        }
    )

    # Verify initial state with type narrowing
    conn = network.elements["conn"]
    assert isinstance(conn, Connection)
    # Check initial TrackedParam values
    power_limit = conn.segments["power_limit"]
    assert isinstance(power_limit, PowerLimitSegment)
    assert power_limit.max_power_source_target is not None
    assert power_limit.max_power_target_source is not None
    assert power_limit.max_power_source_target[0] == 10.0
    assert power_limit.max_power_target_source[0] == 5.0

    # Update via element config
    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: MODEL_ELEMENT_TYPE_CONNECTION,
        "details": {"name": "conn"},
        "endpoints": {"source": "source", "target": "target"},
        "power_limits": {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([20.0, 20.0]),
            CONF_MAX_POWER_TARGET_SOURCE: np.array([15.0, 15.0]),
        },
        "pricing": {},
        "advanced": {},
    }
    update_element(network, config)

    # Verify updated state - TrackedParams should be updated
    assert power_limit.max_power_source_target[0] == 20.0
    assert power_limit.max_power_target_source[0] == 15.0


def test_update_element_raises_for_missing_model_element() -> None:
    """Test update_element raises ValueError when model element is not found."""
    # Create network with only nodes
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "target", "is_source": False, "is_sink": True})
    # Connection "nonexistent_conn" does NOT exist

    # Try to update a nonexistent element
    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: MODEL_ELEMENT_TYPE_CONNECTION,
        "details": {"name": "nonexistent_conn"},
        "endpoints": {"source": "source", "target": "target"},
        "power_limits": {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([20.0, 20.0]),
            CONF_MAX_POWER_TARGET_SOURCE: np.array([15.0, 15.0]),
        },
        "pricing": {},
        "advanced": {},
    }

    with pytest.raises(ValueError, match="Model element 'nonexistent_conn' not found in network during update"):
        update_element(network, config)
