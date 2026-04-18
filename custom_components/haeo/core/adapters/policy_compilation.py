"""Policy compilation: converts policy configs into tagged power flow constraints.

Implements the full compilation pipeline:
1. Flow enumeration — expand policies into (source, dest, price) tuples
2. Signature computation — per-source policy treatment fingerprint
3. VLAN assignment — merge sources with identical signatures (minimum VLANs)
4. Reachability analysis — which connections need which VLANs
5. Connection tagging — per-connection VLAN sets
6. Node source tags — enforce source provenance
7. Node access lists — which VLANs each node can consume
8. Pricing injection — scoped segments at destinations

See docs/modeling/tagged-power.md for design rationale.
See docs/developer-guide/vlan-optimization.md for optimization proofs.
"""

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from typing import Any, NotRequired, TypedDict

import numpy as np

from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, ModelElementConfig
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig

# Tag 0 is used for untagged/default power flows
DEFAULT_TAG = 0


class CompiledPolicyRule(TypedDict):
    """Normalized policy rule consumed by the compiler."""

    sources: list[str]
    destinations: list[str]
    price: NotRequired[object]


def _make_hashable(value: Any) -> Any:
    """Convert a value to a hashable form for signature computation."""
    if isinstance(value, np.ndarray):
        return tuple(value.flat)
    return value


def _as_name_list(value: object) -> list[str]:
    """Normalize a wildcard/list endpoint field to list[str]."""
    if isinstance(value, list):
        return [name for name in value if isinstance(name, str)]
    return []


def compile_policies(
    elements: list[ModelElementConfig],
    policy_configs: Sequence[Mapping[str, object]],
) -> list[ModelElementConfig]:
    """Compile policy rules into tagged power flow constraints on model elements.

    Mutates element configs in-place, adding tags, outbound_tags,
    inbound_tags, and tag_costs fields as needed.

    Args:
        elements: All model element configs (nodes and connections).
        policy_configs: List of policy rule configs, each with:
            - sources: list of node names, or ["*"] for any
            - destinations: list of node names, or ["*"] for any
            - price: $/kWh or None

    Returns:
        The input elements with policy fields injected.

    """
    if not policy_configs:
        return elements

    # Implicit allow-all: unpolicied flows carry no cost but still get VLANs
    policy_configs = [{"sources": ["*"], "destinations": ["*"]}, *policy_configs]

    # Partition by element type — connections have source/target fields
    connections: list[ConnectionElementConfig] = []
    non_connections: list[ModelElementConfig] = []
    by_name: dict[str, ModelElementConfig] = {}
    for elem in elements:
        if elem["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION:
            connections.append(elem)
        else:
            by_name[elem["name"]] = elem
            non_connections.append(elem)

    if not connections:
        return elements

    names: set[str] = set(by_name.keys())

    conn_by_node: dict[str, list[ConnectionElementConfig]] = defaultdict(list)
    for conn in connections:
        conn_by_node[conn["source"]].append(conn)
        conn_by_node[conn["target"]].append(conn)

    graph: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for conn in connections:
        graph[conn["source"]].add((conn["target"], conn["name"]))
        graph[conn["target"]].add((conn["source"], conn["name"]))

    # --- Step 1: Flow enumeration ---
    flows: list[tuple[str, str, Any]] = []
    for policy in policy_configs:
        sources = _resolve_wildcard(_as_name_list(policy.get("sources")), names)
        destinations = _resolve_wildcard(_as_name_list(policy.get("destinations")), names)
        price = policy.get("price")
        for src in sources:
            flows.extend((src, dst, price) for dst in destinations if src != dst)

    if not flows:
        return elements

    # --- Step 2: Signature computation ---
    signatures: dict[str, frozenset[tuple[str, Any]]] = {}
    for name in names:
        sig = frozenset((dst, _make_hashable(p)) for src, dst, p in flows if src == name)
        signatures[name] = sig

    # --- Step 3: VLAN assignment (signature merging) ---
    sig_to_vlan: dict[frozenset[tuple[str, Any]], int] = {}
    vlan_counter = 1
    tag_map: dict[str, int] = {}

    for name, sig in signatures.items():
        if not sig:
            tag_map[name] = DEFAULT_TAG
            continue
        if sig not in sig_to_vlan:
            sig_to_vlan[sig] = vlan_counter
            vlan_counter += 1
        tag_map[name] = sig_to_vlan[sig]

    active_vlans = sorted({v for v in tag_map.values() if v != DEFAULT_TAG})

    # --- Step 4: Reachability analysis ---
    vlan_connections: dict[int, set[str]] = {}
    for vlan_id in active_vlans:
        source_nodes = {n for n, v in tag_map.items() if v == vlan_id}
        dest_nodes = {dst for src, dst, _ in flows if tag_map.get(src) == vlan_id}
        vlan_connections[vlan_id] = _find_reachable_connections(source_nodes, dest_nodes, graph)

    # --- Step 5: Connection tagging ---
    pair_lookup: dict[tuple[str, str], list[str]] = defaultdict(list)
    for conn in connections:
        pair_lookup[(conn["source"], conn["target"])].append(conn["name"])

    final_vlan_connections: dict[int, set[str]] = {}
    for vlan_id in active_vlans:
        tagged_connections = set(vlan_connections.get(vlan_id, set()))
        reverse_connections = {
            rev
            for conn in connections
            if conn["name"] in tagged_connections
            for rev in pair_lookup.get((conn["target"], conn["source"]), [])
        }
        final_vlan_connections[vlan_id] = tagged_connections | reverse_connections

    for conn in connections:
        tags: set[int] = {DEFAULT_TAG}
        for vlan_id in active_vlans:
            if conn["name"] in final_vlan_connections.get(vlan_id, set()):
                tags.add(vlan_id)
        conn["tags"] = tags

    # --- Step 6: Node outbound tags ---
    for name, vlan_id in tag_map.items():
        if vlan_id != DEFAULT_TAG and name in by_name:
            node = by_name[name]
            if node["element_type"] != MODEL_ELEMENT_TYPE_CONNECTION:
                node["outbound_tags"] = {vlan_id}

    # --- Step 7: Node inbound tags ---
    inbound: dict[str, set[int]] = defaultdict(set)
    for src, dst, _ in flows:
        vlan_id = tag_map.get(src, DEFAULT_TAG)
        if vlan_id != DEFAULT_TAG:
            inbound[dst].add(vlan_id)

    for name, allowed in inbound.items():
        if name in by_name:
            node = by_name[name]
            if node["element_type"] != MODEL_ELEMENT_TYPE_CONNECTION:
                node["inbound_tags"] = allowed

    # --- Step 8: Pricing injection ---
    for policy in policy_configs:
        sources = _resolve_wildcard(_as_name_list(policy.get("sources")), names)
        destinations = _resolve_wildcard(_as_name_list(policy.get("destinations")), names)
        price = policy.get("price")
        if price is None:
            continue

        source_vlans = {tag_map[s] for s in sources if tag_map.get(s, DEFAULT_TAG) != DEFAULT_TAG}
        for source_vlan in source_vlans:
            for dest in destinations:
                for conn in conn_by_node.get(dest, []):
                    if source_vlan not in conn.get("tags", {DEFAULT_TAG}):
                        continue
                    if conn["target"] == dest:
                        conn.setdefault("tag_costs", []).append({"tag": source_vlan, "price": price})

    for conn in connections:
        _merge_tag_costs(conn)

    return [*non_connections, *connections]


def _resolve_wildcard(names: list[str], all_names: set[str]) -> list[str]:
    """Resolve wildcard sources/destinations."""
    if names == ["*"]:
        return sorted(all_names)
    return [n for n in names if n in all_names]


def _merge_tag_costs(conn: ConnectionElementConfig) -> None:
    """Sum duplicate tag_cost rows per tag."""
    raw = conn.get("tag_costs")
    if not raw:
        return
    merged: dict[int, Any] = {}
    for tc in raw:
        if "price" not in tc:
            continue
        tag = tc["tag"]
        p = tc["price"]
        merged[tag] = p if tag not in merged else merged[tag] + p
    conn["tag_costs"] = [{"tag": t, "price": p} for t, p in sorted(merged.items())]


def _find_reachable_connections(
    source_nodes: set[str],
    dest_nodes: set[str],
    graph: Mapping[str, set[tuple[str, str]]],
) -> set[str]:
    """Find connections in the source/destination reachable overlap.

    This uses graph reachability instead of path enumeration so it stays
    linear in graph size and remains stable on cyclic topologies.
    """
    if not source_nodes or not dest_nodes:
        return set()

    reverse_graph: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for current, neighbors in graph.items():
        for neighbor, conn_name in neighbors:
            reverse_graph[neighbor].add((current, conn_name))

    def collect_reachable(start_nodes: set[str], adjacency: Mapping[str, set[tuple[str, str]]]) -> set[str]:
        reachable: set[str] = set()
        queue: deque[str] = deque(start_nodes)
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            for neighbor, _conn_name in adjacency.get(current, set()):
                if neighbor not in reachable:
                    queue.append(neighbor)
        return reachable

    forward_reachable = collect_reachable(source_nodes, graph)
    backward_reachable = collect_reachable(dest_nodes, reverse_graph)

    relevant_nodes = forward_reachable & backward_reachable
    if not relevant_nodes:
        return set()

    return {
        conn_name
        for current in relevant_nodes
        for neighbor, conn_name in graph.get(current, set())
        if neighbor in relevant_nodes
    }
