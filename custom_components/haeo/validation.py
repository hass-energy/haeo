"""Validation helpers for HAEO network topology."""

from collections.abc import Mapping, Sequence
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .elements import ELEMENT_TYPE_CONNECTION, ElementConfigSchema, collect_element_subentries
from .util.graph import ConnectivityResult as NetworkConnectivityResult
from .util.graph import find_connected_components


def collect_participant_configs(entry: ConfigEntry) -> dict[str, ElementConfigSchema]:
    """Return a mutable copy of participant configurations for an entry."""

    participants: dict[str, ElementConfigSchema] = {}

    for subentry in collect_element_subentries(entry):
        participants[subentry.name] = subentry.config.copy()

    return participants


def _build_adjacency(
    participants: Mapping[str, ElementConfigSchema],
) -> dict[str, set[str]]:
    """Build adjacency map from element configurations.

    Extracts topology information directly from config schemas without
    loading sensor data. Elements define their connections via:
    - 'connection' field: target node for elements like battery, grid, solar, load
    - 'source'/'target' fields: endpoints for explicit connection elements

    This function creates implicit sub-nodes for elements that have internal structure
    (like batteries with sections) to match what the adapter layer would produce.
    """
    adjacency: dict[str, set[str]] = {}

    for name, config in participants.items():
        element_type = config.get("element_type")

        if element_type == ELEMENT_TYPE_CONNECTION:
            # Explicit connection element - creates edge between source and target
            # Connection elements are not network nodes themselves, just edges
            source: Any = config.get("source")
            target: Any = config.get("target")
            if source and target:
                adjacency.setdefault(source, set()).add(target)
                adjacency.setdefault(target, set()).add(source)
        elif "connection" in config:
            # Element with implicit connection to a target node
            # Add the element as a node
            adjacency.setdefault(name, set())
            target_node: Any = config.get("connection")
            if target_node:
                # Create edge from element to its connection target
                adjacency.setdefault(name, set()).add(target_node)
                adjacency.setdefault(target_node, set()).add(name)
        else:
            # Element without connection (e.g., node) - just add as node
            adjacency.setdefault(name, set())

    return adjacency


def validate_network_topology(
    participants: Mapping[str, ElementConfigSchema],
) -> NetworkConnectivityResult:
    """Validate connectivity for the provided participant configurations.

    Extracts topology directly from configuration schemas without loading
    sensor data. This enables validation during config flow before any
    sensor values are available.

    Args:
        participants: Map of element names to their configurations.

    Returns:
        NetworkConnectivityResult indicating connectivity status.

    """
    if not participants:
        return NetworkConnectivityResult(is_connected=True, components=())

    adjacency = _build_adjacency(participants)
    return find_connected_components(adjacency)


def format_component_summary(components: Sequence[Sequence[str]], *, separator: str = "\n") -> str:
    """Create human-readable summary of disconnected components."""

    lines: list[str] = []
    for index, component in enumerate(components, start=1):
        names = ", ".join(component)
        lines.append(f"{index}) {names}")
    return separator.join(lines)


__all__ = [
    "NetworkConnectivityResult",
    "collect_participant_configs",
    "format_component_summary",
    "validate_network_topology",
]
