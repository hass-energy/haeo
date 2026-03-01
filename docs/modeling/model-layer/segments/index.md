# Segments

Segments are the building blocks that define connection behavior.
Each connection composes an ordered segment chain to apply limits, efficiency losses, pricing, or internal balancing.

## Composing connections

Connection composition follows a few rules:

- Segments are provided as an ordered mapping in the connection configuration.
- Mapping keys become segment names and appear under the `segments` output.
- If no segments are provided, a passthrough segment is created automatically.
- Adjacent segments are linked by equality constraints on their in/out flows.
- Segments receive references to the source and target elements for context.

This pattern keeps the connection model simple while making behavior explicit and reusable.

## Segment types

- **[SOC pricing segment](soc-pricing.md)** for battery SOC penalty costs.
- **[Efficiency segment](efficiency.md)** for direction-specific loss modeling.
- **[Power limit segment](power-limit.md)** for directional limits and time-slice coupling.
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
