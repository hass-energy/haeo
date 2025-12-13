"""Graph connectivity utilities."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ConnectivityResult:
    """Result of connectivity analysis for a graph."""

    is_connected: bool
    components: tuple[tuple[str, ...], ...]

    @property
    def num_components(self) -> int:
        """Return count of connected components."""

        return len(self.components)


def _normalize_components(components: Sequence[Iterable[str]]) -> tuple[tuple[str, ...], ...]:
    """Return sorted, deterministic component tuples."""

    ordered = [tuple(sorted(component)) for component in components]
    ordered.sort()
    return tuple(ordered)


def find_connected_components(adjacency: Mapping[str, Iterable[str]]) -> ConnectivityResult:
    """Find connected components in a graph represented as an adjacency map.

    This is a pure graph algorithm that performs depth-first search to identify
    all connected components in an undirected graph.

    Args:
        adjacency: Mapping from node name to iterable of neighbor names.
                  For undirected graphs, if A connects to B, then B should connect to A.

    Returns:
        ConnectivityResult with connectivity status and component groupings.

    Example:
        >>> adjacency = {"a": ["b"], "b": ["a"], "c": []}
        >>> result = find_connected_components(adjacency)
        >>> result.is_connected
        False
        >>> result.components
        (("a", "b"), ("c",))

    """
    if not adjacency:
        return ConnectivityResult(is_connected=True, components=())

    components: list[set[str]] = []
    visited: set[str] = set()

    for node in sorted(adjacency):
        if node in visited:
            continue

        stack = [node]
        component: set[str] = set()

        while stack:
            current = stack.pop()
            visited.add(current)
            component.add(current)
            neighbours = adjacency[current]
            stack.extend(neighbour for neighbour in sorted(neighbours, reverse=True) if neighbour not in visited)

        components.append(component)

    normalized = _normalize_components(components)
    is_connected = len(normalized) <= 1
    return ConnectivityResult(is_connected=is_connected, components=normalized)


__all__ = [
    "ConnectivityResult",
    "find_connected_components",
]
