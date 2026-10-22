# Understanding optimization results

This guide explains how to interpret HAEO's optimization results and use them effectively.

## Optimization sensors

HAEO creates three main sensors on the **Optimizer** device:

### Cost

**Entity ID**: `sensor.optimizer_cost`

Total cost over the optimization horizon in dollars.

- **Lower is better**: HAEO minimizes this value
- **Includes**: Grid import/export costs, buffer shortfall costs, connection transfer costs
- **Unit**: \$ (or your configured currency)

!!! info "Lexicographic ordering"

    When multiple schedules share the same primary cost, HAEO applies a secondary time-preference objective.
    This ordering favors earlier energy transfers without changing the reported optimization cost.

### Status

**Entity ID**: `sensor.optimizer_status`

State of the latest optimization, as Home Assistant shows it, with the state value automations compare against:

- **Succeeded** (`success`): The latest optimization completed successfully
- **Failed** (`failed`): The latest optimization failed, for example because inputs are unavailable or the problem is infeasible
- **Pending** (`pending`): No optimization has finished since HAEO started

This sensor exists from the moment the hub loads and stays available when an optimization fails.
When the status is **Failed**, its `error` attribute holds the error message, and the other output sensors are unavailable until an optimization succeeds.
Its `last_run` attribute is the time the latest successful optimization finished.

Some failures, such as an input with no reading or a plan that cannot meet every constraint, raise their own repair issue under **Settings** → **System** → **Repairs** that names the cause.
If optimizations keep failing for any other reason for five minutes, HAEO raises an "Optimization failed" repair issue with the error message.
That issue clears on the next successful optimization.

### Duration

**Entity ID**: `sensor.optimizer_duration`

Time taken to solve the optimization in seconds.
If this value climbs higher than you expect, choose a shorter [planning horizon](configuration.md#planning-horizon) or simplify the network.

### Forecast horizon

**Entity ID**: `sensor.optimizer_forecast_horizon`

The period boundaries HAEO currently plans over.
Its state is the start of the current period, and its `forecast` attribute lists the time of every period boundary in the horizon.
It also reports `period_count`, the number of periods, and `smallest_period_seconds`, the length of the shortest period.

Another hub can use this sensor as its [forecast sensor horizon](configuration.md#planning-horizon) to plan on the same periods.

### Auto optimize

**Entity ID**: `switch.optimizer_auto_optimize`

Turns automatic optimization on or off.
It is on by default and keeps its state across restarts.

While it is off, HAEO stops advancing the horizon and does not optimize when inputs change.
Run an optimization yourself with the `haeo.optimize` action, for example from an automation.
Turning it back on resumes automatic optimization.

## Element sensors

Each configured element creates optimization result sensors.
The specific sensors depend on the element type—see each element's documentation for complete details on their outputs.

### Sensor structure

All HAEO sensors follow a consistent structure:

**Current state**: For most sensors, the state shows the optimal value for the current period.
Sensors that summarize the plan, such as a grid's import cost or a load's horizon and next 24 hours totals, show the total instead.
Each element's page says which of its sensors are totals.

**Forecast attributes**: Each sensor includes a `forecast` attribute containing future timestamped values across your optimization horizon.

## Shadow price sensors

Shadow price sensors publish the marginal value of key constraints over the optimization horizon.
They translate physical limits into dollar-per-kilowatt-hour signals that explain the optimizer's dispatch choices.

Available sensors include:

Their names end in "shadow price", so their entity IDs end in `_shadow_price`.
For example, `sensor.{name}_power_balance_shadow_price` reports the local price of energy where power meets, and `sensor.{name}_max_import_power_shadow_price` on a grid shows when its import limit restricts the plan.
Each element's page lists the shadow prices it creates.

All shadow-price sensors are reported in `$/kWh` so they sit on the same axis as tariffs and other energy-priced quantities.

Each shadow price sensor mirrors the standard forecast attribute layout so you can inspect future periods in dashboards and automations.
Review [Shadow Prices](../modeling/shadow-prices.md) for detailed interpretation guidance.

### Understanding forecast attributes

All sensors include forecast attributes with future values:

```yaml
attributes:
  forecast:
    - time: '2025-10-11T12:00:00+00:00'
      value: 1.23
    - time: '2025-10-11T12:05:00+00:00'
      value: 1.17
    - time: '2025-10-11T12:10:00+00:00'
      value: 1.34
    # ... more timestamped values
```

Use these in automations or dashboards to visualize the optimal schedule.

## Using results in automations

### Example: Control battery based on optimization

```yaml
automation:
  - alias: Follow HAEO Battery Charge Schedule
    trigger:
      - platform: state
        entity_id: sensor.main_battery_charge_power
    condition:
      - condition: template
        value_template: "{{ states('sensor.main_battery_charge_power') | float > 0
          }}"
    action:
      - service: battery.set_charge_power
        data:
          power: "{{ states('sensor.main_battery_charge_power') | float }}"

  - alias: Follow HAEO Battery Discharge Schedule
    trigger:
      - platform: state
        entity_id: sensor.main_battery_discharge_power
    condition:
      - condition: template
        value_template: "{{ states('sensor.main_battery_discharge_power') | float
          > 0 }}"
    action:
      - service: battery.set_discharge_power
        data:
          power: "{{ states('sensor.main_battery_discharge_power') | float }}"
```

**Note**: Battery elements create separate sensors for charging (`sensor.{name}_charge_power`) and discharging (`sensor.{name}_discharge_power`).
See the [battery documentation](elements/battery.md) for complete details.

## Performance considerations

### Optimization duration

Monitor the optimization duration sensor to keep solve times reasonable (typically under 10 seconds).

If optimization takes too long:

1. **Shorten the horizon**: Choose a shorter [planning horizon](configuration.md#planning-horizon) preset, or a forecast sensor with fewer periods
2. **Simplify network**: Remove unnecessary elements or connections
3. **Check configuration**: Verify all sensors are available and providing valid data

### Update frequency

HAEO re-optimizes periodically. Balance:

- **More frequent**: Better response to changes, higher CPU usage
- **Less frequent**: Lower CPU usage, may miss price changes

## Interpreting cost

The optimization cost represents the total forecasted cost over the full horizon, not just the immediate step.
Track changes in this value when you adjust configuration parameters to confirm the optimiser is producing the expected behaviour.

## Next steps

Explore these guides to act on the optimization outputs.

<div class="grid cards" markdown>

- :material-play-circle-outline:{ .lg .middle } **Review a complete example**

    ---

    See how the optimization outputs drive real-world decisions.

    [:material-arrow-right: Sigenergy walkthrough](../walkthroughs/sigenergy-system.md)

- :material-robot-outline:{ .lg .middle } **Build automations from the results**

    ---

    Turn recommended power schedules into actionable automations.

    [:material-arrow-right: Automation patterns](automations.md)

- :material-sync:{ .lg .middle } **Monitor data updates**

    ---

    Understand how new sensor data triggers optimizations.

    [:material-arrow-right: Data update guide](data-updates.md)

- :material-math-integral:{ .lg .middle } **Mathematical Modeling**

    ---

    Understand the optimization formulation.

    [:material-arrow-right: Modeling overview](../modeling/index.md)

- :material-help-circle:{ .lg .middle } **Troubleshooting**

    ---

    Common issues and solutions.

    [:material-arrow-right: Troubleshooting guide](troubleshooting.md)

</div>
