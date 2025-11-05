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

### Shadow Price Sensors

| Sensor                                           | Unit  | Description                                |
| ------------------------------------------------ | ----- | ------------------------------------------ |
| `{node}_shadow_price_node_balance`               | $/kWh | Marginal energy value at the node          |
| `{battery}_shadow_price_energy_balance`          | $/kWh | Marginal value of stored energy over time  |
| `{battery}_shadow_price_soc_min`                 | $/kWh | Benefit of relaxing minimum SOC limit      |
| `{battery}_shadow_price_soc_max`                 | $/kWh | Benefit of relaxing maximum SOC limit      |
| `{entity}_shadow_price_power_consumption_max`    | $/kW  | Value of additional consumption headroom   |
| `{entity}_shadow_price_power_production_max`     | $/kW  | Value of additional production headroom    |
| `{grid}_shadow_price_power_export_max`           | $/kW  | Value of additional export capacity        |
| `{grid}_shadow_price_power_import_max`           | $/kW  | Value of additional import capacity        |
| `{connection}_shadow_price_power_flow_min`       | $/kW  | Benefit of relaxing minimum flow limit     |
| `{connection}_shadow_price_power_flow_max`       | $/kW  | Benefit of relaxing maximum flow limit     |
| `{photovoltaics}_shadow_price_forecast_limit`    | $/kWh | Value of additional photovoltaic capacity  |

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
    - datetime: "2025-10-12T10:00:00+00:00"
      value: 5.2
    - datetime: "2025-10-12T10:05:00+00:00"
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
