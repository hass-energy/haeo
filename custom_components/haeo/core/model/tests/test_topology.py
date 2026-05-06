"""Unit tests for serialize_topology."""

import numpy as np

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY as ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION as ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE as ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.policy_pricing import ELEMENT_TYPE as ELEMENT_TYPE_POLICY_PRICING
from custom_components.haeo.core.model.topology import serialize_topology


def _make_network() -> Network:
    """Create a basic network for topology tests."""
    return Network(name="test", periods=np.array([1.0, 1.0, 1.0]))


def test_empty_network() -> None:
    """Serialize an empty network."""
    network = _make_network()
    result = serialize_topology(network, element_types={})

    assert result == {"nodes": [], "edges": [], "groups": {}}
    assert "policies" not in result


def test_single_node() -> None:
    """Serialize a network with one node."""
    network = _make_network()
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "Grid", "is_sink": True, "is_source": True})

    result = serialize_topology(network, element_types={"Grid": "grid"})

    assert len(result["nodes"]) == 1
    assert result["nodes"][0] == {"name": "Grid", "type": "grid", "group": "Grid"}
    assert result["groups"] == {"Grid": ["Grid"]}
    assert result["edges"] == []


def test_connection_produces_edge() -> None:
    """Connections serialize as edges with segments."""
    network = _make_network()
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "Bat", "capacity": 10.0, "initial_charge": 5.0})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "Hub", "is_sink": True, "is_source": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "Bat:link",
            "source": "Bat",
            "target": "Hub",
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 5.0}},
        }
    )

    result = serialize_topology(
        network,
        element_types={"Bat": "battery", "Hub": "node"},
    )

    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["name"] == "Bat:link"
    assert edge["source"] == "Bat"
    assert edge["target"] == "Hub"
    assert len(edge["segments"]) == 1
    assert edge["segments"][0]["type"] == "PowerLimitSegment"
    # No tags when connection has no VLAN routing
    assert "tags" not in edge


def test_connection_tags_excluded_when_only_zero() -> None:
    """Tags == {0} are excluded from output (default tag)."""
    network = _make_network()
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Source",
            "is_sink": False,
            "is_source": True,
            "outbound_tags": {0},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Sink",
            "is_sink": True,
            "is_source": False,
            "inbound_tags": {0},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "Source:link",
            "source": "Source",
            "target": "Sink",
            "tags": {0},
        }
    )

    result = serialize_topology(
        network,
        element_types={"Source": "solar", "Sink": "load"},
    )

    edge = result["edges"][0]
    assert "tags" not in edge


def test_connection_tags_included_when_nonzero() -> None:
    """Non-zero tags are included in edge output."""
    network = _make_network()
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Source",
            "is_sink": False,
            "is_source": True,
            "outbound_tags": {1, 2},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Sink",
            "is_sink": True,
            "is_source": False,
            "inbound_tags": {1, 2},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "Source:link",
            "source": "Source",
            "target": "Sink",
            "tags": {1, 2},
        }
    )

    result = serialize_topology(
        network,
        element_types={"Source": "solar", "Sink": "load"},
    )

    edge = result["edges"][0]
    assert edge["tags"] == [1, 2]


def test_node_outbound_inbound_tags() -> None:
    """Nodes with VLAN tags include them in serialization."""
    network = _make_network()
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Solar",
            "is_sink": False,
            "is_source": True,
            "outbound_tags": {1, 2},
            "inbound_tags": {3},
        }
    )

    result = serialize_topology(network, element_types={"Solar": "solar"})

    node = result["nodes"][0]
    assert node["outbound_tags"] == [1, 2]
    assert node["inbound_tags"] == [3]


def test_node_without_tags_omits_fields() -> None:
    """Nodes without explicit tags don't include tag fields."""
    network = _make_network()
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "Hub", "is_sink": True, "is_source": True})

    result = serialize_topology(network, element_types={"Hub": "node"})

    node = result["nodes"][0]
    assert "outbound_tags" not in node
    assert "inbound_tags" not in node


def test_policy_pricing_serialization() -> None:
    """PolicyPricing elements serialize into the policies list."""
    network = _make_network()
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Solar",
            "is_sink": False,
            "is_source": True,
            "outbound_tags": {1},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Load",
            "is_sink": True,
            "is_source": False,
            "inbound_tags": {1},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "Solar:export",
            "source": "Solar",
            "target": "Load",
            "tags": {1},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_POLICY_PRICING,
            "name": "solar_self_consumption",
            "label": "Solar → Load",
            "price": 0.05,
            "terms": [{"connection": "Solar:export", "tag": 1}],
        }
    )

    result = serialize_topology(
        network,
        element_types={"Solar": "solar", "Load": "load"},
    )

    assert "policies" in result
    assert len(result["policies"]) == 1
    policy = result["policies"][0]
    assert policy["name"] == "solar_self_consumption"
    assert policy["label"] == "Solar → Load"
    assert policy["terms"] == [{"connection": "Solar:export", "tag": 1}]


def test_policy_pricing_without_label() -> None:
    """PolicyPricing without a label omits the label field."""
    network = _make_network()
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "A", "is_sink": False, "is_source": True})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "B", "is_sink": True, "is_source": False})
    network.add({"element_type": ELEMENT_TYPE_CONNECTION, "name": "A:link", "source": "A", "target": "B"})
    network.add(
        {
            "element_type": ELEMENT_TYPE_POLICY_PRICING,
            "name": "pricing_rule",
            "price": 0.10,
            "terms": [{"connection": "A:link", "tag": 0}],
        }
    )

    result = serialize_topology(network, element_types={"A": "solar", "B": "load"})

    policy = result["policies"][0]
    assert "label" not in policy


def test_groups_from_name_prefix() -> None:
    """Nodes with shared prefixes are grouped together."""
    network = _make_network()
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Battery:cell1",
            "is_sink": True,
            "is_source": True,
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_NODE,
            "name": "Battery:cell2",
            "is_sink": True,
            "is_source": True,
        }
    )

    result = serialize_topology(
        network,
        element_types={"Battery:cell1": "battery", "Battery:cell2": "battery"},
    )

    assert result["groups"] == {"Battery": ["Battery:cell1", "Battery:cell2"]}


def test_groups_sorted_alphabetically() -> None:
    """Groups are sorted alphabetically in output."""
    network = _make_network()
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "Zebra", "is_sink": True, "is_source": True})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "Alpha", "is_sink": True, "is_source": True})

    result = serialize_topology(
        network,
        element_types={"Zebra": "node", "Alpha": "node"},
    )

    assert list(result["groups"].keys()) == ["Alpha", "Zebra"]
