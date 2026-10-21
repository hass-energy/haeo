# Policy pricing model

The PolicyPricing model element applies the price of a [power policy](../../tagged-power.md) to the power flows it governs.

## Overview

PolicyPricing is a flow reader.
It produces and consumes nothing and adds no variables or constraints.
It only adds a cost: one price multiplied by the power on a set of connection and tag pairs.

[Policy compilation](../../../developer-guide/policy-compilation.md) creates the elements.
Each policy rule gets one PolicyPricing element per source tag it prices.
Its terms are the connections on the minimum cut that separates the rule's sources from its destinations on that tag, so every tagged path from a source to a destination pays the price exactly once.
See [policy pricing](../../tagged-power.md#policy-pricing) in the power policies formulation for why the cut is used.

## Model formulation

### Decision variables

PolicyPricing creates no decision variables.
It reads the per-tag power variables of the [connections](../connections/connection.md) it prices.

### Parameters

| Parameter | Description                                   |
| --------- | --------------------------------------------- |
| `price`   | Price per kWh for each period (\$/kWh)        |
| `terms`   | Connection and tag pairs the price applies to |

`price` is a tracked parameter.
Changing it rebuilds only this element's cost, so a new policy price takes effect without rebuilding the network.

### Constraints

PolicyPricing adds no constraints.

### Cost contribution

$$
C = \sum_{(e, v) \in \text{terms}} \sum_t P_{e,v}(t) \cdot \pi(t) \cdot \Delta t
$$

where $P_{e,v}(t)$ is the power on tag $v$ at connection $e$'s measured point and $\pi(t)$ is the price.
The measured point is where the connection's power limit applies, so the policy price, the limit, and the reported power all refer to the same flow.
A connection without a power limit is measured where power enters it.

Several PolicyPricing elements can price the same connection and tag.
Their costs add up, which is how policies stack.

## Next steps

<div class="grid cards" markdown>

- :material-tag-multiple:{ .lg .middle } **Power policies formulation**

    ---

    Tagged power, per-tag balance, and pricing placement.

    [:material-arrow-right: Power policies](../../tagged-power.md)

- :material-cog-transfer:{ .lg .middle } **Policy compilation**

    ---

    How policy rules become tags and pricing elements.

    [:material-arrow-right: Policy compilation](../../../developer-guide/policy-compilation.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the policy pricing model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/policy_pricing.py)

</div>
