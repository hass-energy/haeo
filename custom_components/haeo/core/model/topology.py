"""Serialize network topology to a JSON-friendly structure.

Produces a lightweight graph description suitable for frontend rendering.
Contains only structural data (nodes, edges, segment types) — no time-series
values. Entity IDs are included as references so the frontend can look up
live values from HA states.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements import Battery, Connection, Node


def _get_element_type(element: Element[Any]) -> str:
    """Classify an element into a type string for the topology."""
    if isinstance(element, Battery):
        return "battery"
    if isinstance(element, Node):
        return "node"
    return "unknown"


def _get_parent_device(name: str) -> str:
    """Extract the parent device name from an element name.

    Battery elements use the name prefix before the colon as their group.
    E.g. "Battery:charge" -> "Battery".
    """
    return name.split(":")[0]


def serialize_topology(network: Network) -> dict[str, Any]:
    """Serialize network topology to a JSON structure.

    Returns:
        Dict with "nodes" and "edges" lists describing the graph structure.
        Node values and time-series data are NOT included — the frontend
        should look those up via entity_id references.

    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    groups: dict[str, list[str]] = defaultdict(list)

    # Collect non-connection elements as nodes
    for name, element in sorted(network.elements.items()):
        if isinstance(element, Connection):
            continue

        element_type = _get_element_type(element)
        group = _get_parent_device(name)
        groups[group].append(name)

        nodes.append({
            "name": name,
            "type": element_type,
            "group": group,
        })

    # Collect connections as edges with segment metadata
    for name, element in sorted(network.elements.items()):
        if not isinstance(element, Connection):
            continue

        segments: list[dict[str, str]] = []
        for seg_id, segment in element.segments.items():
            segments.append({
                "id": seg_id,
                "type": type(segment).__name__,
            })

        edges.append({
            "name": name,
            "source": element.source,
            "target": element.target,
            "segments": segments,
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "groups": {k: v for k, v in sorted(groups.items())},
    }
