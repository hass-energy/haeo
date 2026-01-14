# Shadow Prices

Shadow prices are dual values from the linear programming optimization.
They quantify how much the total objective would improve if a constraint were relaxed by one unit.
In HAEO, shadow prices help explain why the optimizer makes certain decisions and highlight where additional flexibility creates the most value.

## What shadow prices tell you

Every constraint in the optimization problem has an associated shadow price.
This value represents the marginal benefit of loosening that constraint—essentially answering the question: "How much would I save if I could push this limit by one more unit?"

A key distinction: shadow prices show what you would pay for *additional* capacity, not what you are paying for resources already allocated.
When a constraint is not limiting the solution (slack), its shadow price is zero.
When a constraint is actively restricting the optimizer (binding), the shadow price becomes non-zero.

## Example: Marginal cost of power

The node balance constraint ensures that power flowing into a node equals power flowing out.
Its shadow price represents the marginal cost of power at that location and time.

This is not the price you pay for power currently consumed.
It is the price you would pay to increase (or save by decreasing) consumption by one kilowatt at that node in that time step.

When grid prices are high, the node balance shadow price rises because additional consumption would require expensive imports.
When local generation exceeds demand, the shadow price may drop to zero or become negative, indicating that additional consumption would actually help by absorbing surplus.

## Example: Solar forecast limit

The solar forecast limit constrains solar output to the predicted generation.
Its shadow price reveals when this physical limit is restricting the optimizer.

During midday when prices are negative, curtailment may already be occurring.
The optimizer cannot use all available solar, so more generation would not help.
The shadow price is zero because the constraint is slack—the limit is not what's holding the system back.

At night, the situation reverses.
The forecast limit binds at zero (no sun), but the optimizer would clearly benefit from more solar output to avoid expensive imports or to charge the battery.
The shadow price rises, signaling: "More solar power here would reduce total cost."
This is physically impossible, of course, but the shadow price makes the optimizer's preference visible.

This pattern—zero when slack, non-zero when binding—applies to all shadow prices and makes them useful for identifying system bottlenecks.

## Categories of shadow prices

HAEO exposes shadow prices for various constraint types:

- **Energy-coupled constraints** (reported in \$/kWh): These involve stored energy over time, such as battery state-of-charge limits or energy balance between periods.
- **Instantaneous power constraints** (reported in \$/kW): These limit power flow at a single moment, such as inverter capacity, grid import limits, or connection ratings.

Individual elements document their specific shadow prices.
The interpretation pattern remains consistent: the value shows the marginal benefit of relaxing that particular constraint.

## Practical interpretation

**Sign convention**: Positive shadow prices indicate that loosening the constraint would reduce total cost.
Negative values suggest that tightening the constraint would help (less common in practice).

**Zero values**: A shadow price of zero means the constraint is not currently limiting the solution.
The optimizer has headroom, so relaxing the limit would not change its decisions.

**Non-zero values**: When a shadow price is non-zero, the constraint is binding.
The magnitude indicates how valuable additional capacity would be at that point.

## Control limit recommendations

HAEO synthesizes shadow prices with optimal power flows to produce **control limit recommendation** sensors.
These sensors provide a single kW value that can be directly applied to hardware limits.

The synthesis combines three inputs:

1. **Optimal power value**: The power the optimizer wants to flow
2. **Constraint shadow price**: Whether the limit is binding
3. **Configured limit**: The maximum capacity you specified

### Synthesis logic

| Optimal Power | Shadow Price | Recommendation |
|---------------|--------------|----------------|
| 0 | (any) | 0 kW |
| > 0 | 0 | Configured limit |
| > 0 | > 0 | Optimal power value |

**Interpretation**:

- **Zero power**: The optimizer doesn't want flow in this direction. Recommend blocking it (0 kW limit).
- **Positive power, zero shadow price**: Flow is desired and headroom exists. Recommend maximum capacity.
- **Positive power, non-zero shadow price**: The constraint is binding. Recommend the exact optimal rate.

### Why this works

The key insight is that **lower bounds (≥ 0) don't need separate shadow prices** for automation purposes.
When power is zero, the optimizer has decided not to use that flow direction—the reason (no value, or constraint) doesn't matter for control.
When power is positive, the upper-bound shadow price tells you whether the limit is binding.

This avoids exposing the mathematically correct but practically redundant "reduced costs" on non-negativity constraints.
The recommendation sensors provide everything needed for hardware control.

### Available sensors

| Sensor | Description |
|--------|-------------|
| `sensor.{battery}_charge_limit_recommendation` | Battery charging limit |
| `sensor.{battery}_discharge_limit_recommendation` | Battery discharging limit |
| `sensor.{inverter}_charge_limit_recommendation` | Inverter AC→DC limit |
| `sensor.{inverter}_discharge_limit_recommendation` | Inverter DC→AC limit |
| `sensor.{grid}_import_limit_recommendation` | Grid import limit (when configured) |
| `sensor.{grid}_export_limit_recommendation` | Grid export limit (when configured) |

See [Automation Examples](../user-guide/automations.md) for how to use these sensors.

## Next Steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery modeling**

    ---

    Understand how battery constraints generate shadow prices for state-of-charge and energy balance.

    [:material-arrow-right: Battery model](model-layer/elements/battery.md)

- :material-transmission-tower:{ .lg .middle } **Grid modeling**

    ---

    See how import and export limits affect shadow prices at the grid connection.

    [:material-arrow-right: Grid model](device-layer/grid.md)

- :material-network:{ .lg .middle } **Network overview**

    ---

    Learn how node balance constraints produce marginal energy prices across the network.

    [:material-arrow-right: Network overview](index.md)

</div>
