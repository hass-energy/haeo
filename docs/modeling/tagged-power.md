# Power policies

Power policies control how energy flows through the HAEO network based on provenance.
They define which sources can reach which destinations, at what cost, and with what limits.

## Motivation

Standard HAEO minimizes total cost without tracking where power originates.
A kilowatt from the grid is indistinguishable from a kilowatt from solar once it enters the network.
That behavior is often sufficient for simple systems.
Real-world energy economics can still depend on provenance.

- **Network usage charges**: Grid power can incur distribution fees that local generation does not.
- **Feed-in tariffs**: Export rates can differ by source.
- **Demand constraints**: Some destinations should only draw from specific sources.
- **Battery wear valuation**: Battery-sourced power can carry an internal cycling cost.

Policies add provenance tracking so the optimizer can make source-aware decisions.

## Design inspiration

The policy system borrows concepts from networking, where tagged flow control is well established.

### VLAN analogy

Power policies use integer tags that are analogous to VLAN IDs in Ethernet.

| Network concept  | HAEO equivalent          | Purpose                                  |
| ---------------- | ------------------------ | ---------------------------------------- |
| VLAN ID          | Power tag (integer)      | Identifies power provenance              |
| Trunk port       | Interior connection      | Carries multiple tags between nodes      |
| Access port      | Endpoint connection      | Node produces or consumes specific tags  |
| VLAN access list | Node inbound tags        | Defines which tags a node can consume    |
| Firewall rule    | Policy rule              | Prices specific source-destination flows |
| Default allow    | Implicit policy behavior | No policy means free flow on tag 0       |

### Multi-commodity flow

Tagged power flow is a multi-commodity flow formulation.
Each tag acts as a separate commodity with its own flow variables.
All commodities share the same physical network capacities.
This is a standard LP formulation that HiGHS solves natively.

### MPLS label optimization

VLAN assignment is inspired by MPLS label optimization.
Flows with identical treatment can share labels in MPLS.
HAEO applies the same principle by letting sources with identical policy signatures share a tag.

### SDN and OpenFlow

The compilation pipeline mirrors software-defined networking patterns.
A central controller (the compilation step) derives flow rules from high-level policies and installs them on switches (connections and nodes).
The data plane (the LP model) executes those rules without understanding the policies themselves.

## Semantics

### Node roles and policy scope

Every element in a HAEO network is classified by two independent flags: `is_source` (can produce power) and `is_sink` (can consume power).
The combination determines how policy tags flow through the element, which in turn determines where policies apply.

| Role         | `is_source` | `is_sink` | Example elements            | Tag behaviour                                  |
| ------------ | ----------- | --------- | --------------------------- | ---------------------------------------------- |
| **Source**   | `true`      | `false`   | Solar                       | Originates its own tag                         |
| **Sink**     | `false`     | `true`    | Load, Grid-export-only      | Terminates any tag arriving at it              |
| **Storage**  | `true`      | `true`    | Battery, Grid (bi-dir)      | Originates its own tag *and* terminates others |
| **Junction** | `false`     | `false`   | Inverter, Switchboard, Node | Passes every tag through unchanged             |

The operative rule is: **sinks terminate provenance**.
When tagged power arrives at a sink, the tag stops there.
If the sink is also a source (storage), it re-emits power on *its own* tag, not on whatever tag it received.
Only junctions — elements that are neither source nor sink — pass tags through unchanged.

This directly constrains what a policy can price:

- A policy with `source=X` can only price edges on the path *from X to the nearest sink it reaches*.
- If some other sink sits between X and the policy's named destination, the policy does not follow the energy past that intermediate sink.
- The energy still flows, just under a new tag — whatever provenance the intermediate sink emits as, or the default tag 0 if it is a pure sink.

!!! example "Worked consequence"

    ```
    Solar → Switchboard → Load → ???
    ```

    A policy `Solar → *: $0.01/kWh` prices the Solar-tagged flow up to Load (Load is a sink — the tag terminates).
    There is no "onward" flow downstream of a pure Load.

    ```
    Solar → Switchboard → Battery → Switchboard → Grid
    ```

    A policy `Solar → Grid: $0.02/kWh` prices the Solar → Battery leg only.
    Once energy is stored, it is "Battery power" — any onward pricing must come from a `Battery → Grid` policy, not from the `Solar → Grid` one.
    This is what prevents the optimiser from "laundering" solar through the battery to dodge a per-source tariff.

### Choosing roles when building a system

When you are modelling a new topology, the decision tree for each element is:

1. **Does it generate or consume real energy?**
    - Generates → source (Solar, Grid-import).
    - Consumes → sink (Load, Grid-export).
    - Stores → both (Battery, bidirectional Grid).
    - Neither → junction (Inverter, Switchboard, Node with `is_source=false, is_sink=false`).
2. **Do you want a policy to follow the energy past this point?**
    - If yes, it must be a junction.
    - If no, it must be a sink (storage counts).

A common modelling mistake is using a battery or a load as a routing hub.
Because sinks terminate provenance, any policy that was supposed to price downstream flow will no longer apply past that element.
If you genuinely need a routing hub, model it as a plain `Node` element with both flags off and attach the real sink/source element beside it:

```mermaid
graph LR
    Solar[Solar] --> Switchboard[Switchboard Node]
    Switchboard --> Load[Load]
    Switchboard --> Grid[Grid]
    Switchboard --> Battery[Battery]
```

Here the Switchboard is a junction, so a `Solar → Grid` policy's tag can travel all the way to the Grid edge.
Battery and Load sit beside the junction, each with their own tag provenance.

See [Node element configuration](../user-guide/elements/node.md#source-and-sink-combinations) for practical examples.

### Default behavior without policies

When no policies are configured, behavior matches standard HAEO.
All connections carry only tag 0.
Power is fungible and provenance is not tracked.

### Default-allow model

Policies add costs to specific flows.
Flows without a matching policy are unrestricted.

- **Policied sources**: Assigned a VLAN and forced onto it via `outbound_tags`. Their power carries the configured policy costs at the destination.
- **Unpolicied sources**: Produce on tag 0 (the default tag) at zero policy cost.
- **Sink nodes**: Accept all active VLANs plus tag 0, so both policied and unpolicied power can reach any sink.
- **Wildcard matching**: `sources: ["*"]` or `destinations: ["*"]` matches capability-appropriate nodes (sources or sinks respectively).

This model avoids creating unnecessary VLANs for unpolicied flows.
Only sources with explicit policies receive non-zero tags.

### Policy stacking

Policies are additive.
When multiple policies match the same source-destination pair, all matching rules apply.

- **Pricing**: Matching prices sum — Battery paying `$0.05` (group policy) and `$0.03` (individual policy) pays `$0.08` total.
- **Limits**: Matching constraints all apply, and the effective limit is their combined feasible region.

Policies do not override one another.
A specific policy stacks on top of broader policies.

```
Policy 1: Battery+Solar -> Load: $0.05/kWh   (group)
Policy 2: Battery -> Load: $0.03/kWh         (individual)
```

| Source          | Policies matched    | Total price |
| --------------- | ------------------- | ----------- |
| Solar -> Load   | Policy 1            | `$0.05/kWh` |
| Battery -> Load | Policy 1 + Policy 2 | `$0.08/kWh` |

Battery and solar receive different VLANs because their signatures differ.
Each VLAN gets all applicable pricing segments.

### Group constraints

Policies that target source groups constrain the sum of those source VLANs.
Policies that target one source constrain one VLAN.
Both kinds can coexist.

```
Policy 1: Battery+Solar -> Load: limit 5 kW
Policy 2: Battery -> Load: limit 2 kW
```

| Constraint | Tags                        | Limit     |
| ---------- | --------------------------- | --------- |
| Group      | `VLAN_solar + VLAN_battery` | `<= 5 kW` |
| Individual | `VLAN_battery`              | `<= 2 kW` |

Result: Solar can draw up to 5 kW, Battery up to 2 kW, combined maximum 5 kW.
This uses multi-tag scoping: `power_limit(tags={1,2}, max=5kW)` constrains the sum of VLANs 1 and 2.

## Compilation pipeline

The compiler transforms policy definitions into model-layer constructs.

```mermaid
graph TD
    A[User policy configs] --> B[Flow enumeration]
    B --> C[Signature computation]
    C --> D[VLAN assignment]
    D --> E[Reachability analysis]
    E --> F[Connection tagging]
    F --> G[Node outbound tags]
    G --> H[Node inbound tags]
    H --> I[Pricing injection]
    I --> J[Model elements]
```

### Step 1: Flow enumeration

Each policy expands to concrete source-destination tuples.

- `Grid -> Load: $0.05` becomes `{(Grid, Load, 0.05)}`.
- `* -> Load: $0.05` becomes all sources paired with `Load`.
- `Grid -> *: $0.05` becomes all destinations paired with `Grid`.

### Step 2: Policy signature computation

For each source node, compute a policy signature.
A signature is the set of `(destination, price_st, price_ts)` tuples matched for that source.

$$
\text{sig}(s) = \{(d, \pi_{st}, \pi_{ts}) \mid \text{policy}(s \to d, \pi_{st}, \pi_{ts})\}
$$

### Step 3: VLAN assignment

Sources with identical signatures share one VLAN.
Sources with different signatures must use different VLANs — at least one policy treats them differently, so the optimizer must be able to distinguish them.
The resulting VLAN count is the provably minimum: the number of distinct non-empty signatures, plus tag 0.

Nodes with empty signatures use tag 0.
When no policies exist at all, only tag 0 exists — identical to standard HAEO.

### Step 4: Reachability analysis

For each VLAN, compute which connections can carry it using directed reachability.

1. Identify source nodes assigned to that VLAN.
2. Compute forward reachability from those sources (following connection direction) and backward reachability from *all* sink nodes (reverse direction).
    Forward traversal *absorbs* at sink nodes: a sink is included in the reachable set but expansion does not continue out of it. The VLAN's own sources are exempt so storage elements can still expand their own VLAN forward.
3. Assign VLAN variables only to connections whose endpoints both appear in the intersection of forward and backward reachable sets.

This avoids creating variables on impossible routes, while also ensuring a tagged source has a direct path to every sink it could physically serve.
A policy restricts where tagged flow is *priced* (Step 8), not where it may physically terminate: narrowing the subgraph to policy destinations alone would force solar to detour through storage whenever a Solar→Grid policy exhausted grid capacity, because Load would refuse the Solar tag.
That shows up as spurious simultaneous charge and discharge — power "laundered" through the battery to shed its provenance.
Sink absorption closes a related hole: without it, a VLAN that reached a battery would also propagate onto the battery's outbound edge, letting foreign tags leave storage without paying costs that were priced on the battery's own VLAN — the phantom charge/discharge arbitrage that appears when a negative-priced charge incentive is paired with tag-scoped wear.
Reachability also excludes edges whose *target* is one of the VLAN's own sources: a VLAN cannot re-enter its origin, which breaks the zero-cost self-loop `Battery:discharge → Inverter → Battery:charge → Battery` that would otherwise let solar (or any other incoming VLAN) pay only for the round-trip efficiency loss while the wear cost on the outbound cut is never crossed.
For tree topologies, which cover most home energy systems, paths between any two nodes are unique and the computation is linear in the node count.

### Step 5: Connection tagging

Each connection receives all VLANs that can traverse it.
Interior connections (trunks) can carry many VLANs.
Endpoint connections carry only the VLANs their node produces or consumes.

### Step 6: Node outbound tags

Each source node gets `outbound_tags` constraining which tags it can produce on.
Policied sources produce only on their assigned VLAN.
Unpolicied source-capable nodes produce only on tag 0, preventing unnecessary production decomposition.

### Step 7: Node inbound tags

Sink nodes get `inbound_tags` listing which VLANs they can consume.
All sinks accept tag 0 (unpolicied power) plus all active policy VLANs.
This default-allow approach ensures both policied and unpolicied power can reach any sink.

Power can still pass through a non-sink node on any VLAN for routing.
Junction nodes (neither source nor sink) do not receive inbound tags.

### Step 8: Pricing injection

For each policy, compute a sink-side canonical minimum s-t cut on the per-VLAN subgraph and attach a scoped pricing segment to each connection in that cut.
The algorithm is Edmonds–Karp max-flow with unit edge capacities; the cut is recovered by reverse BFS from the super-sink in the residual graph.

Unit capacities and the sink-side choice jointly guarantee that every source-to-destination path on the VLAN crosses exactly one cut edge, so a unit of tagged flow pays the policy price exactly once — no stacking from overlapping sub-cuts, and no flows that bypass pricing.
Minimum cardinality also means pricing is attached to the fewest connections, which matters for power-limit policies: the limit collapses to a single $\sum_{e \in \text{cut}} P^{tag}_{e,t} \le X$ constraint.

The cut naturally collapses to intuitive placements:

- Target-inbound edges for a specific destination (e.g. `Grid → Load` prices the `SW → Load` connection).
- Source-outbound edges for a single-outbound source targeting a wildcard (e.g. `Battery → *` prices the single `Battery → Inverter` connection).
- A shared bottleneck when many sources and many destinations converge through a narrower middle (e.g. an inverter separating `Solar|Battery` from `Load|Grid`).

Each injected segment's `tag` matches the source VLAN, and `price_source_target` and `price_target_source` map from the policy's directional prices.

## Mathematical formulation

### Per-tag power variables

Each segment creates non-negative variables per tag and period.

$$
P^{st}_{v,t} \geq 0 \quad \forall v \in \text{Tags}(c), \; t \in \{0, \ldots, T-1\}
$$

### Total power in segment constraints

Segment constraints operate on aggregate directional power.

$$
P^{st}_t = \sum_{v \in \text{Tags}(c)} P^{st}_{v,t}
$$

### Per-tag node balance

Node balance applies independently for each tag.

- Junction nodes: $\sum_c P^{tag}_{c,t} = 0$ for each tag (routing).
- Source nodes: only the source's own tag can have net outflow.
- Sink nodes: only tags in the node's `inbound_tags` set can have net inflow.

### Policy pricing term

For policy `(source_vlan, destination, price)`, the policy cost contribution is:

$$
C_{\text{policy}} = \sum_{e \in \text{cut}} \sum_t P^{st}_{v,e,t} \cdot \pi \cdot \Delta t_t
$$

The sum runs over the sink-side canonical minimum cut separating source from destination on the VLAN subgraph (see Step 8).
Unit capacities guarantee each source-to-destination path crosses exactly one cut edge, so the term assesses the policy price on each unit of tagged flow exactly once.

## Variable count analysis

| Scenario                          | VLANs | Connections with VLAN | Variable form                             |
| --------------------------------- | ----- | --------------------- | ----------------------------------------- |
| No policies                       | 1     | all x 1               | $C \times S \times 2 \times T$            |
| One policy (`Grid -> Load`)       | 2     | partial x 2           | $< C \times 2 \times S \times 2 \times T$ |
| All sources same policy signature | 2     | often broad           | $C \times 2 \times S \times 2 \times T$   |
| All sources distinct signatures   | $N+1$ | varies by route       | $\sum_c K_c \times S \times 2 \times T$   |

`C` is connection count, `S` is segments per connection, `T` is period count, and `K_c` is VLAN count on connection `c`.
Signature merging and reachability pruning reduce variable growth compared with naive one-tag-per-source assignment.

## Examples

### Grid surcharge

```
System: Grid <-> Switchboard <-> Load, Solar -> Switchboard
Policy: Grid -> Load: $0.05/kWh
```

Compilation summary:

1. Flows: `{(Grid, Load, 0.05)}`.
2. Signatures: Grid has `{(Load, 0.05)}`, others have empty signatures.
3. VLANs: Grid gets VLAN 1, others stay on tag 0.
4. Reachability: VLAN 1 appears on the directed path from Grid to every sink it can reach (here just Load).
5. Outbound tags: Grid produces on VLAN 1, Solar produces on tag 0.
6. Inbound tags: Load accepts tag 0 and VLAN 1.
7. Pricing: the min-cut separating Grid from Load collapses to the `SW → Load` inbound edge, which gets `pricing(tag=grid_vlan, $0.05)`.

Result:
Grid power carries the surcharge to `Load`.
Solar power flows freely on tag 0 at zero policy cost and is preferred when cheaper.

### Selective pricing

```
System: Grid <-> Switchboard <-> Load, Solar -> Switchboard, Battery <-> Switchboard
Policy: Battery -> *: $0.02/kWh
```

Battery gets a VLAN with a discharge wear cost.
Solar and Grid stay on tag 0 (no policy targets them) at zero cost.
All sink destinations accept tag 0 and Battery's VLAN, so Solar and Grid power reaches them freely.
The wildcard destination expands to every sink reachable from Battery, and the min-cut collapses to the single `Battery → Switchboard` outbound edge — one segment carries the `$0.02/kWh` wear cost regardless of which sink ultimately consumes the power.

## Implementation location

The compilation pipeline runs in `custom_components/haeo/core/adapters/policy_compilation.py`.
It executes as a post-processing step in `collect_model_elements()` after adapter element configs are assembled.
The model layer remains policy-unaware and operates only on tags and scoped segments.

## External and internal pricing

HAEO separates external market pricing from internal valuation policies.

**External pricing** represents real market costs or credits — what you actually pay or earn.
These belong on the element that interfaces with the external system:

- Grid import and export prices from your energy retailer.
- Feed-in tariff rates.

External prices are configured on pricing segments and driven by sensor data.
They are not policies.

**Internal policies** are valuations you choose to apply to guide the optimizer, without representing real money changing hands:

- Battery discharge wear cost (`$0.02/kWh`).
- Battery charge incentive (`-$0.001/kWh`).
- Source-destination routing penalties.

These should be configured as power policies so the cost structure is explicit: "Battery to anything costs `$0.02/kWh` because of wear."

!!! note "Migration path"

    Battery flat pricing fields (`price_source_target`, `price_target_source`) can map to policies.
    Battery discharge cost can become `Battery -> *: $0.02/kWh`.
    Battery charge incentive can become `* -> Battery: -$0.001/kWh`.
    SOC-dependent valuation still requires state-dependent modeling rather than flat per-kWh policies.

## Future work: SOC-based VLANs

Battery SOC partitions could be modeled as separate VLANs so different SOC regions carry different tags.
That approach could enable SOC-dependent valuation through the same policy machinery.
This remains an open modeling topic.

## Next Steps

<div class="grid cards" markdown>

- :material-cog-play:{ .lg .middle } **Policy walkthrough**

    ---

    Configure policy rules end to end in Home Assistant.

    [:material-arrow-right: Power policies walkthrough](../walkthroughs/power-policies.md)

- :material-wrench:{ .lg .middle } **Compilation internals**

    ---

    Review implementation details and compiler behavior.

    [:material-arrow-right: Policy compilation](../developer-guide/policy-compilation.md)

- :material-network:{ .lg .middle } **VLAN optimization**

    ---

    Dive into signature merging and tag minimization rationale.

    [:material-arrow-right: VLAN optimization](../developer-guide/vlan-optimization.md)

</div>
