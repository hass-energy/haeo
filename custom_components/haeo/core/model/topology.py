"""Serialize network topology to a JSON-friendly structure.

Produces a lightweight graph description suitable for frontend rendering.
Contains only structural data (nodes, edges, segment types, VLAN tags) —
no time-series values.
"""

from __future__ import annotations

from collections import defaultdict
from typing import (
    Any,  # noqa: TID251  # Result is an untyped JSON blob consumed by callers (coordinator,
    # frontend, and this module's own tests) that index into nested nodes/edges/policies without
    # narrowing. A precise recursive JSON union type-checks at construction but breaks every such
    # caller (outside this slice); core/ also cannot import homeassistant.util.json.JsonValueType.
)

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.element import NetworkElement
from custom_components.haeo.core.model.elements import Connection
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricing


def serialize_topology(
    network: Network,
    element_types: dict[str, str],
) -> dict[str, Any]:
    """Serialize network topology to a JSON structure.

    Args:
        network: The network to serialize.
        element_types: Mapping of element name to type string
            (e.g. "battery", "grid", "solar").

    Returns:
        Dict with "nodes", "edges", "groups", and optionally "policies"
        describing the full graph structure including tagged power flow routing.

    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    groups: dict[str, list[str]] = defaultdict(list)
    policies: list[dict[str, Any]] = []

    for name, element in sorted(network.elements.items()):
        if isinstance(element, Connection):
            segments: list[dict[str, str]] = [
                {"id": seg_id, "type": type(segment).__name__} for seg_id, segment in element.segments.items()
            ]
            edge_data: dict[str, Any] = {
                "name": name,
                "source": element.source,
                "target": element.target,
                "segments": segments,
            }
            tags = element.connection_tags()
            if tags != {0}:
                edge_data["tags"] = sorted(tags)
            edges.append(edge_data)

        elif isinstance(element, PolicyPricing):
            policy_data: dict[str, Any] = {
                "name": name,
                "terms": [{"connection": t["connection"], "tag": t["tag"]} for t in element.terms],
            }
            if element.label:
                policy_data["label"] = element.label
            policies.append(policy_data)

        else:
            element_type = element_types.get(name, "unknown")
            group = name.split(":")[0]
            groups[group].append(name)
            node_data: dict[str, Any] = {
                "name": name,
                "type": element_type,
                "group": group,
            }
            if isinstance(element, NetworkElement):
                if element.outbound_tags is not None:
                    node_data["outbound_tags"] = sorted(element.outbound_tags)
                if element.inbound_tags is not None:
                    node_data["inbound_tags"] = sorted(element.inbound_tags)
            nodes.append(node_data)

    result: dict[str, Any] = {
        "nodes": nodes,
        "edges": edges,
        "groups": dict(sorted(groups.items())),
    }
    if policies:
        result["policies"] = policies

    return result
