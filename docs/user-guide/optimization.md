# Understanding Optimization Results

This guide explains how to interpret HAEO's optimization results and use them effectively.

## Optimization Sensors

HAEO creates three main network sensors:

### Optimization Cost

**Entity ID**: `sensor.{network_name}_optimization_cost`

Total cost over the optimization horizon in dollars.

- **Lower is better**: HAEO minimizes this value
- **Includes**: Import costs, export revenue, storage costs
- **Unit**: $ (or your configured currency)

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

- **Typical**: 0.5-5 seconds for small networks
- **Large networks**: 5-30 seconds
- **Too slow**: Consider reducing horizon or increasing period

## Entity Sensors

For each configured entity, HAEO creates sensors:

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
    - datetime: "2025-10-11T12:00:00+00:00"
      value: 5.2
    - datetime: "2025-10-11T12:05:00+00:00"
      value: 5.1
    # ... more timestamped values
```

Use these in automations or dashboards to visualize the optimal schedule.

## Using Results in Automations

### Example: Control Battery Based on Optimization

```yaml
automation:
  - alias: "Follow HAEO Battery Schedule"
    trigger:
      - platform: state
        entity_id: sensor.main_battery_power
    action:
      - service: battery.set_power
        data:
          power: "{{ states('sensor.main_battery_power') | float }}"
```

## Performance Considerations

### Optimization Duration

If optimization takes too long:

1. **Reduce horizon**: Use fewer hours
2. **Increase period**: Use larger time steps
3. **Simplify network**: Remove unnecessary entities
4. **Try different solver**: HiGHS is usually fastest

### Update Frequency

HAEO re-optimizes periodically. Balance:

- **More frequent**: Better response to changes, higher CPU usage
- **Less frequent**: Lower CPU usage, may miss price changes

## Interpreting Cost

The optimization cost represents the total forecasted cost over the horizon, not just the immediate cost.

**Example**:
- Horizon: 48 hours
- Cost: $25.50
- Average: $0.53/hour

This helps you:
- Compare different configurations
- Understand system economics
- Validate optimization is working

## Related Documentation

- [Troubleshooting](troubleshooting.md)
- [Objective Function](../modeling/objective-function.md)

[:octicons-arrow-right-24: Continue to Examples](examples/sigenergy-system.md)
