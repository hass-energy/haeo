# Sensor Type Reference

All sensor types created by HAEO.

## Network Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| `{network}_optimization_cost` | $ | Total optimized cost over horizon |
| `{network}_optimization_status` | - | Optimization status (optimal, feasible, infeasible) |
| `{network}_optimization_duration` | s | Time taken to solve optimization |

## Entity Sensors

### Power Sensors

`{entity}_power` - Current optimal power (kW)

- **Positive**: Producing/discharging/importing
- **Negative**: Consuming/charging/exporting

### Energy Sensors (Batteries)

`{entity}_energy` - Current energy level (kWh)

### SOC Sensors (Batteries)

`{entity}_soc` - State of charge (%)

## Forecast Attributes

All sensors include `forecast` attribute with timestamped future values:

```yaml
attributes:
  forecast:
    - datetime: "2025-10-11T12:00:00+00:00"
      value: 5.2
    - datetime: "2025-10-11T12:05:00+00:00"
      value: 5.1
```

## Sensor States

| State | Meaning |
|-------|---------|
| Numeric value | Valid optimization result |
| `unknown` | Optimization not yet run or failed |
| `unavailable` | Sensor temporarily unavailable |
