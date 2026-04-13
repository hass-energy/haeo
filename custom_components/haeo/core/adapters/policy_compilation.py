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

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG


def compile_policies(
    elements: list[dict[str, Any]],
    policy_configs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compile policy rules into tagged power flow constraints on model elements.

    Args:
        elements: All model element configs (nodes and connections).
        policy_configs: List of policy rule configs, each with:
            - sources: list of node names, or ["*"] for any
            - destinations: list of node names, or ["*"] for any
            - price_source_target: $/kWh or None
            - price_target_source: $/kWh or None

    Returns:
        Modified elements list with tags, source_tags, access_lists, and
        scoped segments injected.

    """
    if not policy_configs:
        return elements

    # Separate element types (mutable copies)
    connections: list[dict[str, Any]] = []
    elements_by_name: dict[str, dict[str, Any]] = {}
    other: list[dict[str, Any]] = []
    for elem in elements:
        etype = elem.get("element_type")
        copy = dict(elem)
        if etype == "connection":
            connections.append(copy)
        else:
            # All non-connection elements (nodes, batteries, etc.) can be tagged
            elements_by_name[copy["name"]] = copy
            other.append(copy)

    if not connections:
        return elements

    # All element names (anything a connection can connect to)
    element_names: set[str] = set(elements_by_name.keys())

    # Build adjacency: node_name -> list of (connection, "source"|"target")
    conn_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for conn in connections:
        conn_by_node[conn["source"]].append(conn)
        conn_by_node[conn["target"]].append(conn)

    # Build graph edges for reachability: node -> set of (neighbor, connection_name)
    graph: dict[str, set[tuple[str, str]]] = defaultdict(set)
    conn_by_name: dict[str, dict[str, Any]] = {}
    for conn in connections:
        src, tgt = conn["source"], conn["target"]
        name = conn["name"]
        graph[src].add((tgt, name))
        graph[tgt].add((src, name))
        conn_by_name[name] = conn

    # --- Step 1: Flow enumeration ---
    flows: list[tuple[str, str, Any, Any]] = []  # (source, dest, price_st, price_ts)
    for policy in policy_configs:
        sources = _resolve_wildcard(policy.get("sources", []), element_names)
        destinations = _resolve_wildcard(policy.get("destinations", []), element_names)
        price_st = policy.get("price_source_target")
        price_ts = policy.get("price_target_source")
        for src in sources:
            flows.extend((src, dst, price_st, price_ts) for dst in destinations if src != dst)

    if not flows:
        return elements

    # --- Step 2: Signature computation ---
    # Per source node: frozenset of (dest, price_st, price_ts) tuples
    signatures: dict[str, frozenset[tuple[str, Any, Any]]] = {}
    for name in element_names:
        sig = frozenset((dst, pst, pts) for src, dst, pst, pts in flows if src == name)
        signatures[name] = sig

    # --- Step 3: VLAN assignment (signature merging) ---
    sig_to_vlan: dict[frozenset[tuple[str, Any, Any]], int] = {}
    vlan_counter = 1
    tag_map: dict[str, int] = {}  # node_name -> vlan_id

    for name, sig in signatures.items():
        if not sig:
            tag_map[name] = DEFAULT_TAG
            continue
        if sig not in sig_to_vlan:
            sig_to_vlan[sig] = vlan_counter
            vlan_counter += 1
        tag_map[name] = sig_to_vlan[sig]

    active_vlans = sorted({v for v in tag_map.values() if v != DEFAULT_TAG})
    if not active_vlans:
        return elements

    # --- Step 4: Reachability analysis ---
    # For each VLAN, find connections on paths from source nodes to destination nodes
    vlan_connections: dict[int, set[str]] = {}
    for vlan_id in active_vlans:
        source_nodes = {n for n, v in tag_map.items() if v == vlan_id}
        # Destinations for this VLAN: all dests from flows where source has this VLAN
        dest_nodes = {dst for src, dst, _, _ in flows if tag_map.get(src) == vlan_id}
        reachable = _find_reachable_connections(source_nodes, dest_nodes, graph)
        vlan_connections[vlan_id] = reachable

    # --- Step 5: Connection tagging ---
    # Build a lookup: (src, tgt) -> list of connection names
    conn_pair_lookup: dict[tuple[str, str], list[str]] = defaultdict(list)
    for conn in connections:
        conn_pair_lookup[(conn["source"], conn["target"])].append(conn["name"])

    for conn in connections:
        conn_name = conn["name"]
        tags = {DEFAULT_TAG}
        for vlan_id in active_vlans:
            if conn_name in vlan_connections.get(vlan_id, set()):
                tags.add(vlan_id)
                # Also tag the reverse direction connection (if it exists)
                src, tgt = conn["source"], conn["target"]
                for reverse_name in conn_pair_lookup.get((tgt, src), []):
                    vlan_connections[vlan_id].add(reverse_name)
        conn["tags"] = sorted(tags)

    # Second pass: pick up tags added by reverse-direction tagging above
    for conn in connections:
        conn_name = conn["name"]
        tags = set(conn.get("tags", [DEFAULT_TAG]))
        for vlan_id in active_vlans:
            if conn_name in vlan_connections.get(vlan_id, set()):
                tags.add(vlan_id)
        conn["tags"] = sorted(tags)

    # --- Step 6: Node source tags ---
    for name, vlan_id in tag_map.items():
        if vlan_id != DEFAULT_TAG and name in elements_by_name:
            elements_by_name[name]["source_tag"] = vlan_id

    # --- Step 7: Node access lists ---
    # Which VLANs each node can consume
    access_lists: dict[str, set[int]] = defaultdict(set)
    for src, dst, _, _ in flows:
        vlan_id = tag_map.get(src, DEFAULT_TAG)
        if vlan_id != DEFAULT_TAG:
            access_lists[dst].add(vlan_id)

    for name, allowed_vlans in access_lists.items():
        if name in elements_by_name:
            elements_by_name[name]["access_list"] = sorted(allowed_vlans)

    # --- Step 8: Pricing injection via tag_costs (not separate segments) ---
    for policy in policy_configs:
        sources = _resolve_wildcard(policy.get("sources", []), element_names)
        destinations = _resolve_wildcard(policy.get("destinations", []), element_names)
        price_st = policy.get("price_source_target")
        price_ts = policy.get("price_target_source")

        if price_st is None and price_ts is None:
            continue

        # Collect unique source VLANs for this policy
        source_vlans = {tag_map[s] for s in sources if tag_map.get(s, DEFAULT_TAG) != DEFAULT_TAG}

        for source_vlan in source_vlans:
            for dest_node in destinations:
                if dest_node not in element_names:
                    continue
                dest_conns = conn_by_node.get(dest_node, [])
                for conn in dest_conns:
                    # Only add pricing if this connection has the VLAN
                    if source_vlan not in conn.get("tags", []):
                        continue

                    # Build tag cost entry — only on connections flowing toward destination
                    tag_cost: dict[str, Any] = {"tag": source_vlan}

                    if conn.get("target") == dest_node and price_st is not None:
                        tag_cost["price"] = price_st

                    if "price" in tag_cost:
                        tag_costs = conn.setdefault("tag_costs", [])
                        tag_costs.append(tag_cost)

    return [*other, *connections]


def _resolve_wildcard(names: list[str], all_names: set[str]) -> list[str]:
    """Resolve wildcard sources/destinations."""
    if names == ["*"]:
        return sorted(all_names)
    return [n for n in names if n in all_names]


def _find_reachable_connections(
    source_nodes: set[str],
    dest_nodes: set[str],
    graph: Mapping[str, set[tuple[str, str]]],
) -> set[str]:
    """Find all connections on any path from source nodes to destination nodes.

    Uses BFS from each source node, collecting connections on paths to destinations.
    For tree topologies (no cycles), each path is unique and optimal.
    """
    reachable_connections: set[str] = set()

    for source in source_nodes:
        # BFS to find paths to all destinations
        visited: set[str] = set()
        queue: list[tuple[str, list[str]]] = [(source, [])]
        visited.add(source)

        while queue:
            current, path_conns = queue.pop(0)

            if current in dest_nodes and current != source:
                # Found a destination — all connections on this path are reachable
                reachable_connections.update(path_conns)

            for neighbor, conn_name in graph.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, [*path_conns, conn_name]))

    return reachable_connections
