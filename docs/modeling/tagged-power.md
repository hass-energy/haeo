# Power policies

Power policies attach provenance to power flow so the optimizer can distinguish costs and limits that depend on where the energy originates.
This page describes the modelling framework: the abstract structure, the mathematical formulation, and the algorithm that turns a set of policy rules into a linear program.

See [policy compilation](../developer-guide/policy-compilation.md) for the concrete compilation pipeline and [VLAN optimization](../developer-guide/vlan-optimization.md) for the pruning algorithms used in production.

## Motivation

A plain energy LP minimises total cost without tracking provenance.
Once power enters the network it is fungible: a kilowatt-hour from the grid is indistinguishable from a kilowatt-hour from local generation, and the solver is free to substitute one for the other.
That suffices for systems whose economics depend only on total energy,
but many real tariffs, constraints and internal valuations are explicitly source-aware.

Network charges, feed-in tariffs and storage wear valuations all share a common shape:
the applicable price or limit depends on the history of a particular unit of energy, not only on where it is currently flowing.
Power policies introduce that history as a multi-commodity flow: every distinguishable provenance becomes its own commodity ("tag"), and policies scope prices and limits to the flow of specific tags across specific sub-networks.

## Design inspiration

The formulation borrows concepts from tagged-flow control in packet networks.
Each tag is analogous to a VLAN identifier: a label carried alongside a flow that partitions physical network capacity into logical per-tag flows, sharing underlying edges but with independent balance and capacity accounting on each edge.
Tag assignment follows the optimisation principle behind MPLS label merging — flows that receive identical treatment from every downstream rule can share a label without loss of information — so provenance is tracked at the granularity of distinguishable treatment rather than per individual source.
Policy compilation itself plays the role of an SDN controller: it derives per-edge per-tag flow rules from the high-level policy set and emits them as constraints on the LP, which remains unaware of the policies themselves.

## Semantics

### Node roles and policy scope

Every node has two independent capability bits: whether it can emit power (*source-capable*) and whether it can absorb power (*sink-capable*).
Their combination determines how tags flow through the node.

- A source-capable, non-sink node originates its assigned tag and carries no other tag inbound.
- A sink-capable, non-source node terminates every tag that reaches it.
- A node with both capabilities originates its own tag and terminates every other tag that reaches it.
- A node with neither capability is a *junction* that passes every tag through unchanged.

The operative rule is **a sink terminates every tag that is not its own**.
Tagged flow that reaches a sink is consumed there; any power that continues onward from the same node re-originates under a new tag determined by that node's own source capability, or under the default tag if it has none.

This rule constrains the subgraph over which a policy can apply prices.
A policy extends only through the subgraph reachable from its sources up to the nearest sinks.
Intermediate sinks absorb the tag, and legs downstream of such a sink fall under the provenance of that intermediate node instead.
For a tag to traverse a routing node on its way to a downstream destination, the routing node must therefore be a junction.

### Default-allow model

In the absence of any policy, every connection carries a single default tag and the formulation coincides with the untagged LP.
Introducing policies adds tags only where provenance is distinguishable; unpolicied flow continues on the default tag at zero policy cost.
Sinks admit both default-tagged flow and every active policy tag, so adding a policy cannot make a previously-feasible schedule infeasible.

### Policy stacking

Policies that match overlapping source-destination pairs combine *additively* on each matching flow.
Prices sum, and limits apply as the intersection of feasible regions.
This falls out of each policy contributing an independent pricing or capacity term to the LP, with no override relationship between them:
a specific rule therefore layers on top of a broader rule without restating it.

### Group constraints

A policy whose source list (or destination list) enumerates multiple elements applies its terms to the *sum* of the corresponding tag flows.
Combined with single-source policies, this allows both aggregate and per-source bounds to coexist on the same physical subgraph: the aggregate bound constrains $\sum_v P^v$ while per-source bounds constrain each $P^v$ separately.

## Mathematical formulation

### Per-tag power variables

Each connection carries one non-negative flow variable per direction, per tag, per period:

$$
P^{st}_{v,e,t} \ge 0, \quad P^{ts}_{v,e,t} \ge 0
\quad \forall v \in \text{Tags}(e), \; e \in \text{Edges}, \; t \in \{0, \ldots, T-1\}
$$

### Aggregate flow in segment constraints

Per-connection segment constraints (capacity, pricing, efficiency) operate on the aggregate directional flow:

$$
P^{st}_{e,t} = \sum_{v \in \text{Tags}(e)} P^{st}_{v,e,t}
$$

This keeps segment formulations tag-agnostic while preserving per-tag identity for policy-scoped constraints.

### Per-tag balance

Node balance holds independently for each tag admitted at a node $n$:

$$
\sum_{e \in \text{out}(n)} P^{st}_{v,e,t} - \sum_{e \in \text{in}(n)} P^{st}_{v,e,t} = b_{n,v,t}
$$

where $b_{n,v,t}$ is the node's net production on tag $v$.
The node-role semantics above determine which tags carry which sign of $b$:
source-only nodes have $b > 0$ only on their own tag, sink-only nodes have $b \le 0$ on any admitted tag, and junctions have $b = 0$ for every tag.

### Policy pricing

Each policy contributes a pricing term summed over its *priced edges* — the minimum edge cut on the policy's tag subgraph separating the policy's sources from its destinations:

$$
C_{\text{policy}} = \sum_{e \in \text{cut}} \sum_t P^{st}_{v,e,t} \cdot \pi \cdot \Delta t
$$

Unit edge capacities on the cut guarantee that every source-to-destination path on the tag crosses exactly one priced edge, so each unit of tagged flow pays $\pi$ exactly once and no path bypasses the policy.
Power-limit policies use the same cut to enforce $\sum_{e \in \text{cut}} P^{st}_{v,e,t} \le X$; minimising the cut keeps the constraint over the fewest edges.

## Compilation algorithm

Translating a policy set into the LP constructs above has three algorithmic stages.

### Tag assignment by signature merging

Each source is summarised by its *policy signature*: the set of destination-price tuples in which it participates.
Sources with identical signatures receive identical downstream treatment and are merged to share a tag; sources with distinct signatures require distinct tags.
The resulting tag count is the number of distinct non-empty signatures plus one default tag, which is the provable minimum required to keep every policy distinguishable.

### Reachability with absorbing sinks and source exclusion

Each tag is assigned only to edges that can carry it on some source-to-sink path.
Forward reachability propagates from the tag's sources; backward reachability propagates from all sink nodes; the intersection determines the edges that receive the tag.
Two additional rules keep provenance consistent:

- **Sink absorption.** Forward traversal stops at each sink, except when the sink is one of the tag's own sources.
- **Source exclusion.** Edges whose target is one of the tag's own sources are removed from the result.

Absorbing at sinks prevents a tag from propagating through a storage element and leaving under its original provenance;
source exclusion prevents a tag from re-entering its origin via a return path, which would otherwise admit zero-cost internal loops that bypass any cost placed on an outbound cut.

### Pricing placement by minimum s-t cut

For each policy, the pricing term is attached to the edges of the minimum s-t cut on that policy's tag subgraph between its sources and destinations.
Unit edge capacities and the sink-side canonical cut jointly ensure every source-to-destination path crosses exactly one priced edge.
The minimum-cardinality cut collapses naturally to intuitive placements — onto a single inbound edge when the destination has one inbound, onto a single outbound edge when the source has one outbound, and onto a shared bottleneck when sources and destinations converge through a narrower middle.

## Variable count

Per connection, the number of tagged flow variables scales with the number of tags that actually reach the connection:

$$
|\text{vars}(e)| = K(e) \cdot S(e) \cdot 2 \cdot T
$$

where $K(e)$ is the tag count on edge $e$, $S(e)$ the number of segments on that connection, and $T$ the horizon length.
Three structural bounds shape variable growth:

- In the absence of policies, $K(e) = 1$ for every edge.
- Signature merging caps the global tag count at the number of distinct non-empty signatures plus one.
- Reachability pruning reduces $K(e)$ on any edge that lies outside a given tag's source-to-sink subgraph.

Practical variable growth therefore tracks the number of *distinguishable* policy groupings rather than the number of policies or the number of sources.

## Future work: SOC-based tags

State-of-charge partitioning could be expressed as separate tags assigned to different SOC regions of a storage element, enabling SOC-dependent valuation through the same tag machinery.
This remains an open modelling direction.

## Next Steps

<div class="grid cards" markdown>

- :material-cog-play:{ .lg .middle } **Policy walkthrough**

    ---

    Configure policy rules end to end in Home Assistant.

    [:material-arrow-right: Power policies walkthrough](../walkthroughs/power-policies.md)

- :material-wrench:{ .lg .middle } **Compilation internals**

    ---

    Review the concrete compilation pipeline and algorithm steps.

    [:material-arrow-right: Policy compilation](../developer-guide/policy-compilation.md)

- :material-network:{ .lg .middle } **VLAN optimization**

    ---

    Dive into signature merging and tag minimization rationale.

    [:material-arrow-right: VLAN optimization](../developer-guide/vlan-optimization.md)

</div>
