# Battery

Batteries are energy storage devices that can charge (store energy) and discharge (release energy).
HAEO optimizes when to charge and discharge based on electricity prices, solar availability, and economic preferences.

## Configuration

### Overview

A battery in HAEO represents:

- **Energy storage** with a maximum capacity (kWh)
- **Power limits** for charging and discharging (kW)
- **State of Charge (SOC)** tracking via a Home Assistant sensor
- **Efficiency** losses during charge/discharge cycles
- **Operating range preferences** guided by economic costs (min/max SOC)

## Configuration Fields

| Field                                                          | Type                                  | Required | Default | Description                                                |
| -------------------------------------------------------------- | ------------------------------------- | -------- | ------- | ---------------------------------------------------------- |
| **[Name](#name)**                                              | String                                | Yes      | -       | Unique identifier (e.g., "Main Battery", "Garage Battery") |
| **[Capacity](#capacity)**                                      | Number (kWh)                          | Yes      | -       | Total energy storage capacity                              |
| **[Current Charge Percentage](#current-charge-percentage)**    | [sensor](../forecasts-and-sensors.md) | Yes      | -       | Home Assistant sensor reporting current SOC (0-100%)       |
| **[Min Charge Percentage](#min-and-max-charge-percentage)**    | Number (%)                            | No       | 10      | Preferred minimum SOC (%)                                  |
| **[Max Charge Percentage](#min-and-max-charge-percentage)**    | Number (%)                            | No       | 90      | Preferred maximum SOC (%)                                  |
| **[Undercharge Percentage](#undercharge-configuration)**       | Number (%)                            | No       | -       | Hard minimum SOC limit (%)                                 |
| **[Overcharge Percentage](#overcharge-configuration)**         | Number (%)                            | No       | -       | Hard maximum SOC limit (%)                                 |
| **[Undercharge Cost](#undercharge-configuration)**             | Number (\$/kWh)                       | No       | -       | Economic penalty for discharging below min SOC             |
| **[Overcharge Cost](#overcharge-configuration)**               | Number (\$/kWh)                       | No       | -       | Economic penalty for charging above max SOC                |
| **[Efficiency](#efficiency)**                                  | Number (%)                            | No       | 99      | Round-trip efficiency                                      |
| **[Max Charge Power](#max-charge-and-discharge-power)**        | Number (kW)                           | No       | -       | Maximum charging power                                     |
| **[Max Discharge Power](#max-charge-and-discharge-power)**     | Number (kW)                           | No       | -       | Maximum discharging power                                  |
| **[Early Charge Incentive](#early-charge-incentive-advanced)** | Number (\$/kWh)                       | No       | 0.001   | Small cost to prefer early charging (advanced)             |
| **[Discharge Cost](#discharge-cost)**                          | Number (\$/kWh)                       | No       | 0       | Base discharge cost for degradation modeling               |

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
This creates an "undercharge section" between `undercharge_percentage` and `min_charge_percentage`.

**Ordering requirement**: Must be less than `min_charge_percentage`.

**Example**:

```
undercharge_percentage=5% < min_charge_percentage=10%
```

Creates an undercharge section from 5-10% where discharging incurs the `undercharge_cost` penalty in addition to the normal `discharge_cost`.

!!! tip "Key insight"

    `undercharge_percentage` is the hard limit - the battery cannot discharge below this level.
    The `min_charge_percentage` is the soft limit - HAEO prefers to stay above it but will discharge into the 5-10% undercharge section when economically justified (e.g., grid prices spike high enough to overcome the penalty).

### Overcharge Configuration

Configure an extended high SOC range with economic penalties to model battery behavior above normal operating limits.
This section is optional and can be used independently of undercharge configuration.

#### Overcharge Percentage

Define the **hard maximum SOC limit** (absolute ceiling).
This creates an "overcharge section" between `max_charge_percentage` and `overcharge_percentage`.

**Ordering requirement**: Must be greater than `max_charge_percentage`.

**Example**:

```
max_charge_percentage=90% < overcharge_percentage=95%
```

Creates an overcharge section from 90-95% where charging incurs the `overcharge_cost` penalty.

!!! tip "Key insight"

    `overcharge_percentage` is the hard limit - the battery cannot charge above this level.
    The `max_charge_percentage` is the soft limit - HAEO prefers to stay below it but will charge into the 90-95% overcharge section when economically justified.

#### Undercharge Cost

Economic penalty in \$/kWh for **discharging** from the undercharge section.
Required when `undercharge_percentage` is configured.
This penalty applies **in addition to** the normal `discharge_cost`.

**Setting the cost**: Consider the economic value of avoiding deep discharge:

- Battery degradation from deep cycles
- Manufacturer warranty conditions
- Your risk tolerance for low SOC states

Typical values: \$0.50-\$2.00/kWh

**How it works**: The optimizer compares grid revenue against the combined penalties (discharge_cost + undercharge_cost).
If grid prices are \$0.40/kWh and total cost is \$0.50/kWh (e.g., \$0.02 discharge + \$0.48 undercharge), the battery won't discharge into the undercharge section.
If grid prices spike to \$0.80/kWh, the optimizer will economically justify deep discharge because the \$0.30/kWh profit (\$0.80 - \$0.50) makes it worthwhile.

**Applies to**: Energy discharged from the undercharge section (below `min_charge_percentage`).
The battery will not discharge below `undercharge_percentage` under any circumstance - that is the hard limit.

#### Overcharge Cost

Economic penalty in \$/kWh for **charging** into the overcharge section.
Required when `overcharge_percentage` is configured.

**Setting the cost**: Consider the economic value of avoiding high SOC:

- Battery degradation from high SOC levels
- Cell balancing concerns
- Your risk tolerance for high SOC states

Typical values: \$0.50-\$2.00/kWh

**How it works**: The optimizer compares available energy value against this penalty.

**From grid**: The battery will only charge into the overcharge section from the grid if grid prices are **negative** (you get paid to consume) by more than the overcharge cost.
For example, if overcharge cost is \$1.00/kWh, grid prices would need to be below -\$1.00/kWh.

**From solar**: The battery will charge into the overcharge section from solar if the forecasted future export value exceeds the overcharge cost.
For example, if export prices tomorrow are \$0.50/kWh and overcharge cost is \$0.20/kWh, HAEO will overcharge today to maximize export revenue tomorrow.

**Applies to**: Energy charged into the overcharge section (above `max_charge_percentage`).
The battery will not charge above `overcharge_percentage` under any circumstance - that is the hard limit.

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

A battery configured with undercharge and overcharge sections for conditional extended operation:

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

- **Undercharge section**: 5-10% (available with \$1.50/kWh discharge penalty)
- **Normal section**: 10-90% (preferred operation, only \$0.02/kWh discharge cost for degradation)
- **Overcharge section**: 90-95% (available with \$1.00/kWh charge penalty)
- Total usable range: 5-95% (90%)
- Higher undercharge cost reflects greater degradation risk at low SOC
- Optimizer will use extended sections only when grid conditions justify the penalties

## Sensors Created

HAEO creates these sensors for each battery to provide visibility into power flows, energy storage, and optimization constraints.

| Sensor                                                                               | Unit   | Description                                  |
| ------------------------------------------------------------------------------------ | ------ | -------------------------------------------- |
| [`sensor.{name}_power_charge`](#power-charge)                                        | kW     | Charging power                               |
| [`sensor.{name}_power_discharge`](#power-discharge)                                  | kW     | Discharging power                            |
| [`sensor.{name}_energy_stored`](#energy-stored)                                      | kWh    | Current energy level                         |
| [`sensor.{name}_state_of_charge`](#state-of-charge)                                  | %      | State of charge percentage                   |
| [`sensor.{name}_charge_price`](#charge-price)                                        | \$/kWh | Current charging price                       |
| [`sensor.{name}_discharge_price`](#discharge-price)                                  | \$/kWh | Current discharging price                    |
| [`sensor.{name}_undercharge_energy_stored`](#energy-stored-by-region) (\*)           | kWh    | Energy in undercharge region                 |
| [`sensor.{name}_undercharge_power_charge`](#power-chargedischarge-by-region) (\*)    | kW     | Charging power in undercharge region         |
| [`sensor.{name}_undercharge_power_discharge`](#power-chargedischarge-by-region) (\*) | kW     | Discharging power in undercharge region      |
| [`sensor.{name}_undercharge_charge_price`](#chargedischarge-price-by-region) (\*)    | \$/kWh | Charging price in undercharge region         |
| [`sensor.{name}_undercharge_discharge_price`](#chargedischarge-price-by-region) (\*) | \$/kWh | Discharging price in undercharge region      |
| [`sensor.{name}_normal_energy_stored`](#energy-stored-by-region) (\*)                | kWh    | Energy in normal region                      |
| [`sensor.{name}_normal_power_charge`](#power-chargedischarge-by-region) (\*)         | kW     | Charging power in normal region              |
| [`sensor.{name}_normal_power_discharge`](#power-chargedischarge-by-region) (\*)      | kW     | Discharging power in normal region           |
| [`sensor.{name}_normal_charge_price`](#chargedischarge-price-by-region) (\*)         | \$/kWh | Charging price in normal region              |
| [`sensor.{name}_normal_discharge_price`](#chargedischarge-price-by-region) (\*)      | \$/kWh | Discharging price in normal region           |
| [`sensor.{name}_overcharge_energy_stored`](#energy-stored-by-region) (\*)            | kWh    | Energy in overcharge region                  |
| [`sensor.{name}_overcharge_power_charge`](#power-chargedischarge-by-region) (\*)     | kW     | Charging power in overcharge region          |
| [`sensor.{name}_overcharge_power_discharge`](#power-chargedischarge-by-region) (\*)  | kW     | Discharging power in overcharge region       |
| [`sensor.{name}_overcharge_charge_price`](#chargedischarge-price-by-region) (\*)     | \$/kWh | Charging price in overcharge region          |
| [`sensor.{name}_overcharge_discharge_price`](#chargedischarge-price-by-region) (\*)  | \$/kWh | Discharging price in overcharge region       |
| [`sensor.{name}_battery_power_balance`](#battery-power-balance)                      | \$/kW  | Marginal value of power at battery terminals |
| [`sensor.{name}_battery_max_charge_power`](#battery-max-charge-power)                | \$/kW  | Value of additional charging capacity        |
| [`sensor.{name}_battery_max_discharge_power`](#battery-max-discharge-power)          | \$/kW  | Value of additional discharging capacity     |

(\*) Only created when SOC sections are configured (undercharge/overcharge percentages and costs)

### Power Charge

The optimal charging power for this battery at each time period.

Values represent the average power during the period.
Positive values indicate energy flowing into the battery.
A value of 0 means the battery is not charging.

**Example**: A value of 3.2 kW means the battery is charging at an average rate of 3.2 kW during this period, limited by the configured max charge power or other system constraints.

### Power Discharge

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

### Charge Price

The effective cost per kWh to charge the battery at each time period.

This includes the base energy cost plus any applicable penalties (such as overcharge cost when charging above max SOC).
The price reflects all economic factors influencing charging decisions.

**Example**: A value of 0.12 means it costs \$0.12 per kWh to charge the battery at this time, considering all factors.

### Discharge Price

The effective revenue per kWh from discharging the battery at each time period.

This reflects the value of discharged energy minus any applicable costs (discharge cost for degradation, undercharge cost when discharging below min SOC).
Negative values indicate it costs money to discharge (total costs exceed value of discharged energy).

**Example**: A value of 0.25 means discharging 1 kWh provides \$0.25 of value at this time, after accounting for degradation costs.

### Region-Specific Sensors

When undercharge or overcharge sections are configured, HAEO creates region-specific sensors that break down energy, power, and pricing by SOC region.
These sensors help you understand how the battery operates across its extended range.

**Availability**: Only created when SOC sections are configured (undercharge/overcharge percentages and costs).

#### Energy Stored (by region)

Shows energy stored in each region: undercharge (below min SOC), normal (min to max SOC), or overcharge (above max SOC).
A nonzero value in undercharge or overcharge regions indicates the battery is operating outside its normal range.

#### Power Charge/Discharge (by region)

Shows power flowing into or out of each region.
Undercharge discharge incurs penalties; overcharge charge incurs penalties.
Moving toward normal operation (charging undercharge, discharging overcharge) has no penalty.

#### Charge/Discharge Price (by region)

Shows effective costs/revenue for each region.
Undercharge discharge price includes the undercharge penalty (may be negative, meaning discharge costs money).
Overcharge charge price includes the overcharge penalty.
Normal region prices reflect base costs only.

### Battery Energy Balance

The marginal value of stored energy across the optimization horizon.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price represents the value of having 1 kWh more energy stored at the end of the optimization horizon.
It captures the forward-looking value of stored energy for future time periods beyond the current optimization window.

**Interpretation**:

- **Positive value**: Having more energy stored at the end of the horizon would reduce future costs
- **Zero value**: Energy at the end of the horizon has no marginal value (unusual, may indicate horizon extends beyond meaningful forecasts)
- **Magnitude**: Higher values indicate stored energy is more valuable for future periods

**Example**: A value of 0.15 means having 1 kWh more stored energy at the end of the optimization horizon would save \$0.15 in future costs.

### Battery Max Charge Power

The marginal value of additional charging capacity.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the max charge power limit were increased by 1 kW at this time period.

**Interpretation**:

- **Zero value**: Not charging at maximum rate (charging is below the limit or not charging at all)
- **Positive value**: Charging at maximum rate and the limit is constraining
    - The value shows how much system cost would decrease per kW of additional charge capacity
    - Higher values indicate the charge power limit is causing significant cost increases
    - Suggests that more charge capacity would be valuable at this time

**Example**: A value of 0.12 means that if the battery could charge 1 kW faster, the total system cost would decrease by \$0.12 at this time period.

### Battery Max Discharge Power

The marginal value of additional discharging capacity.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the max discharge power limit were increased by 1 kW at this time period.

**Interpretation**:

- **Zero value**: Not discharging at maximum rate (discharging is below the limit or not discharging at all)
- **Positive value**: Discharging at maximum rate and the limit is constraining
    - The value shows how much system cost would decrease per kW of additional discharge capacity
    - Higher values indicate the discharge power limit is causing significant cost increases
    - Suggests that more discharge capacity would be valuable at this time

**Example**: A value of 0.18 means that if the battery could discharge 1 kW faster, the total system cost would decrease by \$0.18 at this time period.

---

Each sensor includes forecast attributes with future timestamped values for visualization and automations.

## When to Use Extended Operating Ranges

Configure undercharge and overcharge sections when you want to:

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

    [:material-arrow-right: Battery modeling](../../modeling/battery.md)

</div>
