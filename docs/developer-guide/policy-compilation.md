# Policy compilation

This guide explains how user-configured power policies compile into the LP model.
See [Power policies](../modeling/tagged-power.md) for the design rationale.
See [VLAN optimization](vlan-optimization.md) for variable minimization algorithms.

## Overview

Policies are a device-layer concept.
Users configure source-destination pairs with prices and limits.
The compilation pipeline transforms those rules into model-layer constructs.
Those constructs include optimized VLAN assignments, connection tagging, node access lists, and scoped segments.

## Pipeline

```mermaid
graph TD
    A[Policy configs] --> B[Flow enumeration]
    B --> C[Signature computation]
    C --> D[VLAN assignment]
    D --> E[Reachability analysis]
    E --> F[Connection tagging]
    F --> G[Node source tags]
    G --> H[Node access lists]
    H --> I[Pricing injection]
    I --> J[Model elements]
```

### Step 1: Flow enumeration

Each policy expands into concrete `(source, destination, price_st, price_ts)` tuples.
Wildcards (`*`) expand to all nodes.

### Step 2: Signature computation

For each source node, collect the set of `(destination, price)` tuples from all matching policies.
This set is the node's **policy signature**.

### Step 3: VLAN assignment

Group sources by identical signature.
Assign one VLAN per group.
This yields the minimum VLAN count for correct policy behavior.

### Step 4: Reachability analysis

For each VLAN, find connections on paths from source nodes to destination nodes.
Only reachable connections receive variables for that VLAN.

### Step 5: Connection tagging

Apply reachability results so each connection gets the set of VLANs that can traverse it.

### Step 6: Node outbound tags

Set `outbound_tags` on each source node with an assigned VLAN.
The node's `element_power_balance` constraint enforces that only the outbound tags carry produced power.

### Step 7: Node inbound tags

Compute which VLANs each node can consume.

- A node can consume VLAN `v` if any policy has that node as a destination and the source matches VLAN `v`.

Power on non-consumable VLANs can still flow through the node for routing.
That power cannot terminate at the node.

### Step 8: Pricing injection

For each policy, add a scoped pricing segment at the destination connection.
The segment's `tag` matches the source VLAN.

## Architecture

### Where compilation runs

Compilation lives in `custom_components/haeo/core/adapters/policy_compilation.py`.
It runs as a post-processing step in `collect_model_elements()`.

### Adapter interaction

The policy adapter produces rule configs, not model elements.
`collect_model_elements()` extracts those rules and passes them to the compilation pipeline.
The pipeline updates other adapters' model element configs by adding connection tags, node `outbound_tags` values, and tag costs.

### Model layer isolation

The model layer is policy-unaware.
It operates on integer tags and scoped segments.
All policy semantics are resolved in the compilation layer.

## Example

```
Nodes: Grid, Solar, Battery, Switchboard, Load
Policies:
  Grid -> Load: $0.05/kWh
  Solar -> Load: $0.02/kWh
```

| Step             | Result                                                                  |
| ---------------- | ----------------------------------------------------------------------- |
| Flow enumeration | {(Grid,Load,0.05), (Solar,Load,0.02)}                                   |
| Signatures       | Grid={(Load,0.05)}, Solar={(Load,0.02)}, Battery={}, SW={}, Load={}     |
| VLANs            | Grid=1, Solar=2, others=0, K=3                                          |
| Reachability     | VLAN 1: Grid->SW, SW->Load. VLAN 2: Solar->SW, SW->Load                 |
| Connection tags  | Grid->SW: {0,1}, Solar->SW: {0,2}, SW->Load: {0,1,2}, Battery->SW: \{0} |
| Outbound tags    | Grid: outbound_tags={1}, Solar: outbound_tags={2}                      |
| Inbound tags     | Load consumes {1,2}, SW forwards all, Battery consumes \{0}             |
| Pricing          | SW->Load: pricing(tag=1,$0.05), pricing(tag=2,$0.02)                    |

Result: Solar power is preferred over grid power because it has lower policy cost.
Battery power without matching policy cannot reach `Load` because VLAN 0 is not in `Load`'s access list.
Battery can still consume non-policy power on VLAN 0.

## Testing

Tests live in `custom_components/haeo/core/adapters/tests/test_policy_compilation.py`.

- **Signature computation**: correct merging of identical signatures.
- **VLAN assignment**: minimum VLANs for various policy sets.
- **Reachability**: correct connection tagging for tree topologies.
- **Source enforcement**: `outbound_tags` set on correct nodes.
- **End-to-end**: full network optimization with policies produces correct costs.

## Related

- [Power policies](../modeling/tagged-power.md) for design and mathematical formulation.
- [VLAN optimization](vlan-optimization.md) for variable minimization algorithms.
- [Adapter layer](adapter-layer.md) for adapter architecture.
