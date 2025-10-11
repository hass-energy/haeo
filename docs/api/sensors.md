# Sensors API

Sensor implementations that expose optimization results to Home Assistant.

## Sensor Types

### Network Sensors

- **OptimizationCostSensor**: Total system cost
- **OptimizationStatusSensor**: Solver status
- **OptimizationDurationSensor**: Solve time

### Entity Sensors

- **PowerSensor**: Optimal power at each time step
- **EnergySensor**: Battery energy level (for batteries)
- **SOCSensor**: State of charge (for batteries)

## Location

`custom_components/haeo/sensors/`

### Key Modules

- `base.py`: Base sensor classes
- `cost.py`: Cost sensor
- `energy.py`: Energy sensors
- `power.py`: Power sensors  
- `soc.py`: State of charge sensors
- `optimization.py`: Optimization status sensors

## Forecast Attributes

All sensors provide forecast attributes with timestamped future values for use in automations and dashboards.

See [Sensor Type Reference](../reference/sensors.md) for detailed sensor information.
