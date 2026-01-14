"""Tests for coordinator network utilities."""

import pytest

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
from custom_components.haeo.model.elements.composite_connection import CompositeConnection


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

    # Verify initial state with type narrowing
    conn = network.elements["conn"]
    assert isinstance(conn, CompositeConnection)
    # Check initial TrackedParam values
    assert conn.max_power_source_target is not None
    assert conn.max_power_target_source is not None
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


def test_update_element_raises_for_missing_model_element() -> None:
    """Test update_element raises ValueError when model element is not found."""
    # Create network with only nodes
    network = Network(name="test", periods=[1.0, 1.0])
    network.add(MODEL_ELEMENT_TYPE_NODE, "source", is_source=True, is_sink=False)
    network.add(MODEL_ELEMENT_TYPE_NODE, "target", is_source=False, is_sink=True)
    # Connection "nonexistent_conn" does NOT exist

    # Try to update a nonexistent element
    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: MODEL_ELEMENT_TYPE_CONNECTION,
        CONF_NAME: "nonexistent_conn",
        CONF_SOURCE: "source",
        CONF_TARGET: "target",
        CONF_MAX_POWER_SOURCE_TARGET: [20.0, 20.0],
        CONF_MAX_POWER_TARGET_SOURCE: [15.0, 15.0],
    }

    with pytest.raises(ValueError, match="Model element 'nonexistent_conn' not found in network during update"):
        update_element(network, config)
