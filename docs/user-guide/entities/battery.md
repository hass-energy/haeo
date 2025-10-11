# Battery Configuration

Batteries are energy storage devices that can charge (store energy) and discharge (release energy). HAEO optimizes when to charge and discharge based on electricity prices, solar availability, and system constraints.

## Overview

A battery in HAEO represents:

- **Energy storage** with a maximum capacity (kWh)
- **Power limits** for charging and discharging (kW)
- **State of Charge (SOC)** tracking via a Home Assistant sensor
- **Efficiency** losses during charge/discharge cycles
- **Operating range** constraints (min/max SOC)

## Configuration Fields

| Field                         | Type           | Required | Default | Description                                                |
| ----------------------------- | -------------- | -------- | ------- | ---------------------------------------------------------- |
| **Name**                      | String         | Yes      | -       | Unique identifier (e.g., "Main Battery", "Garage Battery") |
| **Capacity**                  | Number (kWh)   | Yes      | -       | Total energy storage capacity                              |
| **Initial Charge Percentage** | Sensor ID      | Yes      | -       | Home Assistant sensor reporting current SOC (0-100%)       |
| **Min Charge Percentage**     | Number (%)     | No       | 10      | Minimum allowed SOC                                        |
| **Max Charge Percentage**     | Number (%)     | No       | 90      | Maximum allowed SOC                                        |
| **Efficiency**                | Number (%)     | No       | 99      | **One-way** efficiency (see below)                         |
| **Max Charge Power**          | Number (kW)    | No       | -       | Maximum charging power                                     |
| **Max Discharge Power**       | Number (kW)    | No       | -       | Maximum discharging power                                  |
| **Charge Cost**               | Number ($/kWh) | No       | 0       | Additional charging cost (see below)                       |
| **Discharge Cost**            | Number ($/kWh) | No       | 0       | Additional discharging cost (see below)                    |

### Name

Use descriptive, user-friendly names without special characters:

- ✅ "Main Battery", "Garage Battery", "Backup Battery"
- ❌ "Main_Battery", "battery1", "bat"

HAEO automatically converts names to valid entity IDs.

### Capacity

Total energy storage capacity in kWh. Check your battery's datasheet for this value.

### Initial Charge Percentage

Sensor entity ID that reports current battery SOC as a percentage (0-100).

**Requirements**:

- Updates regularly (at least every 5 minutes)
- Reports percentage (not decimal: 50% not 0.5)
- Accurate readings from battery management system

**Example**: `sensor.battery_state_of_charge`

See [forecasts and sensors](../forecasts-and-sensors.md) for creating template sensors if needed.

### Min/Max Charge Percentage

Operating range for battery SOC:

- **Min (default 10%)**: Prevents deep discharge that can damage batteries
- **Max (default 90%)**: Prevents overcharging, extends battery lifespan

**Typical ranges**:

- Balanced: 10-90% (80% usable capacity)
- Conservative: 20-80% (60% usable, longer life)
- Maximum: 0-100% (full capacity, faster degradation)

### Efficiency

!!! warning "Important: One-Way Efficiency"
HAEO uses **one-way efficiency**, not round-trip efficiency.

    **Example**: If your battery has 97% round-trip efficiency:

    - One-way efficiency = √0.97 ≈ **98.5%**
    - Configure as: `Efficiency: 98.5`

HAEO models efficiency as symmetric losses on both charging and discharging. The one-way efficiency is applied to each operation:

- **Charging**: Only 98.5% of input energy is stored
- **Discharging**: Only 98.5% of stored energy is output
- **Round-trip**: 0.985 × 0.985 = 0.97 (97%)

If you only know round-trip efficiency, calculate: `one_way = sqrt(round_trip)`

**Typical battery efficiencies** (round-trip):

- Lithium-ion (NMC, LFP): 95-98%
- Lead-acid: 80-85%
- Flow batteries: 65-85%

### Max Charge/Discharge Power

Maximum power rates in kW for charging and discharging.

These limits typically come from:

- Battery inverter rating
- Battery cell chemistry limits
- Electrical installation capacity

If not specified, power is unconstrained (limited only by other system constraints).

!!! info "Asymmetric Limits"
Some systems have different charge and discharge power limits. Configure them independently for accurate optimization.

### Charge Cost

**Additional cost per kWh for charging**, beyond electricity prices.

**Default**: 0 (no additional cost)

**Uses**:

1. **Encourage early charging**: Set a **negative** value to incentivize charging early in the forecast window

   - Example: `-0.01` gives a $0.01/kWh "bonus" for charging
   - This is because the cost **diminishes over the forecast horizon**

2. **Battery degradation**: Set a small positive value to model wear costs
   - Example: `0.01` adds $0.01/kWh degradation cost

!!! tip "Temporal Diminishing"
The charge cost diminishes linearly over the forecast horizon. Early charging gets more negative (bigger bonus) or less positive (smaller penalty), encouraging proactive battery management.

**Most users** should leave this at 0 or set slightly negative to encourage charging.

### Discharge Cost

**Additional cost per kWh for discharging**, beyond opportunity cost.

**Default**: 0 (no additional cost)

**Uses**:

1. **Prevent fluttering**: Set a small positive value to avoid excessive cycling

   - Example: `0.001` (0.1 cents/kWh)
   - Prevents battery from charging/discharging for tiny price differences
   - Reduces wear from unnecessary cycling

2. **Battery degradation**: Model wear from discharge cycles
   - Example: `0.01` for more aggressive degradation cost

!!! info "Fluttering Prevention"
Without discharge cost, tiny price changes (e.g., 0.1 cent/kWh) can cause the optimizer to cycle the battery repeatedly. A small discharge cost prevents this behavior while still allowing beneficial charging/discharging.

**Most users** should set this to a small positive value like `0.001` to prevent fluttering.

## Configuration Example

Here's a typical battery configuration:

```yaml
Name: Main Battery
Capacity: 15 kWh
Initial Charge Percentage: sensor.battery_soc
Min Charge Percentage: 20%
Max Charge Percentage: 90%
Efficiency: 98.5% # 97% round-trip
Max Charge Power: 6 kW
Max Discharge Power: 6 kW
Charge Cost: -0.005 $/kWh # Small bonus to encourage early charging
Discharge Cost: 0.001 $/kWh # Prevent fluttering
```

## How HAEO Uses Battery Configuration

### State of Charge Tracking

HAEO reads your SOC sensor at the start of each optimization and projects how SOC changes over the horizon based on charge/discharge decisions.

### Optimization Strategy

HAEO determines the optimal charge/discharge schedule by:

1. **Price awareness**: Charge during low-price periods, discharge during high-price periods
2. **SOC constraints**: Keep SOC between min and max limits
3. **Power limits**: Respect max charge/discharge power
4. **Efficiency**: Account for losses
5. **Forecast integration**: Plan ahead based on price and solar forecasts

### Typical Behavior

With time-of-use pricing, you'll typically see:

- **Overnight charging**: When prices are low
- **Peak discharge**: During expensive peak periods
- **Solar charging**: During midday if solar exceeds consumption
- **SOC management**: Maintains reserves for expected high-price periods

## Sensors Created

HAEO creates these sensors for each battery:

| Sensor                 | Description                                                     |
| ---------------------- | --------------------------------------------------------------- |
| `sensor.{name}_power`  | Optimal power (kW). Positive = discharging, negative = charging |
| `sensor.{name}_energy` | Current energy level (kWh)                                      |
| `sensor.{name}_soc`    | State of charge (%)                                             |

Each sensor includes forecast attributes with future timestamped values for visualization and automations.

## Troubleshooting

### Battery Not Charging/Discharging

If your battery remains idle:

1. **Check price forecasts**: HAEO needs price variation to optimize (see [forecasts page](../forecasts-and-sensors.md))
2. **Verify SOC sensor**: Ensure it's reporting correctly
3. **Review constraints**: Too-tight SOC limits may prevent operation
4. **Check connections**: Battery must be [connected](../connections.md) to the network

### Unrealistic SOC Predictions

If forecast SOC values seem wrong:

1. **Verify capacity**: Ensure capacity matches your actual battery
2. **Check efficiency**: Confirm it's one-way efficiency (√round-trip)
3. **Review power limits**: Ensure they match your inverter rating

### SOC Sensor Issues

Common problems:

- **Not updating**: Check sensor entity in Developer Tools → States
- **Wrong units**: Must be 0-100%, not 0-1 decimal
- **Incorrect values**: Calibrate battery management system

See the [troubleshooting guide](../troubleshooting.md) for more solutions.

## Multiple Batteries

HAEO supports multiple batteries in the same network:

1. Add each battery with a unique name
2. Connect each battery to the network (typically via a [net entity](net.md))
3. HAEO will optimize all batteries together

This allows HAEO to:

- Balance charging across batteries
- Optimize total system cost
- Handle different battery characteristics

## Related Documentation

- [Forecasts & Sensors](../forecasts-and-sensors.md) - Creating SOC sensors
- [Grid Configuration](grid.md) - Pricing that drives battery decisions
- [Connections](../connections.md) - Connect battery to network
- [Battery Modeling](../../modeling/battery.md) - Mathematical details
- [Units & Stability](../../developer-guide/units.md) - Why kW/kWh units

## Next Steps

After configuring your battery:

1. [Add a grid connection](grid.md) for import/export pricing
2. [Define connections](../connections.md) between battery and grid
3. [View optimization results](../optimization.md) to see battery schedule

[:octicons-arrow-right-24: Continue to Grid Configuration](grid.md)
