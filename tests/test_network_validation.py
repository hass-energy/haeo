"""Tests for network connectivity validation utilities."""

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import ElementConfigSchema
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET
from custom_components.haeo.validation import format_component_summary, validate_network_topology


def _make_participants(
    element_names: list[str], connections: list[tuple[str, str, str]]
) -> dict[str, ElementConfigSchema]:
    """Return participant configs for connectivity testing."""

    participants: dict[str, ElementConfigSchema] = {}

    for name in element_names:
        participants[f"node_{name}"] = {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: name,
        }

    for conn_name, source, target in connections:
        participants[conn_name] = {
            CONF_ELEMENT_TYPE: "connection",
            CONF_NAME: conn_name,
            CONF_SOURCE: source,
            CONF_TARGET: target,
        }

    return participants


def test_check_connectivity_connected() -> None:
    """A fully connected topology reports a single component."""

    participants = _make_participants(["a", "b", "c"], [("ab", "a", "b"), ("bc", "b", "c")])
    result = validate_network_topology(participants)

    assert result.is_connected is True
    assert result.components == (("a", "b", "c"),)


def test_check_connectivity_disconnected_subgraphs() -> None:
    """Separate clusters are reported individually."""

    participants = _make_participants(["a", "b", "c", "d"], [("ab", "a", "b"), ("cd", "c", "d")])
    result = validate_network_topology(participants)

    assert result.is_connected is False
    assert result.components == (("a", "b"), ("c", "d"))


def test_check_connectivity_isolated_element() -> None:
    """Isolated nodes appear as single-item components."""

    participants = _make_participants(["a", "b", "c"], [("ab", "a", "b")])
    result = validate_network_topology(participants)

    assert result.is_connected is False
    assert result.components == (("a", "b"), ("c",))


def test_check_connectivity_empty_network() -> None:
    """Empty networks are considered trivially connected."""

    result = validate_network_topology(_make_participants([], []))

    assert result.is_connected is True
    assert result.components == ()


def test_check_connectivity_connections_only() -> None:
    """Connections referencing endpoints create implicit nodes."""

    participants = _make_participants([], [("conn", "a", "b")])
    result = validate_network_topology(participants)

    assert result.is_connected is True
    assert result.components == (("a", "b"),)


def test_validate_network_topology_disconnected() -> None:
    """Topology validation returns grouped components for disconnected graphs."""

    participants = _make_participants(["a", "b", "c"], [("conn_ab", "a", "b")])
    result = validate_network_topology(participants)

    assert result.is_connected is False
    assert result.components == (("a", "b"), ("c",))
    assert result.component_sets == [{"a", "b"}, {"c"}]
    assert result.num_components == 2

    summary = format_component_summary(result.components)
    assert "1) a, b" in summary
    assert "2) c" in summary


def test_validate_network_topology_connected() -> None:
    """Topology validation reports connected state when all elements link."""

    participants = _make_participants(["a", "b"], [("conn_ab", "a", "b")])
    result = validate_network_topology(participants)

    assert result.is_connected is True
    assert result.components == (("a", "b"),)
    assert result.num_components == 1


def test_validate_network_topology_empty() -> None:
    """Empty participant sets are treated as connected."""

    result = validate_network_topology({})

    assert result.is_connected is True
    assert result.components == ()
    assert result.num_components == 0
