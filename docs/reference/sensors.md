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

All sensors include `forecast` attribute:

```yaml
attributes:
  forecast:
    - datetime: '2025-10-12T10:00:00+00:00'
      value: 5.2
    - datetime: '2025-10-12T10:05:00+00:00'
      value: 5.1
```

Length = number of periods in horizon.

## Sensor States

- **Numeric**: Valid optimization result
- **unknown**: Not yet run or failed
- **unavailable**: Integration disabled or restarting

## Related Documentation

- [Element Reference](elements.md)
- [Battery Configuration](../user-guide/elements/battery.md)
- [Troubleshooting](../user-guide/troubleshooting.md)
