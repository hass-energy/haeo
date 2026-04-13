# VLAN Optimization

This document describes the algorithms for minimizing the number of LP variables
in the power policy system. See [Power Policies](../modeling/tagged-power.md) for
the full design.

## Problem

Each VLAN (tag) on a connection creates `S × 2 × T` LP variables (segments × directions × periods).
Naive approaches (one VLAN per source node) create unnecessarily many variables when
sources receive identical treatment from policies.

## Signature-Based Merging

### Algorithm

```python
def compute_optimal_vlans(nodes: list[str], policies: list[Policy]) -> dict[str, int]:
    """Assign VLANs based on policy signature equivalence classes.

    Returns: node_name -> vlan_id (0 = default/no policy)
    """
    # Compute signature per source node
    signatures: dict[str, frozenset] = {}
    for node in nodes:
        sig = set()
        for policy in policies:
            if node in resolve_sources(policy.sources, nodes):
                for dest in resolve_destinations(policy.destinations, nodes):
                    sig.add((dest, policy.price_st, policy.price_ts))
        signatures[node] = frozenset(sig)

    # Group nodes by identical signatures → shared VLAN
    sig_to_vlan: dict[frozenset, int] = {}
    vlan_counter = 1
    tag_map: dict[str, int] = {}

    for node, sig in signatures.items():
        if not sig:
            tag_map[node] = 0  # No policies apply
            continue
        if sig not in sig_to_vlan:
            sig_to_vlan[sig] = vlan_counter
            vlan_counter += 1
        tag_map[node] = sig_to_vlan[sig]

    return tag_map
```

### Correctness

**Necessary**: Sources with different signatures have at least one policy that treats
them differently. If they shared a VLAN, the optimizer couldn't apply the correct price
at the discriminating destination. The solution would be suboptimal or incorrect.

**Sufficient**: Sources with identical signatures are treated the same by every policy.
Sharing a VLAN loses no information — the optimizer doesn't need to distinguish them.

### Optimality

The number of VLANs equals the number of distinct non-empty signatures plus one (for
VLAN 0). This is the theoretical minimum for any correct implementation.

## Reachability Pruning

### Algorithm

After VLAN assignment, compute which connections actually need each VLAN:

```python
def compute_reachable_connections(
    vlan_id: int,
    source_nodes: set[str],
    dest_nodes: set[str],
    graph: NetworkGraph,
) -> set[str]:
    """Find connections on any path from sources to destinations."""
    reachable = set()
    for source in source_nodes:
        for dest in dest_nodes:
            path_connections = graph.find_path_connections(source, dest)
            reachable.update(path_connections)
    return reachable
```

For tree topologies, `find_path_connections` is O(N) per pair.

### Savings

| Topology                    | Naive | With pruning                |
| --------------------------- | ----- | --------------------------- |
| Star (all connected to hub) | C × K | varies by VLAN reachability |
| Linear chain                | C × K | K × path_length             |
| Tree                        | C × K | K × avg_path_length         |

The savings are largest when VLANs only need to traverse a fraction of the network.

## Combined Pipeline

```python
def optimize_vlan_assignment(nodes, policies, connections):
    # 1. Signature-based merging
    tag_map = compute_optimal_vlans(nodes, policies)

    # 2. Reachability pruning
    all_tags = set(tag_map.values()) - {0}
    connection_tags = {conn.name: {0} for conn in connections}  # default VLAN 0

    for vlan_id in all_tags:
        source_nodes = {n for n, v in tag_map.items() if v == vlan_id}
        dest_nodes = get_destinations_for_vlan(vlan_id, policies, tag_map)
        reachable = compute_reachable_connections(vlan_id, source_nodes, dest_nodes, graph)
        for conn_name in reachable:
            connection_tags[conn_name].add(vlan_id)

    return tag_map, connection_tags
```

## Worked Examples

### 4 Nodes, 1 Policy

```
Nodes: Grid, Solar, Battery, Load
Policy: Grid → Load: $0.05
```

| Step             | Result                                                 |
| ---------------- | ------------------------------------------------------ |
| Signatures       | Grid={(Load,0.05,None)}, Solar={}, Battery={}, Load={} |
| VLANs            | Grid=1, others=0. **K=2**                              |
| Naive would give | K=5 (one per node + default)                           |
| Reachability     | VLAN 1 only on Grid→SW, SW→Load connections            |

### 4 Nodes, 2 Policies, Same Price

```
Policy 1: Grid → Load: $0.05
Policy 2: Solar → Load: $0.05
```

| Step       | Result                                                             |
| ---------- | ------------------------------------------------------------------ |
| Signatures | Grid={(Load,0.05,None)}, Solar={(Load,0.05,None)} — **identical!** |
| VLANs      | Grid=Solar=1, Battery=0. **K=2**                                   |
| Savings    | 1 VLAN eliminated vs naive (Grid and Solar merged)                 |

### Wildcard Policy

```
Policy: * → Load: $0.05
```

All sources get signature {(Load,0.05,None)}. All merge into VLAN 1.
**K=2** regardless of node count.

## Complexity

| Operation              | Time           | Notes                               |
| ---------------------- | -------------- | ----------------------------------- |
| Signature computation  | O(N × P × D)   | N nodes, P policies, D destinations |
| VLAN assignment        | O(N)           | Hash-based grouping                 |
| Reachability (tree)    | O(K × N)       | K VLANs, N nodes per path search    |
| Reachability (general) | O(K × (N + E)) | BFS per VLAN                        |

All steps are polynomial and fast for home energy systems (N < 20, P < 10).
