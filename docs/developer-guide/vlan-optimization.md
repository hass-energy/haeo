# VLAN optimization

This guide describes algorithms that minimize LP variable growth in the power policy system.
See [Power policies](../modeling/tagged-power.md) for the full design context.

## Problem

Each VLAN tag on a connection creates $S \times 2 \times T$ LP variables.
`S` is segments per connection, `2` is direction count, and `T` is period count.
A naive strategy that assigns one VLAN per source node creates unnecessary variables when policies treat sources identically.

## Signature-based merging

### Algorithm

Compute one policy signature per source node.
A signature is the set of destination and price tuples that apply to that source.
Assign the same VLAN to all sources with identical signatures.
Assign VLAN 0 to sources with an empty signature.
Assign increasing non-zero VLAN IDs to each distinct non-empty signature class.

### Correctness

**Necessary.**
Sources with different signatures are treated differently by at least one policy.
If those sources shared a VLAN, the optimizer could not apply distinct policy behavior at the destination.

**Sufficient.**
Sources with identical signatures are treated identically by all policies.
Sharing a VLAN preserves all information needed for optimization.

### Optimality

The VLAN count equals the number of distinct non-empty signatures, plus VLAN 0.
That count is the minimum required for a correct policy representation.

## Reachability pruning

### Algorithm

After VLAN assignment, compute which connections actually need each VLAN using directed reachability.

For each non-zero VLAN, identify the source nodes assigned to that VLAN.
Compute forward reachability from those sources (following connection direction) and backward reachability from *all* sink nodes (reverse direction).
Assign the VLAN only to connections whose endpoints appear in both the forward and backward reachable sets.

Reachability targets every sink in the network, not just the destinations named by policies for that VLAN.
A policy restricts where tagged flow is *priced* — it does not restrict where tagged flow may physically terminate.
If the subgraph were narrowed to policy destinations only, a tagged source would be unable to serve an ordinary sink directly whenever the policy destination's capacity was exhausted, and the solver would be forced to launder power through storage to shed the tag.
Pricing placement (Step 8 of the compilation pipeline) still uses the source-to-policy-destination cut, so non-destination sinks remain policy-free while retaining a direct path.

Forward reachability is also *sink-absorbing* and *source-excluding*: traversal stops at each sink (except the VLAN's own sources), and edges whose target is one of the VLAN's own sources are dropped.
Together these rules mean a tag never leaves a sink, never re-enters its origin, and therefore cannot be laundered through storage to avoid tag-scoped pricing.
See [Node roles and policy scope](../modeling/tagged-power.md#node-roles-and-policy-scope) for the user-facing framing and [Step 4](policy-compilation.md#step-4-reachability-analysis) of the compilation pipeline for the implementation.

### Savings pattern

| Topology     | Naive variable factor | With pruning                 |
| ------------ | --------------------- | ---------------------------- |
| Star         | $C \times K$          | depends on VLAN reachability |
| Linear chain | $C \times K$          | $K \times path\_length$      |
| Tree         | $C \times K$          | $K \times avg\_path\_length$ |

Savings are largest when each VLAN only traverses part of the network.
Expanding targets from policy destinations to all sinks slightly reduces pruning when a source has few policy destinations but many other sinks; the trade-off is sound LP semantics.

## Combined pipeline

1. Compute policy signatures for all source nodes.
2. Merge identical signatures into one VLAN assignment map.
3. Initialize all connections with VLAN 0.
4. For each non-zero VLAN, run reachability between matched sources and all sink nodes.
5. Add that VLAN only to reachable connections.

## Worked examples

### Four nodes, one policy

```
Nodes: Grid, Solar, Battery, Load
Policy: Grid -> Load: $0.05
```

| Step           | Result                                                             |
| -------------- | ------------------------------------------------------------------ |
| Signatures     | Grid={(Load,0.05,None)}, Solar={}, Battery={}, Load={}             |
| VLANs          | Grid=1, others=0, K=2                                              |
| Naive baseline | K=5 (one per node plus default)                                    |
| Reachability   | VLAN 1 appears only on directed path connections from Grid to Load |

### Four nodes, two policies, same price

```
Policy 1: Grid -> Load: $0.05
Policy 2: Solar -> Load: $0.05
```

| Step       | Result                                            |
| ---------- | ------------------------------------------------- |
| Signatures | Grid={(Load,0.05,None)}, Solar={(Load,0.05,None)} |
| VLANs      | Grid=Solar=1, Battery=0, K=2                      |
| Savings    | One VLAN removed versus naive assignment          |

### Wildcard policy

```
Policy: * -> Load: $0.05
```

All source-capable nodes get signature `{(Load,0.05,None)}`.
All source-capable nodes merge into VLAN 1.
`K=2` regardless of node count.

## Complexity

| Operation                    | Time                     | Notes                                     |
| ---------------------------- | ------------------------ | ----------------------------------------- |
| Signature computation        | $O(N \times P \times D)$ | `N` nodes, `P` policies, `D` destinations |
| VLAN assignment              | $O(N)$                   | hash-based grouping                       |
| Reachability (tree)          | $O(K \times N)$          | `K` VLANs, one path search per node pair  |
| Reachability (general graph) | $O(K \times (N + E))$    | graph traversal per VLAN                  |

All steps are polynomial and fast for typical home energy systems, where N < 20 and P < 10.
