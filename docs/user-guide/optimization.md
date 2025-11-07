# Understanding Optimization Results

This guide explains how to interpret HAEO's optimization results and use them effectively.

## Optimization Sensors

HAEO creates three main network sensors:

### Optimization Cost

**Entity ID**: `sensor.{network_name}_optimization_cost`

Total cost over the optimization horizon in dollars.

- **Lower is better**: HAEO minimizes this value
- **Includes**: Import costs, export revenue, storage costs
- **Unit**: \$ (or your configured currency)

!!! info "Artificial Costs"

    The optimization cost includes small artificial costs for battery discharge and solar generation.
    These encourage the optimizer to use stored energy and solar power effectively.
    The actual monetary cost to you is primarily the grid import/export prices.

### Optimization Status

**Entity ID**: `sensor.{network_name}_optimization_status`

Current optimization state:

- `optimal`: Solution found successfully
- `feasible`: Solution found but may not be optimal
- `infeasible`: No solution exists (check constraints)
- `unbounded`: Problem is unbounded (configuration error)
- `undefined`: Solver error

### Optimization Duration

**Entity ID**: `sensor.{network_name}_optimization_duration`

Time taken to solve the optimization in seconds.
If this value climbs higher than you expect, adjust the horizon or period length, simplify the network, or try another solver.
Review the [horizon guidance](configuration.md#horizon-hours) before changing that value.

## Element Sensors

For each configured element, HAEO creates sensors:

### Power Sensors

Current optimal power at this time step (kW).

- **Positive**: Producing/discharging/importing
- **Negative**: Consuming/charging/exporting

### Energy Sensors (Batteries)

Current energy level (kWh).

### SOC Sensors (Batteries)

Current state of charge (%).

## Forecast Attributes

All sensors include forecast attributes with future values:

```yaml
attributes:
  forecast:
    - datetime: '2025-10-11T12:00:00+00:00'
      value: 1.23
    - datetime: '2025-10-11T12:05:00+00:00'
      value: 1.17
    # ... more timestamped values
```

Use these in automations or dashboards to visualize the optimal schedule.

## Using Results in Automations

### Example: Control Battery Based on Optimization

```yaml
automation:
  - alias: Follow HAEO Battery Schedule
    trigger:
      - platform: state
        entity_id: sensor.main_battery_power
    action:
      - service: battery.set_power
        data:
          power: "{{ states('sensor.main_battery_power') | float }}"
```

## Performance Considerations

### Optimization duration

Monitor the optimization duration sensor to keep solve times comfortable.
Reduce the horizon, increase the period length, simplify the network, or try a different solver if it starts trending upward.
Follow the [horizon guidance](configuration.md#horizon-hours) whenever you adjust the planning window.

### Update Frequency

HAEO re-optimizes periodically. Balance:

- **More frequent**: Better response to changes, higher CPU usage
- **Less frequent**: Lower CPU usage, may miss price changes

## Interpreting Cost

The optimization cost represents the total forecasted cost over the full horizon, not just the immediate step.
Track changes in this value when you adjust configuration parameters to confirm the optimiser is producing the expected behaviour.

## Related Documentation

- [Troubleshooting](troubleshooting.md)
- [Mathematical Modeling](../modeling/index.md)

## Next Steps

Explore these guides to act on the optimization outputs.

<div class="grid cards" markdown>

- :material-play-circle-outline:{ .lg .middle } __Review a complete example__

    See how the optimization outputs drive real-world decisions.

    [:material-arrow-right: Sigenergy example](examples/sigenergy-system.md)

- :material-robot-outline:{ .lg .middle } __Build automations from the results__

    Turn recommended power schedules into actionable automations.

    [:material-arrow-right: Automation patterns](automations.md)

- :material-sync:{ .lg .middle } __Monitor data updates__

    Understand how new sensor data triggers optimizations.

    [:material-arrow-right: Data update guide](data-updates.md)

</div>
