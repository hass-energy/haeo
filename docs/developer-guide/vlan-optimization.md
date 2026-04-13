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

After VLAN assignment, compute which connections actually need each VLAN.

For each non-zero VLAN, identify the source nodes assigned to that VLAN.
Identify destination nodes that policies allow for that VLAN's signature class.
Compute the set of path connections between those source and destination sets.
Assign the VLAN only to those reachable connections.

### Savings pattern

| Topology     | Naive variable factor | With pruning                 |
| ------------ | --------------------- | ---------------------------- |
| Star         | $C \times K$          | depends on VLAN reachability |
| Linear chain | $C \times K$          | $K \times path\_length$      |
| Tree         | $C \times K$          | $K \times avg\_path\_length$ |

Savings are largest when each VLAN only traverses part of the network.

## Combined pipeline

1. Compute policy signatures for all source nodes.
2. Merge identical signatures into one VLAN assignment map.
3. Initialize all connections with VLAN 0.
4. For each non-zero VLAN, run reachability between matched sources and destinations.
5. Add that VLAN only to reachable connections.

## Worked examples

### Four nodes, one policy

```
Nodes: Grid, Solar, Battery, Load
Policy: Grid -> Load: $0.05
```

| Step           | Result                                                    |
| -------------- | --------------------------------------------------------- |
| Signatures     | Grid={(Load,0.05,None)}, Solar={}, Battery={}, Load={}    |
| VLANs          | Grid=1, others=0, K=2                                     |
| Naive baseline | K=5 (one per node plus default)                           |
| Reachability   | VLAN 1 appears only on path connections from Grid to Load |

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

All sources get signature `{(Load,0.05,None)}`.
All sources merge into VLAN 1.
`K=2` regardless of node count.

## Complexity

| Operation                    | Time                     | Notes                                     |
| ---------------------------- | ------------------------ | ----------------------------------------- |
| Signature computation        | $O(N \times P \times D)$ | `N` nodes, `P` policies, `D` destinations |
| VLAN assignment              | $O(N)$                   | hash-based grouping                       |
| Reachability (tree)          | $O(K \times N)$          | `K` VLANs, one path search per node pair  |
| Reachability (general graph) | $O(K \times (N + E))$    | graph traversal per VLAN                  |

All steps are polynomial.
In practice, signature merging and reachability pruning significantly reduce variable growth versus naive tagging.
