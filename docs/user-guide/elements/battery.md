# Battery

Batteries are energy storage devices that can charge (store energy) and discharge (release energy).
HAEO optimizes when to charge and discharge based on electricity prices, solar availability, and economic preferences.

Internally, HAEO represents batteries as a single storage element and applies SOC preferences via connection pricing. This provides flexible, economically-rational battery behavior without partitioning the battery model.

!!! note "Connection endpoints"

    Battery elements appear in connection selectors only when Advanced Mode is enabled on your hub.

For mathematical details, see [Battery Modeling](../../modeling/device-layer/battery.md).

## Configuration

### Overview

A battery in HAEO represents:

- **Energy storage** with a maximum capacity (kWh)
- **Power limits** for charging and discharging (kW)
- **State of Charge (SOC)** tracking via a Home Assistant sensor
- **Efficiency** losses during charge/discharge cycles
- **Operating range preferences** guided by economic costs (min/max SOC)

### Configuration process

Battery configuration uses a single-step flow where you enter the name, connection, and configure each input field.
For each field, select "Entity" to link to a sensor, "Constant" to enter a fixed value, or "None" for optional fields you don't need.

Fields configured with "Constant" create input entities that you can adjust at runtime without reconfiguring.
Optional fields set to "None" are omitted from the optimization entirely.

## Configuration Fields

| Field                                                          | Type       | Required | Default | Description                                                |
| -------------------------------------------------------------- | ---------- | -------- | ------- | ---------------------------------------------------------- |
| **[Name](#name)**                                              | String     | Yes      | -       | Unique identifier (e.g., "Main Battery", "Garage Battery") |
| **[Capacity](#capacity)**                                      | Energy     | Yes      | -       | Total energy storage capacity                              |
| **[Current Charge Percentage](#current-charge-percentage)**    | Percentage | Yes      | -       | Home Assistant sensor reporting current SOC (0-100%)       |
| **[Min Charge Percentage](#min-and-max-charge-percentage)**    | Percentage | No       | 10      | Preferred minimum SOC (%)                                  |
| **[Max Charge Percentage](#min-and-max-charge-percentage)**    | Percentage | No       | 90      | Preferred maximum SOC (%)                                  |
| **[Undercharge Percentage](#undercharge-configuration)**       | Percentage | No       | -       | Hard minimum SOC limit (%)                                 |
| **[Overcharge Percentage](#overcharge-configuration)**         | Percentage | No       | -       | Hard maximum SOC limit (%)                                 |
| **[Undercharge Cost](#undercharge-configuration)**             | Price      | No       | -       | Economic penalty for discharging below min SOC             |
| **[Overcharge Cost](#overcharge-configuration)**               | Price      | No       | -       | Economic penalty for charging above max SOC                |
| **[Efficiency](#efficiency)**                                  | Percentage | No       | 99      | Round-trip efficiency                                      |
| **[Max Charge Power](#max-charge-and-discharge-power)**        | Power      | No       | -       | Maximum charging power                                     |
| **[Max Discharge Power](#max-charge-and-discharge-power)**     | Power      | No       | -       | Maximum discharging power                                  |
| **[Early Charge Incentive](#early-charge-incentive-advanced)** | Price      | No       | 0.001   | Small cost to prefer early charging (advanced)             |
| **[Discharge Cost](#discharge-cost)**                          | Price      | No       | 0       | Base discharge cost for degradation modeling               |

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

### Current charge percentage

Select the Home Assistant sensor that reports the battery's current SOC.
HAEO expects values between 0 and 100.

### Min and max charge percentage

Set the preferred operating range for routine battery use.
HAEO will normally keep the battery within this range.
These are the **inner bounds** of normal operation.
Leaving the defaults (10-90%) is a good starting point unless your manufacturer recommends otherwise.

### Efficiency

Enter the round-trip efficiency as a percentage (0-100).
HAEO automatically converts this to one-way efficiency internally for accurate charge/discharge modeling.
Most modern lithium batteries have round-trip efficiencies in the 95-98% range, while older chemistries may be lower.
Refer to your battery or inverter specifications for the round-trip efficiency value.

### Max charge and discharge power

Add limits based on your battery's charge/discharge rating.
Leave the fields blank when no practical limit applies.

!!! note

    Use the battery charge/discharge rating, not the inverter rating.
    Hybrid inverters often have separate ratings for battery power and inverter output power.

### Early Charge Incentive (Advanced)

Creates a small time-varying cost that prefers charging earlier in the optimization window when all else is equal.
Default is 0.001 \$/kWh (0.1 cents).

**How it works**: The incentive varies linearly from a small negative cost (encourages charging) at the beginning of the optimization window to zero at the end.
This prevents arbitrary timing decisions when grid prices are flat.

**When to adjust**:

- Keep the default (0.001) for most systems
- Increase slightly (0.002-0.005) if the battery seems to delay charging unnecessarily
- Decrease (0.0005) if you want more flexibility in timing

!!! important

    Keep this value small (< 0.01 \$/kWh) so it doesn't override actual price signals.

### Discharge Cost

Base cost in \$/kWh applied to all battery discharge operations.
Models battery degradation from cycling.

**Setting the cost**: Consider the cost of battery wear per cycle.
A typical value is \$0.00-\$0.05/kWh depending on battery chemistry and expected lifetime.

**Leave at zero** if you don't want to model degradation costs.

### Undercharge Configuration

Configure an extended low SOC range with economic penalties to model battery behavior below normal operating limits.
This section is optional and can be used independently of overcharge configuration.

#### Undercharge Percentage

Define the **hard minimum SOC limit** (absolute floor).
This is the lower bound of the battery's operating range.

**Ordering requirement**: Must be less than `min_charge_percentage`.

**Example**:

```
undercharge_percentage=5% < min_charge_percentage=10%
```

This allows operation between 5-10% SOC with an added `undercharge_cost` penalty when discharging below `min_charge_percentage`.

!!! tip "Key insight"

    `undercharge_percentage` is the hard limit - the battery cannot discharge below this level.
    The `min_charge_percentage` is the soft limit - HAEO prefers to stay above it but will discharge into the 5-10% range when economically justified.

### Overcharge Configuration

Configure an extended high SOC range with economic penalties to model battery behavior above normal operating limits.
This section is optional and can be used independently of undercharge configuration.

#### Overcharge Percentage

Define the **hard maximum SOC limit** (absolute ceiling).
This is the upper bound of the battery's operating range.

**Ordering requirement**: Must be greater than `max_charge_percentage`.

**Example**:

```
max_charge_percentage=90% < overcharge_percentage=95%
```

This allows operation between 90-95% SOC with an added `overcharge_cost` penalty when charging above `max_charge_percentage`.

!!! tip "Key insight"

    `overcharge_percentage` is the hard limit - the battery cannot charge above this level.
    The `max_charge_percentage` is the soft limit - HAEO prefers to stay below it but will charge into the 90-95% range when economically justified.

#### Undercharge Cost

Economic penalty in \$/kWh for **discharging** below `min_charge_percentage`.
Required when `undercharge_percentage` is configured.
This penalty applies **in addition to** the normal `discharge_cost`.

**Setting the cost**: Consider the economic value of avoiding deep discharge:

- Battery degradation from deep cycles
- Manufacturer warranty conditions
- Your risk tolerance for low SOC states

Typical values: \$0.50-\$2.00/kWh

**How it works**: The optimizer compares grid revenue against the combined penalties (discharge_cost + undercharge_cost).
If grid prices are \$0.40/kWh and total cost is \$0.50/kWh (e.g., \$0.02 discharge + \$0.48 undercharge), the battery won't discharge into the undercharge range.
If grid prices spike to \$0.80/kWh, the optimizer will economically justify deep discharge because the \$0.30/kWh profit (\$0.80 - \$0.50) makes it worthwhile.

**Applies to**: Energy discharged below `min_charge_percentage`.
The battery will not discharge below `undercharge_percentage` under any circumstance.

#### Overcharge Cost

Economic penalty in \$/kWh for **charging** above `max_charge_percentage`.
Required when `overcharge_percentage` is configured.

**Setting the cost**: Consider the economic value of avoiding high SOC:

- Battery degradation from high SOC levels
- Cell balancing concerns
- Your risk tolerance for high SOC states

Typical values: \$0.50-\$2.00/kWh

**How it works**: The optimizer compares available energy value against this penalty.

**From grid**: The battery will only charge into the overcharge range from the grid if grid prices are **negative** (you get paid to consume) by more than the overcharge cost.
For example, if overcharge cost is \$1.00/kWh, grid prices would need to be below -\$1.00/kWh.

**From solar**: The battery will charge into the overcharge range from solar if the forecasted future export value exceeds the overcharge cost.
For example, if export prices tomorrow are \$0.50/kWh and overcharge cost is \$0.20/kWh, HAEO will overcharge today to maximize export revenue tomorrow.

**Applies to**: Energy charged above `max_charge_percentage`.
The battery will not charge above `overcharge_percentage` under any circumstance.

## Configuration Examples

### Basic Battery Configuration

A typical battery configuration with just the essential parameters:

| Field                         | Example Value      |
| ----------------------------- | ------------------ |
| **Name**                      | Main Battery       |
| **Capacity**                  | 15 kWh             |
| **Current Charge Percentage** | sensor.battery_soc |
| **Min Charge Percentage**     | 20%                |
| **Max Charge Percentage**     | 90%                |
| **Efficiency**                | 99%                |
| **Max Charge Power**          | 6 kW               |
| **Max Discharge Power**       | 6 kW               |

This creates a battery that operates in the 20-90% range with no economic penalties for staying within that range.

### Battery with Extended Operating Range

A battery configured with undercharge and overcharge ranges for conditional extended operation:

| Field                         | Example Value      |
| ----------------------------- | ------------------ |
| **Name**                      | Main Battery       |
| **Capacity**                  | 15 kWh             |
| **Current Charge Percentage** | sensor.battery_soc |
| **Min Charge Percentage**     | 10%                |
| **Max Charge Percentage**     | 90%                |
| **Undercharge Percentage**    | 5%                 |
| **Overcharge Percentage**     | 95%                |
| **Undercharge Cost**          | 1.50 \$/kWh        |
| **Overcharge Cost**           | 1.00 \$/kWh        |
| **Efficiency**                | 99%                |
| **Max Charge Power**          | 6 kW               |
| **Max Discharge Power**       | 6 kW               |
| **Discharge Cost**            | 0.02 \$/kWh        |

In this example:

- **Undercharge range**: 5-10% (available with \$1.50/kWh discharge penalty)
- **Normal range**: 10-90% (preferred operation, only \$0.02/kWh discharge cost for degradation)
- **Overcharge range**: 90-95% (available with \$1.00/kWh charge penalty)
- Total usable range: 5-95% (90%)
- Higher undercharge cost reflects greater degradation risk at low SOC
- Optimizer will use extended ranges only when grid conditions justify the penalties

### Input Entities

Each configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                                                | Unit   | Description                                  |
| ---------------------------------------------------- | ------ | -------------------------------------------- |
| `number.{name}_capacity`                             | kWh    | Battery storage capacity                     |
| `number.{name}_soc`                                  | %      | Current state of charge from sensor          |
| `number.{name}_soc_min`                              | %      | Preferred minimum SOC (normal range floor)   |
| `number.{name}_soc_max`                              | %      | Preferred maximum SOC (normal range ceiling) |
| `number.{name}_soc_target`                           | %      | Target SOC at end of horizon                 |
| `number.{name}_max_charge_power`                     | kW     | Maximum charging power                       |
| `number.{name}_max_discharge_power`                  | kW     | Maximum discharging power                    |
| `number.{name}_charge_cost_per_cycle`                | -      | Base cycle degradation cost                  |
| `number.{name}_charge_cost_per_kwh`                  | \$/kWh | Per-kWh charging cost                        |
| `number.{name}_undercharge_soc`                      | %      | Hard minimum SOC limit (if configured)       |
| `number.{name}_overcharge_soc`                       | %      | Hard maximum SOC limit (if configured)       |
| `number.{name}_undercharge_cost` / `overcharge_cost` | \$/kWh | Penalty costs for extended regions           |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Battery element creates a single device in Home Assistant:

- **Battery device** (`{name}`): Always created with total power, energy, SOC, and shadow price sensors

### Battery Device Sensors

These sensors appear on the battery device:

| Sensor                                                       | Unit  | Description                                  |
| ------------------------------------------------------------ | ----- | -------------------------------------------- |
| [`sensor.{name}_power_charge`](#charge-power)                | kW    | Charging power                               |
| [`sensor.{name}_power_discharge`](#discharge-power)          | kW    | Discharging power                            |
| [`sensor.{name}_energy_stored`](#energy-stored)              | kWh   | Current energy level                         |
| [`sensor.{name}_state_of_charge`](#state-of-charge-sensor)   | %     | State of charge percentage                   |
| [`sensor.{name}_power_balance`](#power-balance-shadow-price) | \$/kW | Marginal value of power at battery terminals |

### Charge Power

The optimal charging power for this battery at each time period.

Values represent the average power during the period.
Positive values indicate energy flowing into the battery.
A value of 0 means the battery is not charging.

**Example**: A value of 3.2 kW means the battery is charging at an average rate of 3.2 kW during this period, limited by the configured max charge power or other system constraints.

### Discharge Power

The optimal discharging power for this battery at each time period.

Values represent the average power during the period.
Positive values indicate energy flowing out of the battery.
A value of 0 means the battery is not discharging.

**Example**: A value of 2.5 kW means the battery is discharging at an average rate of 2.5 kW during this period, providing power to loads or exporting to the grid.

### Energy Stored

The total energy currently stored in the battery across all SOC regions.

This represents the absolute energy level in kWh.
Multiply by 100 and divide by capacity to get state of charge percentage.

**Example**: A value of 12.5 kWh in a 15 kWh battery means 83.3% state of charge.

### State of Charge Sensor

The battery's state of charge as a percentage (0-100%).

This is calculated from the energy stored divided by total capacity.
Provides a convenient percentage view of the battery level.

**Example**: A value of 75% means the battery has 75% of its capacity available.

### Power Balance Shadow Price

The marginal value of power at the battery terminals.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price represents the economic value of 1 kW of additional power capacity at the battery.
It reflects the cost of power flowing through the battery connection point.

**Interpretation**:

- **Positive value**: Power at the battery terminals has value (usually during discharge periods)
- **Negative value**: Additional power would increase costs (usually during charging periods)
- **Magnitude**: Higher absolute values indicate the battery connection is more valuable to the system

**Example**: A value of 0.15 means 1 kW of additional power capacity at the battery would save \$0.15 per time period.

---

Each sensor includes forecast attributes with future timestamped values for visualization and automations.

## How It Works Internally

HAEO models batteries using a single storage element with an SOC-aware connection:

1. **Battery element**: Tracks stored energy within the configured SOC bounds
2. **SOC pricing**: Applies undercharge and overcharge penalties when enabled
3. **Network connection**: The connection applies efficiency, limits, and pricing

This architecture allows HAEO to:

- Prefer staying within the min/max SOC range when penalties are configured
- Trade off extended SOC operation when prices justify it
- Preserve hard SOC bounds defined by undercharge and overcharge percentages

## When to Use Extended Operating Ranges

Configure undercharge and overcharge ranges when you want to:

1. **Economic flexibility for extreme conditions**: Allow the battery to operate in extended SOC ranges when grid conditions make it economically worthwhile (e.g., very high grid prices justify deep discharge despite degradation costs).

2. **Model degradation economics**: Reflect the real economic cost of battery degradation at extreme SOC levels.
    The optimizer will automatically trade off grid savings against battery wear costs.

3. **Capture opportunistic value**: Enable the battery to charge above normal limits when excess solar is available or grid prices are negative, while still discouraging routine overcharging.

4. **Flexible protection**: Maintain conservative normal operation (e.g., 10-90%) while allowing economically-justified excursions (e.g., 5-95%) rather than imposing hard limits.

**When NOT to use extended ranges**:

- When the normal operating range is sufficient for your use case
- When you want absolute hard limits that cannot be violated under any circumstances (cost-based boundaries are economic, not physical)
- When you cannot estimate appropriate penalty costs relative to your grid price volatility
- For new batteries where the degradation cost structure is uncertain

**Key difference from hard limits**: Extended ranges create economic trade-offs, not absolute constraints.
The battery can operate in these ranges when conditions justify it, providing flexibility while still protecting against unnecessary degradation.

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
2. **Check efficiency**: Confirm you've entered round-trip efficiency (HAEO converts internally)
3. **Review power limits**: Ensure they match your battery rating

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

## Next Steps

Build on your battery configuration with these guides.

<div class="grid cards" markdown>

- :material-power-plug:{ .lg .middle } **Add a grid connection**

    ---

    Link your battery to grid pricing so HAEO can optimize imports and exports.

    [:material-arrow-right: Grid guide](grid.md)

- :material-source-branch:{ .lg .middle } **Define connections**

    ---

    Create power flow links between your battery and the rest of the network.

    [:material-arrow-right: Connection setup](connections.md)

- :material-chart-line:{ .lg .middle } **View optimization results**

    ---

    Verify the battery schedule and state of charge produced by HAEO.

    [:material-arrow-right: Optimization overview](../optimization.md)

- :material-math-integral:{ .lg .middle } **Battery modeling**

    ---

    Understand the mathematical formulation and constraints.

    [:material-arrow-right: Battery modeling](../../modeling/device-layer/battery.md)

</div>
