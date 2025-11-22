# Sensor Type Reference

## Network Sensors

| Sensor                            | Unit | Description             |
| --------------------------------- | ---- | ----------------------- |
| `{network}_optimization_cost`     | \$   | Total cost over horizon |
| `{network}_optimization_status`   | -    | Status (optimal/failed) |
| `{network}_optimization_duration` | s    | Solve time              |

## Entity Sensors

### All Entities

| Sensor           | Unit | Description            |
| ---------------- | ---- | ---------------------- |
| `{entity}_power` | kW   | Current/forecast power |

### Battery Only

| Sensor            | Unit | Description     |
| ----------------- | ---- | --------------- |
| `{entity}_energy` | kWh  | Energy level    |
| `{entity}_soc`    | %    | State of charge |

## Power Sign Conventions

| Entity        | Positive    | Negative       |
| ------------- | ----------- | -------------- |
| Battery       | Discharging | Charging       |
| Grid          | Importing   | Exporting      |
| Photovoltaics | Generating  | Never negative |
| Load          | Consuming   | Never negative |

## Forecast Attribute

All sensors include a `forecast` attribute that maps ISO 8601 timestamps to future values:

```yaml
attributes:
  forecast:
    '2025-10-12T10:00:00+00:00': 5.2
    '2025-10-12T10:05:00+00:00': 5.1
```

The number of forecast entries depends on the sensor type.

## Forecast Lengths

Power and energy sensors have different forecast lengths due to how they measure values:

**Power sensors** (kW) measure average power over each optimization period.
With a 12-hour horizon and 15-minute periods, power sensors have 48 forecast entries (one per period).

**Energy sensors** (kWh, %, SOC) measure instantaneous values at time boundaries between periods.
With the same 12-hour horizon and 15-minute periods, energy sensors have 49 forecast entries (one per boundary).

This applies consistently across all element types:

- Battery power: 48 values (intervals)
- Battery energy/SOC: 49 values (boundaries)
- Grid power: 48 values (intervals)
- Solar power: 48 values (intervals)
- Load power: 48 values (intervals)

The extra boundary value in energy sensors represents the state at the end of the optimization horizon.

For more technical details, see the [modeling documentation](../modeling/index.md#power-and-energy-discretization).

## Sensor States

- **Numeric**: Valid optimization result
- **unknown**: Not yet run or failed
- **unavailable**: Integration disabled or restarting

## Related Documentation

- [Element Reference](elements.md)
- [Battery Configuration](../user-guide/elements/battery.md)
- [Troubleshooting](../user-guide/troubleshooting.md)
