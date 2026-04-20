"""Policy compilation: converts policy configs into tagged power flow constraints.

Implements the full compilation pipeline:
1. Flow enumeration — expand policies into (source, dest, price) tuples
2. Signature computation — per-source policy treatment fingerprint
3. VLAN assignment — merge sources with identical signatures (minimum VLANs)
4. Reachability analysis — which connections need which VLANs
5. Connection tagging — per-connection VLAN sets
6. Node outbound tags — enforce source provenance
7. Node inbound tags — default-allow with all active VLANs
8. Pricing injection — per-VLAN sink-side minimum s-t cut placement

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
    # Iterate names in sorted order so VLAN assignment below is deterministic
    # regardless of Python hash randomization.
    signatures: dict[str, frozenset[tuple[str, Any]]] = {}
    for name in sorted(names):
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
    # VLAN membership follows source provenance: a VLAN covers every
    # connection on a directed path from the VLAN's sources to *any* sink.
    #
    # Restricting to policy destinations alone would force tagged flow to
    # detour through a battery (or curtail) whenever the source exceeds
    # the policy destination's capacity, because non-destination sinks
    # would refuse the VLAN tag. Pricing is still only placed on the cut
    # separating source from policy-specific destinations (step 8);
    # non-destination sinks remain policy-free.
    vlan_connections: dict[int, set[str]] = {}
    for vlan_id in active_vlans:
        source_nodes = {n for n, v in tag_map.items() if v == vlan_id}
        vlan_connections[vlan_id] = _find_reachable_connections(source_nodes, sink_names, directed_graph)

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
    # For each VLAN participating in a rule, place the price on a minimum
    # edge cut separating that VLAN's sources from the rule's destinations
    # in the VLAN subgraph. The sink-side canonical min-cut (closest to the
    # destinations) is an antichain: every source→destination path crosses
    # exactly one cut edge, so a unit of flow pays the price exactly once
    # regardless of path length. It also minimises the number of places
    # operations are installed (a single power-limit policy becomes a single
    # sum-over-cut constraint rather than one per destination).
    #
    # Degenerate shapes of the same algorithm:
    #   - specific target: cut collapses to the target's inbound edges,
    #     which uniquely discriminate flow arriving at that target;
    #   - wildcard target with a single-outbound source: cut collapses to
    #     the source's outbound edges (the natural discharge / production
    #     gate);
    #   - shared bottleneck between multiple sources and targets (e.g. an
    #     inverter between DC and AC): cut is the bottleneck edge.
    conn_by_name: dict[str, ConnectionElementConfig] = {conn["name"]: conn for conn in connections}
    for policy in policy_configs:
        sources = _resolve_wildcard(_as_name_list(policy.get("sources")), names, wildcard_set=source_names)
        destinations = _resolve_wildcard(_as_name_list(policy.get("destinations")), names, wildcard_set=sink_names)
        price = policy.get("price")
        if price is None:
            continue

        sources_by_vlan: dict[int, set[str]] = defaultdict(set)
        for src in sources:
            vlan = tag_map.get(src, DEFAULT_TAG)
            if vlan == DEFAULT_TAG:
                continue
            sources_by_vlan[vlan].add(src)

        for source_vlan, vlan_sources in sources_by_vlan.items():
            vlan_edges = [
                (conn["source"], conn["target"], conn["name"])
                for conn in connections
                if source_vlan in conn.get("tags", {DEFAULT_TAG})
            ]
            cut = _min_cut_edges(vlan_sources, set(destinations), vlan_edges)
            for conn_name in cut:
                conn_by_name[conn_name].setdefault("tag_costs", []).append({"tag": source_vlan, "price": price})

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


def _min_cut_edges(
    sources: set[str],
    destinations: set[str],
    directed_edges: Sequence[tuple[str, str, str]],
) -> set[str]:
    """Return connection names on a sink-side minimum s-t cut.

    Solves max s-t flow with unit capacity on each internal directed edge
    (Edmonds-Karp BFS) and returns the cut closest to the destination side:
    the S-side is every node from which ``SUPER_DST`` is NOT reachable in
    the final residual graph, so the cut lands where source-tagged flow
    converges onto the destination boundary.

    The returned cut has two properties we rely on for policy placement:

    * every s→t path in ``directed_edges`` crosses exactly one cut edge
      (it is a directed antichain), so a unit of flow can be priced or
      capacity-constrained exactly once without double-counting;
    * the cut has minimum cardinality, so the number of places where
      constraints / costs are installed is minimised.

    Degenerate shapes this collapses to:

    * single target → target-inbound edges (discriminates flow arriving
      at that target);
    * wildcard target with a single-outbound source → source-outbound
      edges;
    * a bottleneck shared by all source→destination paths (e.g. an
      inverter linking a DC bus to an AC bus) → the bottleneck edge.

    Parallel edges between the same ``(u, v)`` pair share one aggregated
    flow variable with capacity equal to the number of parallels; if the
    aggregate lies on the cut, every parallel connection name is returned.
    """
    if not sources or not destinations:
        return set()
    # Self-loops (a node that is both a source and a destination) carry no
    # meaningful flow from the node to itself; drop them from destinations
    # only so that multi-source/multi-dest rules with overlap still find a
    # cut for the non-overlapping destinations.
    effective_destinations = destinations - sources
    if not effective_destinations:
        return set()
    effective_sources = sources

    super_src = "\x00__min_cut_src__"
    super_dst = "\x00__min_cut_dst__"
    inf = float("inf")

    residual: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    conns_by_pair: dict[tuple[str, str], list[str]] = defaultdict(list)

    for src in effective_sources:
        residual[super_src][src] = inf
    for dst in effective_destinations:
        residual[dst][super_dst] = inf
    for u, v, conn_name in directed_edges:
        residual[u][v] += 1
        conns_by_pair[(u, v)].append(conn_name)

    def _bfs_augmenting_path() -> dict[str, str] | None:
        parent: dict[str, str] = {}
        visited = {super_src}
        queue: deque[str] = deque([super_src])
        while queue:
            u = queue.popleft()
            for v, cap in residual[u].items():
                if v not in visited and cap > 0:
                    visited.add(v)
                    parent[v] = u
                    if v == super_dst:
                        return parent
                    queue.append(v)
        return None

    while (parent := _bfs_augmenting_path()) is not None:
        path_flow = inf
        v = super_dst
        while v in parent:
            u = parent[v]
            path_flow = min(path_flow, residual[u][v])
            v = u
        v = super_dst
        while v in parent:
            u = parent[v]
            residual[u][v] -= path_flow
            residual[v][u] += path_flow
            v = u

    # Sink-side canonical cut: T = {nodes from which super_dst is reachable
    # via forward residual edges}. Equivalently, a forward BFS in the
    # reverse residual from super_dst.
    reverse_adj: dict[str, list[str]] = defaultdict(list)
    for u, outbound in residual.items():
        for v, cap in outbound.items():
            if cap > 0:
                reverse_adj[v].append(u)

    t_side = {super_dst}
    queue = deque([super_dst])
    while queue:
        v = queue.popleft()
        for u in reverse_adj[v]:
            if u not in t_side:
                t_side.add(u)
                queue.append(u)

    cut_conn_names: set[str] = set()
    for (u, v), conn_names in conns_by_pair.items():
        if u not in t_side and v in t_side:
            cut_conn_names.update(conn_names)
    return cut_conn_names
