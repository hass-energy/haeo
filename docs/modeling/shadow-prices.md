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

## Energy-native constraint formulation

All HAEO shadow-price sensors are emitted in **\$/kWh** so they sit on the same axis as tariffs and other energy-priced quantities.
Rather than computing power-based duals and converting them after the fact, the LP layer expresses power-balance and power-limit constraints in energy units directly.
Each instantaneous power expression is multiplied by the period width `dt` before the constraint is added to the solver, so the corresponding dual variable is dimensionally \$/kWh from the moment HiGHS returns it.

For a period of width `dt[hours]`, the constraints take the form:

- Power balance: `(connections + production - consumption) * dt == 0`
- Power limits: `power * dt <= max_power * dt` (and symmetrically for the lower bound)

The primal solution is unchanged because `dt > 0` scales both sides of every constraint equally.
The dual variables, however, are now natively in \$/kWh and need no post-processing in the adapter layer.

Because HAEO supports variable-width intervals, `dt` is taken from `Element.periods` for each period.
Individual elements document their specific shadow prices, but the interpretation is uniform: the value shows the marginal benefit of relaxing that constraint, per kWh of slack.

All published sensors use the suffix `_shadow_energy_price` and emit \$/kWh.

### Worked example

For a 5-minute period (`dt = 1/12 h`), an LP-layer dual of `1.20` on the power-balance constraint reads directly as `\$1.20/kWh` at the corresponding node and time.
The equivalent power-unit dual would have been `1.20 * (1/12) = 0.10` \$/kW for that period, but HAEO no longer surfaces this intermediate form.

## Diagnostic visibility

Shadow-price sensors are tagged as `EntityCategory.DIAGNOSTIC`.
They are diagnostic indicators of solver behaviour, not setpoints to act on directly, so they are hidden by default in the Home Assistant UI.
Templates and dashboards that reference them by entity ID continue to work; users who want them on a default dashboard can unhide them per entity.

## Practical interpretation

**Sign convention**: Positive shadow prices indicate that loosening the constraint would reduce total cost.
Negative values suggest that tightening the constraint would help (less common in practice).

**Zero values**: A shadow price of zero means the constraint is not currently limiting the solution.
The optimizer has headroom, so relaxing the limit would not change its decisions.

**Non-zero values**: When a shadow price is non-zero, the constraint is binding.
The magnitude indicates how valuable additional capacity would be at that point.

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
