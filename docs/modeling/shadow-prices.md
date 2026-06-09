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

All HAEO shadow-price sensors are reported in **\$/kWh** so they sit on the same axis as tariffs and other energy-priced quantities.
The LP model formulates both power-balance and power-limit constraints in energy units (kWh) by multiplying by the period duration, so the solver produces \$/kWh duals natively.
Individual elements document their specific shadow prices, but the interpretation is uniform: the value shows the marginal benefit of relaxing that constraint, per kWh of slack.

## Diagnostic visibility

Shadow-price sensors are tagged as `EntityCategory.DIAGNOSTIC`.
They are diagnostic indicators of solver behavior, not setpoints to act on directly, so they are hidden by default in the Home Assistant UI.
Templates and dashboards that reference them by entity ID continue to work; users who want them on a default dashboard can unhide them per entity.

## Practical interpretation

**Sign convention**: Positive shadow prices indicate that loosening the constraint would reduce total cost.
Negative values suggest that tightening the constraint would help (less common in practice).

**Zero values**: A shadow price of zero means the constraint is not currently limiting the solution.
The optimizer has headroom, so relaxing the limit would not change its decisions.

**Non-zero values**: When a shadow price is non-zero, the constraint is binding.
The magnitude indicates how valuable additional capacity would be at that point.

## Ranging

Every shadow-price sensor also carries ranging metadata: `range_up` and `range_dn`.
These values come from LP sensitivity analysis (HiGHS `getRanging()`) and describe how far a constraint's right-hand side can move before its shadow price changes.

For an energy-balance constraint, `range_up` is the headroom (in kWh) by which the balance can increase before the marginal price at that timestep changes; `range_dn` is the corresponding headroom on the decrease side.
A positive `range_up` means the current shadow price still applies if the balance shifts upward by that amount; once the headroom is exhausted, the dual may change.

Ranging is computed once per solve at the end of `Network.optimize()`, not lazily when a sensor is read.
Output extraction only slices the cached ranging arrays.
This is deliberate: ranging cost is part of the measured solve, and the results feed multi-tag marginal pricing and future intent-signal analysis.

Computing ranging is a substantial share of post-solve work and is kept always-on because it powers marginal dual selection for multi-tagged elements.
Every shadow-price sensor exposes `range_up` and `range_dn` as diagnostic fields alongside the dual values.

## Per-tag balance shadow prices

When an element's connections carry more than one VLAN tag, the per-tag energy-balance constraint produces one block of shadow-price values per tag — one balance dual per tag per period.
See [Power policies](tagged-power.md) for the tag formulation.

Home Assistant exposes these duals in two ways:

### Collapsed primary sensor

Sensors such as `node_power_balance` and `battery_power_balance` collapse the per-tag dual blocks into a single series aligned with the element forecast.
At each timestep, the marginal-selection rule chooses the cheapest tag dual among tags that still have ranging headroom (`range_up > 0`); if every tag is saturated, the most expensive (maximum) dual is used.
Elements with only one tag pass their dual through unchanged.

### Per-tag diagnostic sensors

When more than one tag is present, HAEO also emits advanced per-tag diagnostic sensors: `{prefix}_tag_{N}_power_balance`, where `{prefix}` is one of `node`, `battery`, `battery_section`, or `inverter_dc_bus`, and `{N}` is the VLAN tag id.
These sensors expose each tag's full per-period dual series and ranging metadata.
They are disabled by default.

## Next steps

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
