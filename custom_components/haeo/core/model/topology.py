"""Serialize network topology to a JSON-friendly structure.

Produces a lightweight graph description suitable for frontend rendering.
Contains only structural data (nodes, edges, segment types, VLAN tags) —
no time-series values. Entity IDs are included as references so the frontend
can look up live values from HA states.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements import Battery, Connection, Node
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricing


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


def serialize_topology(
    network: Network,
    element_types: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Serialize network topology to a JSON structure.

    Args:
        network: The network to serialize.
        element_types: Optional mapping of element name to type string
            (e.g. "battery", "grid", "solar"). If not provided, types are
            inferred from model classes (battery/node only).

    Returns:
        Dict with "nodes", "edges", "groups", and "vlans" describing the
        full graph structure including tagged power flow routing.

    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    groups: dict[str, list[str]] = defaultdict(list)

    # Collect non-connection elements as nodes
    for name, element in sorted(network.elements.items()):
        if isinstance(element, (Connection, PolicyPricing)):
            continue

        element_type = (
            element_types.get(name) if element_types else None
        ) or _get_element_type(element)
        group = _get_parent_device(name)
        groups[group].append(name)

        node_data: dict[str, Any] = {
            "name": name,
            "type": element_type,
            "group": group,
        }

        # Add VLAN tag info if present
        outbound = getattr(element, "outbound_tags", None)
        inbound = getattr(element, "inbound_tags", None)
        if outbound is not None:
            node_data["outbound_tags"] = sorted(outbound)
        if inbound is not None:
            node_data["inbound_tags"] = sorted(inbound)

        nodes.append(node_data)

    # Collect connections as edges with segment metadata and tags
    for name, element in sorted(network.elements.items()):
        if not isinstance(element, Connection):
            continue

        segments: list[dict[str, str]] = []
        for seg_id, segment in element.segments.items():
            segments.append({
                "id": seg_id,
                "type": type(segment).__name__,
            })

        edge_data: dict[str, Any] = {
            "name": name,
            "source": element.source,
            "target": element.target,
            "segments": segments,
        }

        # Add VLAN tags carried by this connection
        tags = element.connection_tags()
        if tags != {0}:
            edge_data["tags"] = sorted(tags)

        edges.append(edge_data)

    # Collect policy pricing placements (min-cut positions)
    policies: list[dict[str, Any]] = []
    for name, element in sorted(network.elements.items()):
        if not isinstance(element, PolicyPricing):
            continue
        policies.append({
            "name": name,
            "terms": [
                {"connection": t["connection"], "tag": t["tag"]}
                for t in element.terms
            ],
        })

    result: dict[str, Any] = {
        "nodes": nodes,
        "edges": edges,
        "groups": dict(sorted(groups.items())),
    }

    # Only include policies section if there are any
    if policies:
        result["policies"] = policies

    return result
