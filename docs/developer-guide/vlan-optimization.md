# VLAN Optimization

This document analyzes the minimum number of VLANs (tags) required to correctly
model a set of power policies, and the algorithms to achieve that minimum.

## Problem Statement

Each VLAN adds `S × 2 × T` LP variables per connection (`S` segments, 2 directions,
`T` time periods). With `C` connections, the total variable cost is `C × K × S × 2 × T`
where `K` is the number of VLANs. Minimizing `K` directly improves solve time.

## Policy Signatures

The key insight: **VLANs distinguish sources, not destinations.** Destination-specific
pricing is handled by scoped segments at the destination connection. A VLAN only needs
to track *where power came from*.

Two source nodes need separate VLANs **only if** at least one policy treats them
differently. We formalize this as a **policy signature**.

### Definition

For a source node `s`, its policy signature is the set of `(destination, price_st, price_ts)`
tuples from all policies that match `s` as a source:

$$
\text{sig}(s) = \{(d, \pi_{st}, \pi_{ts}) \mid \text{policy}(s \to d, \pi_{st}, \pi_{ts}) \text{ exists}\}
$$

### Equivalence Classes

Sources with identical policy signatures are treated identically by all policies.
They can share a single VLAN without loss of information.

The set of VLANs is the set of **distinct non-empty signatures** plus VLAN 0 (default).

### Proof of Optimality

- **Necessary**: Two sources with different signatures must have different VLANs,
  because at some destination node, the optimizer needs to apply different pricing
  to their power. If they shared a VLAN, the optimizer couldn't distinguish them.

- **Sufficient**: Two sources with identical signatures can share a VLAN. Every
  policy that applies to one also applies to the other with the same parameters.
  The optimizer doesn't need to distinguish between them.

Therefore: **number of VLANs = number of distinct non-empty signatures + 1** is optimal.

## Algorithm

```python
def compute_optimal_vlans(nodes, policies):
    """Compute minimum VLAN assignment from policy rules.
    
    Returns:
        tag_map: dict[node_name, vlan_id] (0 = default/untagged)
    """
    # Step 1: Compute policy signature per node
    signatures: dict[str, frozenset] = {}
    for node in nodes:
        sig = set()
        for policy in policies:
            if matches_source(node, policy.sources):
                for dest in resolve_destinations(policy.destinations, nodes):
                    sig.add((dest, policy.price_st, policy.price_ts))
        signatures[node] = frozenset(sig)
    
    # Step 2: Group by identical signatures
    sig_to_vlan: dict[frozenset, int] = {}
    vlan_counter = 1
    tag_map: dict[str, int] = {}
    
    for node, sig in signatures.items():
        if not sig:
            tag_map[node] = 0  # No policies → default VLAN
            continue
        if sig not in sig_to_vlan:
            sig_to_vlan[sig] = vlan_counter
            vlan_counter += 1
        tag_map[node] = sig_to_vlan[sig]
    
    return tag_map
```

## Examples

### Example 1: Simple Grid Surcharge

```
Nodes: Grid, Solar, Battery, Load
Policy: Grid → Load: $0.05/kWh
```

| Node | Signature | VLAN |
|------|-----------|------|
| Grid | {(Load, 0.05, None)} | 1 |
| Solar | {} | 0 |
| Battery | {} | 0 |
| Load | {} | 0 |

**Result: 2 VLANs** (0 and 1). Solar and Battery share VLAN 0.

### Example 2: Different Source Prices

```
Policy 1: Grid → Load: $0.05/kWh
Policy 2: Solar → Load: $0.02/kWh
```

| Node | Signature | VLAN |
|------|-----------|------|
| Grid | {(Load, 0.05, None)} | 1 |
| Solar | {(Load, 0.02, None)} | 2 |
| Battery | {} | 0 |

**Result: 3 VLANs**. Each source has unique treatment.

### Example 3: Same Price, Different Sources

```
Policy 1: Grid → Load: $0.05/kWh
Policy 2: Solar → Load: $0.05/kWh
```

| Node | Signature | VLAN |
|------|-----------|------|
| Grid | {(Load, 0.05, None)} | 1 |
| Solar | {(Load, 0.05, None)} | 1 |
| Battery | {} | 0 |

**Result: 2 VLANs**. Grid and Solar share VLAN 1 (identical treatment).

### Example 4: Wildcard Source

```
Policy: * → Load: $0.05/kWh
```

| Node | Signature | VLAN |
|------|-----------|------|
| Grid | {(Load, 0.05, None)} | 1 |
| Solar | {(Load, 0.05, None)} | 1 |
| Battery | {(Load, 0.05, None)} | 1 |

**Result: 2 VLANs**. All sources share VLAN 1 (all treated identically).

### Example 5: Complex Policies

```
Policy 1: Grid → Load: $0.05/kWh
Policy 2: Grid → Battery: $0.03/kWh
Policy 3: Solar → Load: $0.02/kWh
```

| Node | Signature | VLAN |
|------|-----------|------|
| Grid | {(Load, 0.05, None), (Battery, 0.03, None)} | 1 |
| Solar | {(Load, 0.02, None)} | 2 |
| Battery | {} | 0 |

**Result: 3 VLANs**. Grid and Solar have different signatures.

## Connection-Level Optimization

A further optimization: **not all connections need all VLANs.**

If a VLAN can never flow through a connection (no path exists from any source
with that VLAN to any destination that consumes it), the connection doesn't need
variables for that VLAN.

### Reachability Analysis

For each VLAN `v`:
1. Find source nodes: `{n | tag_map[n] == v}`
2. Find destination nodes: all destinations referenced by policies matching this VLAN
3. Compute connections on paths between source and destination nodes
4. Only these connections need VLAN `v`

For **tree topologies** (most home energy systems), the path between any two nodes
is unique and can be found in O(N) time. For general graphs, BFS/DFS from each
source set gives reachable connections.

### Variable Savings

With `C` connections and `K` VLANs, the naive approach uses `C × K` tag-connection pairs.
After reachability pruning, only the reachable pairs need variables. For sparse policy
sets (few source→destination pairs relative to the full graph), this can dramatically
reduce variable count.

## Comparison

| Approach | VLANs | Variables per connection | Total variables |
|----------|-------|------------------------|-----------------|
| Naive (1 per source) | N_sources + 1 | (N_sources + 1) × S × 2 × T | C × (N_sources + 1) × S × 2 × T |
| Signature merging | N_signatures + 1 | (N_signatures + 1) × S × 2 × T | C × (N_signatures + 1) × S × 2 × T |
| + Reachability pruning | N_signatures + 1 | varies per connection | Σ_c K_c × S × 2 × T |

Where `N_signatures ≤ N_sources`, and `K_c ≤ K` is the number of VLANs reaching connection `c`.

## Implementation Notes

The signature-based VLAN assignment replaces the current per-source assignment in
`compile_policies()`. The change is localized to the tag assignment step — the rest
of the pipeline (connection tagging, source enforcement, pricing injection) works
the same way with the reduced VLAN set.

Reachability pruning requires access to the network graph topology, which is available
from the connection configs. It can be implemented as an additional step after VLAN
assignment but before connection tagging.

Both optimizations are **semantically equivalent** to the naive approach — the optimizer
produces the same optimal cost. They only affect solve time.
