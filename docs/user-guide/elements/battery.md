# Battery Configuration

Batteries are energy storage devices that can charge (store energy) and discharge (release energy).
HAEO optimizes when to charge and discharge based on electricity prices, solar availability, and system constraints.

## Overview

A battery in HAEO represents:

- **Energy storage** with a maximum capacity (kWh)
- **Power limits** for charging and discharging (kW)
- **State of Charge (SOC)** tracking via a Home Assistant sensor
- **Efficiency** losses during charge/discharge cycles
- **Operating range** constraints (min/max SOC)

## Configuration Fields

| Field                         | Type            | Required | Default | Description                                                |
| ----------------------------- | --------------- | -------- | ------- | ---------------------------------------------------------- |
| **Name**                      | String          | Yes      | -       | Unique identifier (e.g., "Main Battery", "Garage Battery") |
| **Capacity**                  | Number (kWh)    | Yes      | -       | Total energy storage capacity                              |
| **Initial Charge Percentage** | Sensor ID       | Yes      | -       | Home Assistant sensor reporting current SOC (0-100%)       |
| **Min Charge Percentage**     | Number (%)      | No       | 10      | Minimum allowed SOC (hard limit)                           |
| **Max Charge Percentage**     | Number (%)      | No       | 90      | Maximum allowed SOC (hard limit)                           |
| **Undercharge Percentage**    | Number (%)      | No       | -       | Soft minimum SOC (requires undercharge cost)               |
| **Overcharge Percentage**     | Number (%)      | No       | -       | Soft maximum SOC (requires overcharge cost)                |
| **Undercharge Cost**          | Number (\$/kWh) | No       | -       | Penalty for operating below undercharge percentage         |
| **Overcharge Cost**           | Number (\$/kWh) | No       | -       | Penalty for operating above overcharge percentage          |
| **Efficiency**                | Number (%)      | No       | 99      | **One-way** efficiency (see below)                         |
| **Max Charge Power**          | Number (kW)     | No       | -       | Maximum charging power                                     |
| **Max Discharge Power**       | Number (kW)     | No       | -       | Maximum discharging power                                  |
| **Charge Cost**               | Number (\$/kWh) | No       | 0       | Additional charging cost (see below)                       |
| **Discharge Cost**            | Number (\$/kWh) | No       | 0       | Additional discharging cost (see below)                    |

If not specified, power is unconstrained (limited only by other system constraints).

!!! info "Asymmetric Limits"

    Some systems have different charge and discharge power limits.
    Configure them independently for accurate optimization.

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Capacity

Enter the usable capacity in kWh from your battery or inverter documentation.
The optimizer uses this value when calculating state of charge.

### Initial charge percentage

Select the Home Assistant sensor that reports the battery's current SOC.
HAEO expects values between 0 and 100.

### Min and max charge percentage

Set the allowable SOC range to protect your battery.
Leaving the defaults is a good starting point unless your manufacturer recommends otherwise.

### Efficiency

Enter the one-way efficiency as a percentage.
If you only know the round-trip efficiency, take the square root to convert it.
For example, a 97% round-trip battery becomes roughly 98.5% one-way.
Most lithium systems sit in the high 90s, while older chemistries are lower.

### Max charge and discharge power

Add limits if your inverter or wiring restricts how quickly the battery can charge or discharge.
Leave the fields blank when no practical limit applies.

### Charge Cost

Adds an extra cost (or incentive) per kWh when charging.
Leave it at zero for most systems.
Set a small negative value if you want the battery to favour early charging, or a small positive value if you want to discourage unnecessary cycling.

### Discharge Cost

Adds an extra cost per kWh when discharging.
Use a small positive value if the battery switches direction too often, or leave it at zero if you are happy with the schedule.

### Undercharge Percentage (Optional)

Define a soft minimum SOC below which penalty costs apply.
When paired with undercharge cost, the optimizer can temporarily operate in the range between the hard minimum and undercharge percentage when economically justified.

For example:

- Hard minimum: 5% (absolute lower limit via `min_charge_percentage`)
- Undercharge percentage: 10% (soft minimum with penalties)

The optimizer will normally stay above 10%, but can use the 5-10% range during extreme conditions (e.g., very high grid prices), paying the undercharge cost penalty.

### Overcharge Percentage (Optional)

Define a soft maximum SOC above which penalty costs apply.
When paired with overcharge cost, the optimizer can temporarily operate in the range between the overcharge percentage and hard maximum when economically beneficial.

For example:

- Overcharge percentage: 90% (soft maximum with penalties)
- Hard maximum: 95% (absolute upper limit via `max_charge_percentage`)

The optimizer will normally stay below 90%, but can use the 90-95% range to capture cheap energy (e.g., excess solar production), paying the overcharge cost penalty.

### Undercharge Cost (Optional)

Cost penalty in \$/kWh for operating below the undercharge percentage.
Required when undercharge percentage is configured.

**Setting the cost**: Consider battery degradation from deep discharge cycles.
A typical value might be \$0.50-\$2.00/kWh.
Higher values more strongly discourage operation below the undercharge percentage.

**Time-varying costs**: You can provide multiple sensor values for time-varying costs (e.g., higher penalties during peak hours).

### Overcharge Cost (Optional)

Cost penalty in \$/kWh for operating above the overcharge percentage.
Required when overcharge percentage is configured.

**Setting the cost**: Consider battery degradation from high SOC levels.
A typical value might be \$0.50-\$2.00/kWh.
Higher values more strongly discourage operation above the overcharge percentage.

**Time-varying costs**: You can provide multiple sensor values for time-varying costs (e.g., dynamic penalty based on conditions).

## Configuration Examples

### Basic Battery Configuration

A typical battery configuration without soft limits:

| Field                         | Example Value      |
| ----------------------------- | ------------------ |
| **Name**                      | Main Battery       |
| **Capacity**                  | 15 kWh             |
| **Initial Charge Percentage** | sensor.battery_soc |
| **Min Charge Percentage**     | 20%                |
| **Max Charge Percentage**     | 90%                |
| **Efficiency**                | 98.5%              |
| **Max Charge Power**          | 6 kW               |
| **Max Discharge Power**       | 6 kW               |
| **Charge Cost**               | -0.005 \$/kWh      |
| **Discharge Cost**            | 0.001 \$/kWh       |

### Battery with Soft Limits

A battery configured with soft limits for extended operating range:

| Field                         | Example Value      |
| ----------------------------- | ------------------ |
| **Name**                      | Main Battery       |
| **Capacity**                  | 15 kWh             |
| **Initial Charge Percentage** | sensor.battery_soc |
| **Min Charge Percentage**     | 5%                 |
| **Max Charge Percentage**     | 95%                |
| **Undercharge Percentage**    | 10%                |
| **Overcharge Percentage**     | 90%                |
| **Undercharge Cost**          | 1.50 \$/kWh        |
| **Overcharge Cost**           | 1.00 \$/kWh        |
| **Efficiency**                | 98.5%              |
| **Max Charge Power**          | 6 kW               |
| **Max Discharge Power**       | 6 kW               |

In this example:

- Normal operation: 10-90% (80% usable range)
- Extended operation: 5-95% when economically justified (90% total range)
- Higher undercharge cost reflects greater degradation risk at low SOC

## Sensors Created

HAEO creates these sensors for each battery:

| Sensor                 | Description                                                     |
| ---------------------- | --------------------------------------------------------------- |
| `sensor.{name}_power`  | Optimal power (kW). Positive = discharging, negative = charging |
| `sensor.{name}_energy` | Current energy level (kWh)                                      |
| `sensor.{name}_soc`    | State of charge (%)                                             |

Each sensor includes forecast attributes with future timestamped values for visualization and automations.

## When to Use Soft Limits

Soft limits are useful when you want to:

1. **Extend operational range conditionally**: Allow the battery to exceed normal limits during extreme price events while discouraging routine operation outside preferred ranges.

2. **Model battery degradation**: Reflect increased degradation costs at very low or very high SOC levels.
    The optimizer will use these ranges only when grid savings exceed the penalty costs.

3. **Safety margins with flexibility**: Maintain conservative normal operation while retaining emergency capacity.
    For example, keep 10% reserve normally but use it during power outages or price spikes.

4. **Time-varying constraints**: Use sensor-based costs to implement dynamic penalties based on conditions like temperature, battery age, or time of day.

**When NOT to use soft limits**:

- When hard limits are sufficient for your use case
- When you want strict enforcement (use hard limits instead)
- When the penalty cost structure is unclear or difficult to estimate

## Troubleshooting

### Battery Not Charging/Discharging

If your battery remains idle:

1. **Check price forecasts**: HAEO needs price variation to optimize.
    See the [forecasts page](../forecasts-and-sensors.md) for details.
2. **Verify SOC sensor**: Ensure it's reporting correctly
3. **Review constraints**: Too-tight SOC limits may prevent operation
4. **Check connections**: Battery must be [connected](connections.md) to the network

### Unrealistic SOC Predictions

If forecast SOC values seem wrong:

1. **Verify capacity**: Ensure capacity matches your actual battery
2. **Check efficiency**: Confirm it's one-way efficiency (sqrt of the round-trip value)
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
2. Connect each battery to the network (typically via a [node](node.md))
3. HAEO will optimize all batteries together

This allows HAEO to:

- Balance charging across batteries
- Optimize total system cost
- Handle different battery characteristics

## Related Documentation

- [Forecasts & Sensors](../forecasts-and-sensors.md) - Creating SOC sensors
- [Grid Configuration](grid.md) - Pricing that drives battery decisions
- [Connections](connections.md) - Connect battery to network
- [Battery Modeling](../../modeling/battery.md) - Mathematical details
- [Units & Stability](../../developer-guide/units.md) - Why kW/kWh units

## Next Steps

Build on your battery configuration with these guides.

<div class="grid cards" markdown>

- :material-power-plug:{ .lg .middle } __Add a grid connection__

    Link your battery to grid pricing so HAEO can optimize imports and exports.

    [:material-arrow-right: Grid guide](grid.md)

- :material-source-branch:{ .lg .middle } __Define connections__

    Create power flow links between your battery and the rest of the network.

    [:material-arrow-right: Connection setup](connections.md)

- :material-chart-line:{ .lg .middle } __View optimization results__

    Verify the battery schedule and state of charge produced by HAEO.

    [:material-arrow-right: Optimization overview](../optimization.md)

</div>
