# Shadow Prices

Shadow prices are the dual values associated with linear constraints in the optimization model.
They quantify how much the total objective would change if the constraint were relaxed by one additional unit.
In HAEO, shadow prices help explain why the optimizer schedules certain energy flows and highlight where additional flexibility creates the most value.

## Available shadow prices

HAEO publishes shadow prices for multiple constraint groups.
Energy-coupled constraints report values in $/kWh, while instantaneous power limits use $/kW.
Positive values indicate that relaxing the constraint would reduce the total cost, while negative values show that tightening the constraint would be beneficial.

### Node balance (`shadow_price_node_balance`)

- Meaning: marginal cost of supplying one more kilowatt-hour at a node and time step.
- Interpretation: local spot price for energy at the node.
- Typical behaviour: usually mirrors the cheapest available supply route; spikes when the grid price is high or supply is scarce.
- Use cases: demand response weighting, virtual pricing signals, settlement benchmarking.

### Battery energy balance (`shadow_price_energy_balance`)

- Meaning: time-coupled value of stored energy between consecutive periods.
- Interpretation: how much future value the battery preserves by retaining one more kilowatt-hour right now.
- Typical behaviour: higher before expensive import periods, lower when surplus renewable energy is forecast.
- Use cases: validating charge and discharge schedules, estimating opportunity cost of deploying stored energy early.

### Battery state-of-charge bounds (`shadow_price_soc_min` and `shadow_price_soc_max`)

- Meaning: value of relaxing the minimum or maximum state-of-charge constraints.
- Interpretation: how much the objective would improve if the battery could discharge deeper or charge beyond the current limit.
- Typical behaviour: becomes non-zero only when the SOC bound is binding; zero when there is slack.
- Use cases: tuning SOC limits, assessing whether capacity upgrades would yield benefits.

### Power limits (`shadow_price_power_consumption_max`, `shadow_price_power_production_max`, `shadow_price_power_import_max`, `shadow_price_power_export_max`, `shadow_price_power_flow_min`, `shadow_price_power_flow_max`)

- Meaning: marginal benefit of increasing the instantaneous power cap on a device or grid tie.
- Interpretation: price signal showing when additional charger, inverter, import, or export headroom would lower total cost.
- Typical behaviour: activates during peak charge/discharge or when grid limits prevent the optimizer from following price incentives.
- Use cases: sizing inverters and breakers, negotiating demand or export limits, prioritising flexible loads when multiple devices compete for the same headroom.
- Connection limits (`shadow_price_power_flow_min` and `shadow_price_power_flow_max`) highlight when line ratings or contract minimums prevent energy from flowing between elements.

### Photovoltaic forecast limit (`shadow_price_forecast_limit`)

- Meaning: worth of an additional kilowatt-hour of solar generation at a specific time step.
- Interpretation: price premium for more renewable energy relative to alternative supply.
- Typical behaviour: increases when the model would prefer more solar to avoid imports or fuel usage.
- Use cases: capacity planning, curtailment diagnostics, valuing forecast improvements.

## Technical notes

- Solver support: HiGHS (default) exposes dual values; other solvers must offer dual recovery for shadow prices to be non-zero.
- Complementary slackness: a binding constraint yields a non-zero shadow price, while a non-binding constraint yields exactly zero.
- Sign convention: positive prices mean that loosening the constraint reduces total cost; negative prices mean tighter enforcement would help.
- Diagnostics: all shadow price sensors expose time-indexed forecasts, matching the optimization horizon and allowing visual analysis.
