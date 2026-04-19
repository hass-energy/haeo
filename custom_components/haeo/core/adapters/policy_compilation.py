"""Policy compilation: converts policy configs into tagged power flow constraints.

Implements the full compilation pipeline:
1. Flow enumeration — expand policies into (source, dest, price) tuples
2. Signature computation — per-source policy treatment fingerprint
3. VLAN assignment — merge sources with identical signatures (minimum VLANs)
4. Reachability analysis — which connections need which VLANs
5. Connection tagging — per-connection VLAN sets
6. Node outbound tags — enforce source provenance
7. Node inbound tags — default-allow with all active VLANs
8. Pricing injection — scoped segments at destinations

Default-allow model: unpolicied sources produce on tag 0 (the default tag),
which all connections carry. Policied sources are forced onto their VLAN by
outbound_tags. Sink nodes accept all active VLANs plus tag 0, so both
policied and unpolicied power can reach any sink. Costs are applied only at
destinations where explicit policies exist (via tag_costs).

See docs/modeling/tagged-power.md for design rationale.
See docs/developer-guide/vlan-optimization.md for optimization proofs.
"""

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from typing import Any, NotRequired, TypedDict

import numpy as np

from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, ModelElementConfig
from custom_components.haeo.core.model.elements.battery import BatteryElementConfig
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.elements.node import NodeElementConfig

# Tag 0 is used for untagged/default power flows
DEFAULT_TAG = 0

# Non-connection element configs (nodes and batteries) that can carry tags
_TaggableConfig = NodeElementConfig | BatteryElementConfig


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

    # Partition by element type — connections have source/target fields
    connections: list[ConnectionElementConfig] = []
    non_connections: list[ModelElementConfig] = []
    by_name: dict[str, _TaggableConfig] = {}
    for elem in elements:
        if elem["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION:
            connections.append(elem)
        else:
            by_name[elem["name"]] = elem
            non_connections.append(elem)

    if not connections:
        return elements

    names: set[str] = set(by_name.keys())

    # Capability sets for wildcard expansion: nodes that can only produce
    # should not appear as destinations, and nodes that can only consume
    # should not appear as sources. Batteries default to both.
    source_names = {name for name, elem in by_name.items() if elem.get("is_source", True)}
    sink_names = {name for name, elem in by_name.items() if elem.get("is_sink", True)}

    conn_by_node: dict[str, list[ConnectionElementConfig]] = defaultdict(list)
    for conn in connections:
        conn_by_node[conn["source"]].append(conn)
        conn_by_node[conn["target"]].append(conn)

    # Directed graph: edges follow connection direction (source → target)
    directed_graph: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for conn in connections:
        directed_graph[conn["source"]].add((conn["target"], conn["name"]))

    # --- Step 1: Flow enumeration ---
    flows: list[tuple[str, str, Any]] = []
    for policy in policy_configs:
        sources = _resolve_wildcard(_as_name_list(policy.get("sources")), names, wildcard_set=source_names)
        destinations = _resolve_wildcard(_as_name_list(policy.get("destinations")), names, wildcard_set=sink_names)
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
        # Tagged power must be able to reach ALL nodes, not just the
        # policy destination — otherwise it gets stranded at intermediate
        # nodes with no exit path (e.g., solar power cant reach load).
        # Use all node names as destinations for reachability.
        dest_nodes = names
        vlan_connections[vlan_id] = _find_reachable_connections(source_nodes, dest_nodes, directed_graph)

    # --- Step 5: Connection tagging ---
    for conn in connections:
        tags: set[int] = {DEFAULT_TAG}
        for vlan_id in active_vlans:
            if conn["name"] in vlan_connections.get(vlan_id, set()):
                tags.add(vlan_id)
        conn["tags"] = tags

    # --- Step 6: Node outbound tags ---
    # Policied sources produce on their VLAN. Unpolicied source-capable nodes
    # produce on tag 0 only, preventing unnecessary production decomposition.
    for name, vlan_id in tag_map.items():
        node = by_name[name]
        if vlan_id != DEFAULT_TAG:
            node["outbound_tags"] = {vlan_id}
        elif name in source_names:
            node["outbound_tags"] = {DEFAULT_TAG}

    # --- Step 7: Node inbound tags ---
    # Default-allow: all sinks accept tag 0 (unpolicied power) plus all
    # active policy VLANs. Policied sources reach sinks on their assigned
    # VLAN via outbound_tags, not via DEFAULT_TAG.
    for name in sink_names:
        if name in by_name:
            by_name[name]["inbound_tags"] = {DEFAULT_TAG} | set(active_vlans)

    # --- Step 8: Pricing injection ---
    for policy in policy_configs:
        sources = _resolve_wildcard(_as_name_list(policy.get("sources")), names, wildcard_set=source_names)
        destinations = _resolve_wildcard(_as_name_list(policy.get("destinations")), names, wildcard_set=sink_names)
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


def _resolve_wildcard(
    names: list[str],
    all_names: set[str],
    *,
    wildcard_set: set[str] | None = None,
) -> list[str]:
    """Resolve wildcard sources/destinations.

    When wildcard_set is provided, ["*"] expands to that set instead of
    all_names. This filters wildcards to only capability-matching nodes
    (e.g., sources that can actually produce power).
    """
    if names == ["*"]:
        return sorted(wildcard_set if wildcard_set is not None else all_names)
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
    directed_graph: Mapping[str, set[tuple[str, str]]],
) -> set[str]:
    """Find connections on directed paths from source_nodes to dest_nodes.

    Uses directed reachability: forward from sources follows connection
    direction (source → target), backward from destinations follows reverse
    direction (target → source). Only connections whose endpoints both appear
    in the intersection of forward and backward reachable sets are included.

    Stays linear in graph size and is stable on cyclic topologies.
    """
    if not source_nodes or not dest_nodes:
        return set()

    # Build reverse directed graph
    reverse_graph: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for current, neighbors in directed_graph.items():
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

    forward_reachable = collect_reachable(source_nodes, directed_graph)
    backward_reachable = collect_reachable(dest_nodes, reverse_graph)

    relevant_nodes = forward_reachable & backward_reachable
    if not relevant_nodes:
        return set()

    return {
        conn_name
        for current in relevant_nodes
        for neighbor, conn_name in directed_graph.get(current, set())
        if neighbor in relevant_nodes
    }
