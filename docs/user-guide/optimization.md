# Understanding Optimization Results

This guide explains how to interpret HAEO's optimization results and use them effectively.

## Optimization Sensors

HAEO creates three main network sensors:

### Optimization Cost

**Entity ID**: `sensor.{network_name}_optimization_cost`

Total cost over the optimization horizon in dollars.

- **Lower is better**: HAEO minimizes this value
- **Includes**: Grid import/export costs, virtual incentive costs for battery/solar usage, connection transfer costs
- **Unit**: \$ (or your configured currency)

!!! info "Virtual Costs"

    The optimization cost includes small virtual costs to guide decision-making:

    - Battery discharge: Encourages using stored energy at optimal times
    - Solar generation: Encourages self-consumption over export when economically similar
    - Undercharge/overcharge: Penalty costs for operating outside normal SOC range

    These virtual costs ensure stable optimization behavior but don't represent actual utility charges.
    Your real electricity bill depends primarily on grid import/export and your configured prices.

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
If this value climbs higher than you expect, adjust the interval tiers, simplify the network, or try another solver.
Review the [interval tier guidance](configuration.md#interval-tiers) before changing that value.

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

- **Nodes**: `sensor.{node_name}_shadow_price_node_balance` reports the local spot price for energy at each node.
- **Batteries**: `sensor.{battery_name}_shadow_price_energy_balance`, `sensor.{battery_name}_shadow_price_soc_min`, `sensor.{battery_name}_shadow_price_soc_max`, `sensor.{battery_name}_shadow_price_power_consumption_max`, and `sensor.{battery_name}_shadow_price_power_production_max` quantify the value of stored energy, SOC bounds, and charge/discharge headroom.
- **Grid**: `sensor.{grid_name}_shadow_price_power_import_max` and `sensor.{grid_name}_shadow_price_power_export_max` indicate when import or export limits restrict the optimization.
- **Other controllable elements**: `sensor.{entity_name}_shadow_price_power_consumption_max` and `sensor.{entity_name}_shadow_price_power_production_max` appear for any device that enforces variable power caps.
- **Connections**: `sensor.{connection_name}_shadow_price_power_flow_min` and `sensor.{connection_name}_shadow_price_power_flow_max` tell you when minimum or maximum flow limits block energy transfers between elements.
- **Solar**: `sensor.{pv_name}_shadow_price_forecast_limit` shows when extra solar output would reduce total cost.

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
        entity_id: sensor.main_battery_power_consumed
    condition:
      - condition: template
        value_template: "{{ states('sensor.main_battery_power_consumed') | float >
          0 }}"
    action:
      - service: battery.set_charge_power
        data:
          power: "{{ states('sensor.main_battery_power_consumed') | float }}"

  - alias: Follow HAEO Battery Discharge Schedule
    trigger:
      - platform: state
        entity_id: sensor.main_battery_power_produced
    condition:
      - condition: template
        value_template: "{{ states('sensor.main_battery_power_produced') | float >
          0 }}"
    action:
      - service: battery.set_discharge_power
        data:
          power: "{{ states('sensor.main_battery_power_produced') | float }}"
```

**Note**: Battery elements create separate sensors for charging (`power_consumed`) and discharging (`power_produced`).
See the [battery documentation](elements/battery.md) for complete details.

## Performance Considerations

### Optimization Duration

Monitor the optimization duration sensor to keep solve times reasonable (typically under 10 seconds).

If optimization takes too long:

1. **Adjust interval tiers**: Reduce tier 4 count or increase tier durations for faster solving (see [interval tier guidance](configuration.md#interval-tiers))
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

    [:material-arrow-right: Sigenergy example](examples/sigenergy-system.md)

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
