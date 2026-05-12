"""Policy compilation: converts network elements into tagged power flow constraints.

The compiler always runs, even when no policies are configured. This
ensures the network structure (tags, outbound/inbound constraints) is
consistent regardless of whether policies exist. Adding a policy to an
unrelated element does not change how existing elements behave.

Implements the full compilation pipeline:
1. Flow enumeration — expand policies into (source, dest, price) tuples
2. Signature computation — per-source policy treatment fingerprint
3. VLAN assignment — merge sources with identical signatures (minimum VLANs)
4. Reachability analysis — which connections need which VLANs
5. Connection tagging — per-connection VLAN sets
6. Node outbound tags — enforce source provenance
7. Node inbound tags — all active VLANs
8. Pricing injection — per-VLAN sink-side minimum s-t cut placement as
   PolicyPricing model elements with reactive TrackedParam prices

Every source-capable node receives a VLAN through signature merging.
Policied sources get VLANs from their rule signatures; unpolicied sources
share a single VLAN (the empty-signature group) with no pricing elements.
The pricing loop only creates PolicyPricing elements for VLANs that appear
in actual policy rules, so unpolicied VLANs carry zero policy cost without
any special-casing. Sink nodes accept all active VLANs so every source can
reach every sink.

See docs/modeling/tagged-power.md for design rationale.
See docs/developer-guide/vlan-optimization.md for optimization proofs.
"""

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Any, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, ModelElementConfig
from custom_components.haeo.core.model.elements.battery import BatteryElementConfig
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.elements.node import NodeElementConfig
from custom_components.haeo.core.model.elements.policy_pricing import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_POLICY_PRICING
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricingElementConfig, PolicyPricingTerm

# Non-connection element configs (nodes and batteries) that can carry tags
_TaggableConfig = NodeElementConfig | BatteryElementConfig

# A rule grouping identifies a rule by its source/destination sets,
# independent of price. Rules with the same grouping share VLAN structure.
type _RuleGrouping = tuple[frozenset[str], frozenset[str]]


class CompiledPolicyRule(TypedDict):
    """Normalized policy rule consumed by the compiler."""

    sources: list[str]
    destinations: list[str]
    enabled: NotRequired[bool]
    price: float | NDArray[np.floating[Any]]


class CompilationResult(TypedDict):
    """Result of policy compilation."""

    elements: list[ModelElementConfig]
    pricing_rule_map: dict[int, list[str]]


def _as_name_list(value: object) -> list[str]:
    """Normalize a wildcard/list endpoint field to list[str]."""
    if isinstance(value, list):
        return [name for name in value if isinstance(name, str)]
    return []


def compile_policies(
    elements: list[ModelElementConfig],
    policy_configs: Sequence[CompiledPolicyRule],
) -> CompilationResult:
    """Compile policy rules into tagged power flow constraints on model elements.

    Mutates element configs in-place, adding tags, outbound_tags, and
    inbound_tags fields. Generates PolicyPricing model elements for each
    pricing placement.

    Args:
        elements: All model element configs (nodes and connections).
        policy_configs: List of policy rule configs, each with:
            - sources: list of node names, or ["*"] for any
            - destinations: list of node names, or ["*"] for any
            - price: $/kWh (omitted for tagging-only rules)

    Returns:
        CompilationResult with the element configs and a mapping from
        policy rule index to pricing element names.

    """
    # Partition by element type — connections have source/target fields
    connections: list[ConnectionElementConfig] = []
    non_connections: list[ModelElementConfig] = []
    by_name: dict[str, _TaggableConfig] = {}
    for elem in elements:
        if elem["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION:
            connections.append(elem)
        elif elem["element_type"] == MODEL_ELEMENT_TYPE_POLICY_PRICING:
            non_connections.append(elem)
        else:
            by_name[elem["name"]] = elem
            non_connections.append(elem)

    if not connections:
        return CompilationResult(elements=elements, pricing_rule_map={})

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
    # Each rule is identified by its source/destination grouping. Rules with
    # identical groupings are treated as one for VLAN purposes (they differ
    # only in price, which TrackedParams handle reactively).
    rule_groupings: list[_RuleGrouping] = []
    source_memberships: dict[str, set[_RuleGrouping]] = defaultdict(set)
    for policy in policy_configs:
        sources = _resolve_wildcard(_as_name_list(policy["sources"]), names, wildcard_set=source_names)
        destinations = _resolve_wildcard(_as_name_list(policy["destinations"]), names, wildcard_set=sink_names)
        grouping: _RuleGrouping = (frozenset(sources), frozenset(destinations))
        rule_groupings.append(grouping)
        for src in sources:
            if any(dst != src for dst in destinations):
                source_memberships[src].add(grouping)

    # --- Step 2: Signature computation ---
    # Signatures capture which rule groupings apply to each source. Sources
    # that participate in the same set of groupings share a VLAN because
    # they receive identical treatment. Rules with the same source/destination
    # sets but different prices fold together naturally. This keeps the
    # network structure stable across price changes — only PolicyPricing
    # TrackedParams update.
    signatures: dict[str, frozenset[_RuleGrouping]] = {}
    for name in sorted(source_names | set(source_memberships.keys())):
        signatures[name] = frozenset(source_memberships.get(name, set()))

    # --- Step 3: VLAN assignment (signature merging) ---
    # All signatures — including the empty signature shared by unpolicied
    # sources — get a regular VLAN number. Unpolicied sources collapse to
    # one VLAN through signature merging with no pricing elements, since
    # they don't appear in any rule's source list.
    sig_to_vlan: dict[frozenset[_RuleGrouping], int] = {}
    vlan_counter = 1
    tag_map: dict[str, int] = {}

    for name, sig in signatures.items():
        if sig not in sig_to_vlan:
            sig_to_vlan[sig] = vlan_counter
            vlan_counter += 1
        tag_map[name] = sig_to_vlan[sig]

    active_vlans = sorted(set(tag_map.values()))

    # --- Step 4: Reachability analysis ---
    # Tag membership follows source provenance: a tag covers every
    # connection on a directed path from the tag's sources to *any* sink,
    # stopping at each sink (sinks absorb the tag).
    #
    # Reaching every sink (not just policy destinations) is necessary so
    # excess flow has somewhere to go without detouring or being curtailed
    # whenever the source exceeds the policy destination's capacity.
    # Absorbing at sinks prevents phantom passthrough where a storage
    # element (battery) would otherwise allow tagged flow to enter and
    # re-emerge on its outbound edge, laundering provenance and exposing
    # zero-wear arbitrage loops against tag-scoped prices. Pricing is
    # still only placed on the cut separating source from policy-specific
    # destinations (step 8); non-destination sinks remain policy-free.
    tag_connections: dict[int, set[str]] = {}

    for vlan_id in active_vlans:
        source_nodes = {n for n, v in tag_map.items() if v == vlan_id}
        # Per-source reachability with union: each source's self-loop
        # exclusion only blocks edges targeting that specific source.
        # A single call with all source_nodes would exclude edges into
        # ANY source, which breaks when multiple sources share a VLAN
        # (e.g. Grid:export and Battery:charge become unreachable even
        # though they're valid paths for other sources in the VLAN).
        reachable: set[str] = set()
        for src in source_nodes:
            reachable |= _find_reachable_connections({src}, sink_names, directed_graph, absorb_at=sink_names)
        tag_connections[vlan_id] = reachable

    # --- Step 5: Connection tagging ---
    # Each connection carries only tags whose sources can reach it via
    # directed paths. In a well-formed network every connection on a
    # source-to-sink path receives at least one tag.
    for conn in connections:
        tags = {tag_id for tag_id, reachable in tag_connections.items() if conn["name"] in reachable}
        conn["tags"] = tags

    # --- Step 6: Node outbound tags ---
    # Every source in the tag map gets outbound_tags forcing its production
    # onto its assigned VLAN. Unpolicied and policied sources are treated
    # uniformly — the difference is only whether pricing elements exist.
    for name, vlan_id in tag_map.items():
        by_name[name]["outbound_tags"] = {vlan_id}

    # --- Step 7: Node inbound tags ---
    # All sinks accept every active VLAN so both policied and unpolicied
    # power can reach any sink.
    for name in sink_names:
        if name in by_name:
            by_name[name]["inbound_tags"] = set(active_vlans)

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
    # Each placement becomes a PolicyPricing model element with a TrackedParam
    # price, enabling reactive updates when policy values change.
    #
    # Degenerate shapes of the same algorithm:
    #   - specific target: cut collapses to the target's inbound edges,
    #     which uniquely discriminate flow arriving at that target;
    #   - wildcard target with a single-outbound source: cut collapses to
    #     the source's outbound edges (the natural discharge / production
    #     gate);
    #   - shared bottleneck between multiple sources and targets (e.g. an
    #     inverter between DC and AC): cut is the bottleneck edge.
    pricing_elements: list[PolicyPricingElementConfig] = []
    pricing_rule_map: dict[int, list[str]] = {}

    for rule_idx, policy in enumerate(policy_configs):
        sources = _resolve_wildcard(_as_name_list(policy["sources"]), names, wildcard_set=source_names)
        destinations = _resolve_wildcard(_as_name_list(policy["destinations"]), names, wildcard_set=sink_names)
        # Disabled rules compile into the network structure (VLANs, tags)
        # but start with zero price so they have no cost influence.
        # Toggling enabled/disabled updates the TrackedParam reactively.
        price = policy["price"]
        if not policy.get("enabled", True):
            price = 0.0

        sources_by_vlan: dict[int, set[str]] = defaultdict(set)
        for src in sources:
            if src not in tag_map:
                continue
            sources_by_vlan[tag_map[src]].add(src)

        rule_pricing_names: list[str] = []
        for source_vlan, vlan_sources in sorted(sources_by_vlan.items()):
            vlan_edges = [
                (conn["source"], conn["target"], conn["name"])
                for conn in connections
                if source_vlan in conn.get("tags", set())
            ]
            cut = _min_cut_edges(vlan_sources, set(destinations), vlan_edges)
            if not cut:
                continue

            terms: list[PolicyPricingTerm] = [
                PolicyPricingTerm(connection=conn_name, tag=source_vlan) for conn_name in sorted(cut)
            ]
            element_name = f"policy_pricing_r{rule_idx}_v{source_vlan}"
            pricing_elements.append(
                PolicyPricingElementConfig(
                    element_type=MODEL_ELEMENT_TYPE_POLICY_PRICING,
                    name=element_name,
                    price=price,
                    terms=terms,
                )
            )
            rule_pricing_names.append(element_name)

        if rule_pricing_names:
            pricing_rule_map[rule_idx] = rule_pricing_names

    return CompilationResult(
        elements=[*non_connections, *connections, *pricing_elements],
        pricing_rule_map=pricing_rule_map,
    )


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


def _find_reachable_connections(
    source_nodes: set[str],
    dest_nodes: set[str],
    directed_graph: Mapping[str, set[tuple[str, str]]],
    absorb_at: set[str] | None = None,
) -> set[str]:
    """Find connections on directed paths from source_nodes to dest_nodes.

    Uses directed reachability: forward from sources follows connection
    direction (source → target), backward from destinations follows reverse
    direction (target → source). Only connections whose endpoints both appear
    in the intersection of forward and backward reachable sets are included.

    When ``absorb_at`` is provided (typically the set of sink nodes), the
    forward traversal treats those nodes as absorbing: flow may reach them
    but does not continue out of them. This is what gives storage elements
    "tag-absorbing" semantics — a VLAN that reaches a battery does not
    propagate onto that battery's outbound connections, so downstream flow
    is tagged with the battery's own provenance rather than passing
    through. Nodes in ``source_nodes`` are exempt from absorption so the
    VLAN's own sources can still expand outward. Backward traversal is
    unaffected, so sinks on the destination side still trace their way
    back to the appropriate sources.

    Edges whose target lies in ``source_nodes`` are excluded from the
    result to prevent self-loops.  The caller invokes this function
    per-source (one source at a time) and unions the results, so the
    exclusion only blocks edges targeting that specific source — other
    sources in the same VLAN can still reach those edges through their
    own reachability calls.

    Stays linear in graph size and is stable on cyclic topologies.
    """
    if not source_nodes or not dest_nodes:
        return set()

    absorbing = (absorb_at or set()) - source_nodes

    # Build reverse directed graph
    reverse_graph: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for current, neighbors in directed_graph.items():
        for neighbor, conn_name in neighbors:
            reverse_graph[neighbor].add((current, conn_name))

    def collect_reachable(
        start_nodes: set[str],
        adjacency: Mapping[str, set[tuple[str, str]]],
        *,
        stop_at: AbstractSet[str] = frozenset(),
    ) -> tuple[set[str], set[str]]:
        """Return (reachable, expanded) where expanded excludes stop_at nodes."""
        reachable: set[str] = set()
        expanded: set[str] = set()
        queue: deque[str] = deque(start_nodes)
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            if current in stop_at:
                continue
            expanded.add(current)
            for neighbor, _conn_name in adjacency.get(current, set()):
                if neighbor not in reachable:
                    queue.append(neighbor)
        return reachable, expanded

    forward_reachable, forward_expanded = collect_reachable(source_nodes, directed_graph, stop_at=absorbing)
    backward_reachable, _ = collect_reachable(dest_nodes, reverse_graph)

    relevant_nodes = forward_reachable & backward_reachable
    if not relevant_nodes:
        return set()

    # Only emit edges out of nodes we actually expanded forward; edges out
    # of absorbing nodes are excluded so tags stop at the sink.  Edges
    # whose target is the VLAN's own source are also excluded, so tagged
    # flow cannot re-enter its origin and create phantom storage loops.
    return {
        conn_name
        for current in relevant_nodes & forward_expanded
        for neighbor, conn_name in directed_graph.get(current, set())
        if neighbor in relevant_nodes and neighbor not in source_nodes
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

    for src in sorted(effective_sources):
        residual[super_src][src] = inf
    for dst in sorted(effective_destinations):
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
