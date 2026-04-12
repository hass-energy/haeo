# Segments

Segments are the building blocks that define connection behavior.
Each connection composes an ordered segment chain to apply limits, efficiency losses, pricing, or internal balancing.

## Composing connections

Segments are **functional transforms** on power flow expressions.
The Connection creates LP variables for `power_in` and passes them through its segment chain.

Each segment receives a `power_in` expression at construction time and exposes a `power_out` expression.
Most segments are **identity transforms** — they return the input unchanged and add constraints or costs as side effects:

- **Identity segments**: `power_out = power_in`, add constraint/cost.
- **Transform segments**: `power_out = power_in * factor` (e.g., efficiency).
- **Auxiliary segments**: `power_out = power_in`, create auxiliary LP variables for penalties.

This design means:

- Segments do not create power flow LP variables.
- Variable count = connection flow decisions (T) + auxiliary variables only.
- Segments are composable and order-independent for identity transforms.

## Segment types

- **[SOC pricing segment](soc-pricing.md)** for battery SOC penalty costs.
- **[Efficiency segment](efficiency.md)** for loss modeling.
- **[Power limit segment](power-limit.md)** for power limits.
- **[Pricing segment](pricing.md)** for transfer costs and fees.
- **[Passthrough segment](passthrough.md)** for lossless flow with no constraints or cost.

## Next steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connection model**

    ---

    Segment-based connection formulation.

    [:material-arrow-right: Connection formulation](../connections/connection.md)

- :material-battery-charging:{ .lg .middle } **Elements**

    ---

    Battery and Node model elements.

    [:material-arrow-right: Element types](../elements/index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View segment source code.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/tree/main/custom_components/haeo/core/model/elements/segments)

</div>
