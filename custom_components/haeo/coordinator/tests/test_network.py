"""Tests for coordinator network utilities."""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.coordinator.network import update_element
from custom_components.haeo.core.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments import EfficiencySegment, PowerLimitSegment
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.connection import (
    CONF_MAX_POWER_SOURCE_TARGET,
    SECTION_EFFICIENCY,
    SECTION_ENDPOINTS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)


def test_update_element_updates_tracked_params() -> None:
    """Test update_element updates TrackedParams on existing elements."""
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
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )

    conn = network.elements["conn"]
    assert isinstance(conn, Connection)
    pl = conn.segments["power_limit"]
    assert isinstance(pl, PowerLimitSegment)
    assert pl.max_power is not None
    assert pl.max_power[0] == 10.0

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([20.0, 20.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }
    update_element(network, config)

    assert pl.max_power[0] == 20.0


def test_update_element_raises_for_missing_model_element() -> None:
    """Test update_element raises ValueError when model element is not found."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "target", "is_source": False, "is_sink": True})

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "nonexistent_conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([20.0, 20.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }

    with pytest.raises(ValueError, match="Model element 'nonexistent_conn' not found in network during update"):
        update_element(network, config)


def test_update_element_allows_empty_efficiency_section() -> None:
    """Clearing optional efficiency should behave as 100% and not crash optimization."""
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
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([0.95, 0.95])},
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([10.0, 10.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }
    update_element(network, config)

    conn = network.elements["conn"]
    assert isinstance(conn, Connection)
    efficiency = conn.segments["efficiency"]
    assert isinstance(efficiency, EfficiencySegment)
    assert efficiency.efficiency is None

    network.optimize()


def test_update_element_raises_on_empty_tuple_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict tuple update paths must be non-empty tuples of strings."""
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
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )

    def fake_model_elements(_config: ElementConfigData) -> list[dict[Any, Any]]:
        bad: dict[Any, Any] = {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
        }
        bad[()] = 1.0
        return [bad]

    monkeypatch.setattr(connection_adapter, "model_elements", fake_model_elements)

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([10.0, 10.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }

    with pytest.raises(ValueError, match="Invalid update path"):
        update_element(network, config)


def test_update_element_raises_on_malformed_tuple_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tuple paths must contain only string segments."""
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
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )

    def fake_model_elements(_config: ElementConfigData) -> list[dict[Any, Any]]:
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                (1, "bad"): 1.0,
            }
        ]

    monkeypatch.setattr(connection_adapter, "model_elements", fake_model_elements)

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([10.0, 10.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }

    with pytest.raises(ValueError, match="Invalid update path"):
        update_element(network, config)


def test_update_element_skips_non_string_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-string keys in model element updates are ignored."""
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
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )

    def fake_model_elements(_config: ElementConfigData) -> list[dict[Any, Any]]:
        row: dict[Any, Any] = {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "target",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power": np.array([33.0, 33.0]),
                },
            },
        }
        row[999] = "ignored"
        return [row]

    monkeypatch.setattr(connection_adapter, "model_elements", fake_model_elements)

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([10.0, 10.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }

    update_element(network, config)

    conn = network.elements["conn"]
    assert isinstance(conn, Connection)
    pl = conn.segments["power_limit"]
    assert isinstance(pl, PowerLimitSegment)
    assert pl.max_power is not None
    assert pl.max_power[0] == 33.0


def test_update_element_ignores_non_strict_resolve_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Updates that fail path resolution are skipped when not marked strict."""
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
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )

    def fake_model_elements(_config: ElementConfigData) -> list[dict[str, Any]]:
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "source",
                "target": "target",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": np.array([44.0, 44.0]),
                    },
                },
                "nonesuch": {"x": 1.0},
            }
        ]

    monkeypatch.setattr(connection_adapter, "model_elements", fake_model_elements)

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([10.0, 10.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }

    update_element(network, config)

    conn = network.elements["conn"]
    assert isinstance(conn, Connection)
    pl = conn.segments["power_limit"]
    assert isinstance(pl, PowerLimitSegment)
    assert pl.max_power is not None
    assert pl.max_power[0] == 44.0


def test_update_element_strict_tuple_propagates_set_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict tuple paths surface ValueError from invalid final keys."""
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
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )

    def fake_model_elements(_config: ElementConfigData) -> list[dict[Any, Any]]:
        row: dict[Any, Any] = {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "target",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power": np.array([10.0, 10.0]),
                },
            },
        }
        row["segments", "power_limit", "nonexistent"] = np.array([1.0])
        return [row]

    monkeypatch.setattr(connection_adapter, "model_elements", fake_model_elements)

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "conn",
        SECTION_ENDPOINTS: {
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: np.array([10.0, 10.0]),
        },
        SECTION_PRICING: {},
        SECTION_EFFICIENCY: {},
    }

    with pytest.raises(ValueError, match=r"Invalid update path|missing attribute|missing key"):
        update_element(network, config)
