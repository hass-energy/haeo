"""Tests for graph connectivity utilities."""

from custom_components.haeo.util.graph import find_connected_components


def test_find_connected_components_empty() -> None:
    """Empty graph is considered connected."""
    result = find_connected_components({})
    assert result.is_connected is True
    assert result.components == ()
    assert result.num_components == 0


def test_find_connected_components_single_node() -> None:
    """Single isolated node forms one component."""
    adjacency = {"a": []}
    result = find_connected_components(adjacency)
    assert result.is_connected is True
    assert result.components == (("a",),)
    assert result.num_components == 1


def test_find_connected_components_connected_pair() -> None:
    """Two connected nodes form one component."""
    adjacency = {"a": ["b"], "b": ["a"]}
    result = find_connected_components(adjacency)
    assert result.is_connected is True
    assert result.components == (("a", "b"),)


def test_find_connected_components_disconnected_pair() -> None:
    """Two isolated nodes form two components."""
    adjacency = {"a": [], "b": []}
    result = find_connected_components(adjacency)
    assert result.is_connected is False
    assert result.components == (("a",), ("b",))
    assert result.num_components == 2


def test_find_connected_components_chain() -> None:
    """Chain of connected nodes forms one component."""
    adjacency = {"a": ["b"], "b": ["a", "c"], "c": ["b"]}
    result = find_connected_components(adjacency)
    assert result.is_connected is True
    assert result.components == (("a", "b", "c"),)


def test_find_connected_components_cycle() -> None:
    """Cycle in graph is handled correctly."""
    adjacency = {"a": ["b", "c"], "b": ["a", "c"], "c": ["a", "b"]}
    result = find_connected_components(adjacency)
    assert result.is_connected is True
    assert result.components == (("a", "b", "c"),)


def test_find_connected_components_multiple_clusters() -> None:
    """Multiple disconnected clusters are identified."""
    adjacency = {
        "a": ["b"],
        "b": ["a"],
        "c": ["d"],
        "d": ["c"],
        "e": [],
    }
    result = find_connected_components(adjacency)
    assert result.is_connected is False
    assert result.components == (("a", "b"), ("c", "d"), ("e",))
    assert result.num_components == 3


def test_find_connected_components_component_sets() -> None:
    """Component sets property returns mutable sets."""
    adjacency = {"a": ["b"], "b": ["a"], "c": []}
    result = find_connected_components(adjacency)
    assert result.component_sets == [{"a", "b"}, {"c"}]
