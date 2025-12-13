"""Tests for graph connectivity utilities."""

from typing import TypedDict

import pytest

from custom_components.haeo.util.graph import find_connected_components


class TestCase(TypedDict):
    """Test case for find_connected_components."""

    description: str
    adjacency: dict[str, list[str]]
    expected_is_connected: bool
    expected_components: tuple[tuple[str, ...], ...]
    expected_num_components: int


TEST_CASES: dict[str, TestCase] = {
    "empty": {
        "description": "empty graph is considered connected",
        "adjacency": {},
        "expected_is_connected": True,
        "expected_components": (),
        "expected_num_components": 0,
    },
    "single_node": {
        "description": "single isolated node forms one component",
        "adjacency": {"a": []},
        "expected_is_connected": True,
        "expected_components": (("a",),),
        "expected_num_components": 1,
    },
    "connected_pair": {
        "description": "two connected nodes form one component",
        "adjacency": {"a": ["b"], "b": ["a"]},
        "expected_is_connected": True,
        "expected_components": (("a", "b"),),
        "expected_num_components": 1,
    },
    "disconnected_pair": {
        "description": "two isolated nodes form two components",
        "adjacency": {"a": [], "b": []},
        "expected_is_connected": False,
        "expected_components": (("a",), ("b",)),
        "expected_num_components": 2,
    },
    "chain": {
        "description": "chain of connected nodes forms one component",
        "adjacency": {"a": ["b"], "b": ["a", "c"], "c": ["b"]},
        "expected_is_connected": True,
        "expected_components": (("a", "b", "c"),),
        "expected_num_components": 1,
    },
    "cycle": {
        "description": "cycle in graph is handled correctly",
        "adjacency": {"a": ["b", "c"], "b": ["a", "c"], "c": ["a", "b"]},
        "expected_is_connected": True,
        "expected_components": (("a", "b", "c"),),
        "expected_num_components": 1,
    },
    "multiple_clusters": {
        "description": "multiple disconnected clusters are identified",
        "adjacency": {"a": ["b"], "b": ["a"], "c": ["d"], "d": ["c"], "e": []},
        "expected_is_connected": False,
        "expected_components": (("a", "b"), ("c", "d"), ("e",)),
        "expected_num_components": 3,
    },
}


@pytest.mark.parametrize("test_case", TEST_CASES.values(), ids=TEST_CASES.keys())
def test_find_connected_components(test_case: TestCase) -> None:
    """Test find_connected_components with various graph structures."""
    result = find_connected_components(test_case["adjacency"])
    assert result.is_connected is test_case["expected_is_connected"], test_case["description"]
    assert result.components == test_case["expected_components"], test_case["description"]
    assert result.num_components == test_case["expected_num_components"], test_case["description"]
