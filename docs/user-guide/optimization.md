# Understanding Optimization Results

This guide explains how to interpret HAEO's optimization results and use them effectively.

## Optimization Sensors

HAEO creates three main network sensors:

### Optimization Cost

**Entity ID**: `sensor.{network_name}_optimization_cost`

Total cost over the optimization horizon in dollars.

- **Lower is better**: HAEO minimizes this value
- **Includes**: Grid import/export costs, configured SOC pricing costs, connection transfer costs
- **Unit**: \$ (or your configured currency)

!!! info "Lexicographic ordering"

    When multiple schedules share the same primary cost, HAEO applies a secondary time-preference objective.
    This ordering favors earlier energy transfers without changing the reported optimization cost.

### Optimization Status

**Entity ID**: `sensor.{network_name}_optimization_status`

Current optimization state:

- `success`: Optimization completed successfully
- `failed`: Optimization failed (infeasible constraints, solver error, or timeout)
- `pending`: Optimization is currently running or has not started yet

When status is `failed`, check the Home Assistant logs for detailed error messages explaining the cause.

### Optimization Duration

**Entity ID**: `sensor.{network_name}_optimization_duration`

Time taken to solve the optimization in seconds.
If this value climbs higher than you expect, adjust the interval tiers or simplify the network.
Review the [custom tier guidance](configuration.md#custom-tiers) before changing that value.

## Element Sensors

Each configured element creates optimization result sensors.
The specific sensors depend on the element type—see each element's documentation for complete details on their outputs.

### Sensor Structure

All HAEO sensors follow a consistent structure:

**Current state**: The sensor's state shows the optimal value for the current time step.

**Forecast attributes**: Each sensor includes a `forecast` attribute containing future timestamped values across your optimization horizon.

## Shadow Price Sensors

Shadow price sensors publish the marginal value of key constraints over the optimization horizon.
They translate physical limits into dollar-per-kilowatt-hour signals that explain the optimizer's dispatch choices.

Available sensors include:

- **Nodes**: `sensor.{node_name}_power_balance` reports the local spot price for energy at each node.
- **Batteries**: `sensor.{battery_name}_power_balance`, `sensor.{battery_name}_soc_min`, `sensor.{battery_name}_soc_max`, `sensor.{battery_name}_energy_in_flow`, and `sensor.{battery_name}_energy_out_flow` quantify the value of stored energy, SOC bounds, and charge/discharge headroom.
- **Grid**: `sensor.{grid_name}_power_max_import_price` and `sensor.{grid_name}_power_max_export_price` indicate when import or export limits restrict the optimization.
- **Inverter**: `sensor.{inverter_name}_max_power_dc_to_ac_price` and `sensor.{inverter_name}_max_power_ac_to_dc_price` appear when the inverter's per-direction caps are binding.
- **Load**: `sensor.{load_name}_forecast_limit_price` exposes the marginal value of serving this load.
- **Solar**: `sensor.{pv_name}_forecast_limit` shows when extra solar output would reduce total cost.

All shadow-price sensors are reported in `$/kWh` so they sit on the same axis as tariffs and other energy-priced quantities.

Each shadow price sensor mirrors the standard forecast attribute layout so you can inspect future periods in dashboards and automations.
Review [Shadow Prices](../modeling/shadow-prices.md) for detailed interpretation guidance.

### Understanding Forecast Attributes

All sensors include forecast attributes with future values:

```yaml
attributes:
  forecast:
    '2025-10-11T12:00:00+00:00': 1.23
    '2025-10-11T12:05:00+00:00': 1.17
    '2025-10-11T12:10:00+00:00': 1.34
    # ... more timestamped values
```

Use these in automations or dashboards to visualize the optimal schedule.

## Using Results in Automations

### Example: Control Battery Based on Optimization

```yaml
automation:
  - alias: Follow HAEO Battery Charge Schedule
    trigger:
      - platform: state
        entity_id: sensor.main_battery_power_charge
    condition:
      - condition: template
        value_template: "{{ states('sensor.main_battery_power_charge') | float > 0
          }}"
    action:
      - service: battery.set_charge_power
        data:
          power: "{{ states('sensor.main_battery_power_charge') | float }}"

  - alias: Follow HAEO Battery Discharge Schedule
    trigger:
      - platform: state
        entity_id: sensor.main_battery_power_discharge
    condition:
      - condition: template
        value_template: "{{ states('sensor.main_battery_power_discharge') | float
          > 0 }}"
    action:
      - service: battery.set_discharge_power
        data:
          power: "{{ states('sensor.main_battery_power_discharge') | float }}"
```

**Note**: Battery elements create separate sensors for charging (`power_charge`) and discharging (`power_discharge`).
See the [battery documentation](elements/battery.md) for complete details.

## Performance Considerations

### Optimization Duration

Monitor the optimization duration sensor to keep solve times reasonable (typically under 10 seconds).

If optimization takes too long:

1. **Adjust interval tiers**: Reduce tier 4 count or increase tier durations for faster solving (see [custom tier guidance](configuration.md#custom-tiers))
2. **Increase tier durations**: Fewer time steps reduce problem size
3. **Simplify network**: Remove unnecessary elements or connections
4. **Check configuration**: Verify all sensors are available and providing valid data

### Update Frequency

HAEO re-optimizes periodically. Balance:

- **More frequent**: Better response to changes, higher CPU usage
- **Less frequent**: Lower CPU usage, may miss price changes

## Interpreting Cost

The optimization cost represents the total forecasted cost over the full horizon, not just the immediate step.
Track changes in this value when you adjust configuration parameters to confirm the optimiser is producing the expected behaviour.

## Next Steps

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
