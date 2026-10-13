# Battery

Batteries are energy storage devices that can charge (store energy) and discharge (release energy).
HAEO optimizes when to charge and discharge based on electricity prices, solar availability, and economic preferences.

Internally, HAEO represents a battery as a single storage element between hard minimum and maximum charge levels.
Preferences inside that range are holding costs: a cost for each kWh held above or below a state of charge, for each hour it stays there.

For mathematical details, see [Battery Modeling](../../modeling/device-layer/battery.md).

## Configuration

### Overview

A battery in HAEO represents:

- **Energy storage** with a maximum capacity (kWh)
- **Power limits** for charging and discharging (kW)
- **State of Charge (SOC)** tracking via a Home Assistant sensor
- **Charge and discharge efficiency** losses during power conversion
- **Hard operating limits** on the state of charge (min/max SOC)
- **Operating range preferences** guided by [holding costs](#holding-costs)

### Configuration process

Battery configuration uses a sectioned flow where you enter the name, connection, and configure each input field.
For each field, select "Entity" to link to a sensor, "Constant" to enter a fixed value, or "None" for optional fields you don't need.
Holding costs are added afterwards, by reconfiguring the battery.

Fields configured with "Constant" create input entities that you can adjust at runtime without reconfiguring.
Optional fields set to "None" are omitted from the optimization entirely.

## Configuration Fields

| Field                                                        | Type       | Required | Default | Description                                                |
| ------------------------------------------------------------ | ---------- | -------- | ------- | ---------------------------------------------------------- |
| **[Name](#name)**                                            | String     | Yes      | -       | Unique identifier (e.g., "Main Battery", "Garage Battery") |
| **[Capacity](#capacity)**                                    | Energy     | Yes      | -       | Total energy storage capacity                              |
| **[Current Charge Percentage](#current-charge-percentage)**  | Percentage | Yes      | -       | Home Assistant sensor reporting current SOC (0-100%)       |
| **[Min Charge Percentage](#min-and-max-charge-percentage)**  | Percentage | No       | 0       | Lowest SOC the battery may reach (%)                       |
| **[Max Charge Percentage](#min-and-max-charge-percentage)**  | Percentage | No       | 100     | Highest SOC the battery may reach (%)                      |
| **[Discharge efficiency](#charge-and-discharge-efficiency)** | Percentage | No       | 95      | Efficiency when discharging (battery to network)           |
| **[Charge efficiency](#charge-and-discharge-efficiency)**    | Percentage | No       | 95      | Efficiency when charging (network to battery)              |
| **[Max Charge Power](#max-charge-and-discharge-power)**      | Power      | No       | -       | Maximum charging power                                     |
| **[Max Discharge Power](#max-charge-and-discharge-power)**   | Power      | No       | -       | Maximum discharging power                                  |
| **[Salvage Value](#salvage-value)**                          | Price      | No       | 0       | Value assigned to stored energy at the horizon end         |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

!!! tip "Charge and discharge pricing"

    To apply a per-kWh cost or incentive for charging or discharging, use a [Power Policy](../../walkthroughs/power-policies.md).
    Policies let you set directional pricing rules between elements, replacing the older per-element charge/discharge price fields.

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

Set the range the battery's state of charge must stay within.
These are **hard limits**: HAEO never plans to charge above the maximum or discharge below the minimum.
If you leave them unset, HAEO allows the full 0-100% range.

To prefer a narrower range without forbidding the rest, keep these limits wide and add [holding costs](#holding-costs) inside them.
For example, a minimum of 5% with a holding cost below 10% lets HAEO use the 5-10% band when it pays to, rather than never.

### Charge and discharge efficiency

Enter separate charge and discharge efficiencies as percentages (0-100).
Charge efficiency applies when power flows from the network into the battery.
Discharge efficiency applies when power flows from the battery into the network.
Efficiency is the loss between the battery terminals and the energy stored in the cells.
Charging 10 kW at 95% efficiency stores 9.5 kWh per hour, and discharging 10 kW at 95% efficiency draws about 10.5 kWh per hour from storage.
If you only have a round-trip figure, use the same value for both directions or approximate a symmetric value with $\sqrt{\text{round-trip}}$.
Most modern lithium batteries have efficiencies in the 95-98% range, while older chemistries may be lower.
Refer to your battery or inverter specifications for the most appropriate values.

### Max charge and discharge power

Add limits based on your battery's charge/discharge rating.
Leave the fields blank when no practical limit applies.

Both limits apply at the battery terminals, where battery management systems usually measure power.
A 5 kW discharge limit means at most 5 kW leaves the battery terminals, whatever the discharge efficiency.

!!! note

    Use the battery charge/discharge rating, not the inverter rating.
    Hybrid inverters often have separate ratings for battery power and inverter output power.

### Salvage Value

Value in \$/kWh assigned to stored energy at the end of the optimization horizon.
This prevents the optimizer from draining the battery to zero when future value is still expected.

**Default**: 0 \$/kWh (no terminal value)

**How it works**: The optimizer credits the final stored energy by this amount.
Higher values encourage retaining energy for periods beyond the horizon.

## Holding costs

A holding cost charges a rate for each kWh the battery holds above or below a state of charge, for every hour it stays there.
It makes HAEO prefer one side of that state of charge without forbidding the other side.
A battery can have any number of holding costs, and their costs add up where they overlap.

To add one, reconfigure the battery and choose **Add a holding cost**.
To change or remove one, reconfigure the battery and choose **Edit or delete a holding cost**.

| Field                                       | Type         | Description                                                |
| ------------------------------------------- | ------------ | ---------------------------------------------------------- |
| **Name**                                    | String       | Names the holding cost and its input entities              |
| **Enabled**                                 | Boolean      | Whether the holding cost applies; creates a switch entity  |
| **[Applies to energy](#applies-to-energy)** | Above, below | Which side of the state of charge the cost applies to      |
| **[State of charge](#state-of-charge)**     | Percentage   | State of charge the cost is measured from (%)              |
| **[Cost](#cost)**                           | Price rate   | Cost per kWh past the state of charge, per hour (\$/kWh/h) |

### Applies to energy

**Below** charges for energy missing below the state of charge, which keeps a reserve.
**Above** charges for energy stored above the state of charge, which keeps headroom.

### State of charge

The state of charge the cost is measured from, as a percentage of capacity.
Like the other inputs it can be a constant or an entity, so a forecast sensor can move it over time, for example to hold a larger reserve overnight.

A holding cost only matters between the [min and max charge percentage](#min-and-max-charge-percentage).
A state of charge outside them never has energy past it.

### Cost

A rate in \$/kWh/h (your currency per kWh per hour).
The cost accrues over time, not once per kWh moved.
At every point in the forecast, HAEO measures how many kWh the battery holds past the state of charge and charges this rate for each hour that lasts:

$$
\text{cost} = \text{rate} \times \text{kWh past the state of charge} \times \text{hours held}
$$

**Worked example**: With a cost of 0.02 \$/kWh/h below 10%, discharging 1 kWh below 10% and leaving it there for 72 hours costs 0.02 \$/kWh/h × 1 kWh × 72 h = \$1.44.
Refilling that kWh after 3 hours instead costs only \$0.06.

**How it works**: Going past the state of charge is worthwhile when the value of doing so exceeds the rate multiplied by how long the battery stays there.
A short dip into a reserve that is refilled soon is cheap, while a deficit that lasts until the end of the forecast horizon is expensive.
A reserve therefore tends to be used for short price spikes and refilled soon afterwards.
Headroom works the same way: HAEO fills the top of the battery shortly before it can use that energy, such as before an evening export peak, rather than early in the day.

**Setting the cost**: Decide what one kWh past the state of charge should cost if it stays there for a typical duration, then divide by that duration.

| Cost           | Held 1 hour | Held 12 hours | Held 24 hours | Held 72 hours |
| -------------- | ----------- | ------------- | ------------- | ------------- |
| 0.005 \$/kWh/h | \$0.005     | \$0.06        | \$0.12        | \$0.36        |
| 0.02 \$/kWh/h  | \$0.02      | \$0.24        | \$0.48        | \$1.44        |
| 0.05 \$/kWh/h  | \$0.05      | \$0.60        | \$1.20        | \$3.60        |

Typical values are 0.005-0.05 \$/kWh/h.
For example, if using a reserve for a day should cost about the same as a \$0.50/kWh price difference, use \$0.50/kWh ÷ 24 h ≈ 0.02 \$/kWh/h.

Compare the cost over your planning horizon with the price differences HAEO can exploit.
If the rate multiplied by the hours spent past the state of charge is smaller than the money gained, HAEO treats that energy as normal capacity.
With a 72-hour horizon, a rate of 0.0015 \$/kWh/h costs at most about \$0.11 per kWh, which is less than a typical gap between import and export prices.

The cost stops at the end of the forecast horizon, so energy that goes past the state of charge near the end costs little.
Use the [salvage value](#salvage-value) to value the energy left in the battery at the end of the horizon.

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
| **Discharge Efficiency**      | 99%                |
| **Charge Efficiency**         | 99%                |
| **Max Charge Power**          | 6 kW               |
| **Max Discharge Power**       | 6 kW               |

This creates a battery that operates in the 20-90% range with no economic penalties for staying within that range.

### Battery with a reserve and headroom

A battery that may use 5-95% of its capacity, but prefers to stay between 10% and 90%:

| Field                         | Example Value      |
| ----------------------------- | ------------------ |
| **Name**                      | Main Battery       |
| **Capacity**                  | 15 kWh             |
| **Current Charge Percentage** | sensor.battery_soc |
| **Min Charge Percentage**     | 5%                 |
| **Max Charge Percentage**     | 95%                |

Then reconfigure the battery and add two holding costs:

| Name     | Applies to energy | State of charge | Cost          |
| -------- | ----------------- | --------------- | ------------- |
| Reserve  | Below             | 10%             | 0.03 \$/kWh/h |
| Headroom | Above             | 90%             | 0.02 \$/kWh/h |

In this example:

- **5-10%**: available with a holding cost of \$0.03/kWh for each hour, or \$0.72/kWh per day
- **10-90%**: preferred operation, with no holding cost
- **90-95%**: available with a holding cost of \$0.02/kWh for each hour, or \$0.48/kWh per day
- The higher reserve cost reflects greater degradation risk at low SOC
- HAEO uses the outer bands only when prices justify the holding cost for as long as the battery stays there

### Input Entities

Each configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                                          | Unit     | Description                                     |
| ---------------------------------------------- | -------- | ----------------------------------------------- |
| `number.{name}_capacity`                       | kWh      | Battery storage capacity                        |
| `number.{name}_initial_charge_percentage`      | %        | Current state of charge from sensor             |
| `number.{name}_min_charge_percentage`          | %        | Lowest SOC the battery may reach                |
| `number.{name}_max_charge_percentage`          | %        | Highest SOC the battery may reach               |
| `number.{name}_max_power_target_source`        | kW       | Maximum charging power                          |
| `number.{name}_max_power_source_target`        | kW       | Maximum discharging power                       |
| `number.{name}_efficiency_source_target`       | %        | Discharge efficiency (if configured)            |
| `number.{name}_efficiency_target_source`       | %        | Charge efficiency (if configured)               |
| `number.{name}_{holding_cost}_state_of_charge` | %        | State of charge a holding cost is measured from |
| `number.{name}_{holding_cost}_cost`            | \$/kWh/h | Holding cost rate                               |
| `number.{name}_charge_cost`                    | \$/kWh   | Charge cost (if configured)                     |
| `number.{name}_discharge_cost`                 | \$/kWh   | Discharge cost (if configured)                  |

Each holding cost also creates a `switch.{name}_{holding_cost}_enabled` entity that turns it on or off, for example from an automation that keeps a larger reserve when a storm is forecast.

The charge and discharge cost inputs are surfaced from the [policy](../../walkthroughs/power-policies.md) rules they create.
They appear on both the battery device and the Policies device; editing either updates the same stored value.

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Battery element creates a single device in Home Assistant:

- **Battery device** (`{name}`): Always created with total power, energy, SOC, and shadow price sensors

### Battery Device Sensors

These sensors appear on the battery device:

| Sensor                                                       | Unit   | Description                     |
| ------------------------------------------------------------ | ------ | ------------------------------- |
| [`sensor.{name}_power_charge`](#charge-power)                | kW     | Charging power                  |
| [`sensor.{name}_power_discharge`](#discharge-power)          | kW     | Discharging power               |
| [`sensor.{name}_energy_stored`](#energy-stored)              | kWh    | Current energy level            |
| [`sensor.{name}_state_of_charge`](#state-of-charge-sensor)   | %      | State of charge percentage      |
| [`sensor.{name}_power_balance`](#power-balance-shadow-price) | \$/kWh | Marginal value of energy stored |

### Charge Power

The optimal charging power for this battery at each time period.

Values represent the average power during the period, measured at the battery terminals.
Positive values indicate energy flowing into the battery.
A value of 0 means the battery is not charging.
The energy stored rises by this power less the charge efficiency loss.

**Example**: A value of 3.2 kW means the battery is charging at an average rate of 3.2 kW during this period, limited by the configured max charge power or other system constraints.

### Discharge Power

The optimal discharging power for this battery at each time period.

Values represent the average power during the period, measured at the battery terminals.
Positive values indicate energy flowing out of the battery.
A value of 0 means the battery is not discharging.
The energy stored falls by this power plus the discharge efficiency loss.

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

The marginal value of energy stored in the battery, measured inside the charge and discharge efficiency.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

It shows how much the total system cost would change if one more kWh were held in the battery at that time.

**Interpretation**:

- **Positive value**: Energy in the battery has value (usually during discharge periods)
- **Negative value**: Holding more energy would increase costs (usually during charging periods)
- **Magnitude**: Higher absolute values indicate stored energy is more valuable to the system

**Example**: A value of 0.15 means one more kWh held in the battery at that time would save \$0.15.

---

Each sensor includes forecast attributes with future timestamped values for visualization and automations.

## How It Works Internally

HAEO models batteries using a single storage element with a holding cost element for each holding cost:

1. **Battery element**: Tracks stored energy between the min and max charge percentage
2. **Holding costs**: Charge for energy held past each holding cost's state of charge
3. **Network connections**: Separate charge and discharge connections apply efficiency and power limits

This architecture allows HAEO to:

- Never plan outside the min and max charge percentage
- Prefer staying on one side of a holding cost's state of charge
- Go past it when prices justify the holding cost for as long as the battery stays there

## When to use holding costs

Add holding costs when you want to:

1. **Keep a reserve for extreme conditions**: Let the battery dip into a reserve when grid prices make it worthwhile, such as a price spike, and refill it soon afterwards.

2. **Model degradation economics**: Reflect the cost of battery wear from time spent at very high or very low SOC.
    HAEO trades off grid savings against that cost.

3. **Capture opportunistic value**: Let the battery charge into its headroom when excess solar is available or grid prices are negative, while still discouraging routinely sitting full.

4. **Flexible protection**: Keep conservative normal operation (for example 10-90%) while allowing economically justified excursions (for example 5-95%) rather than imposing hard limits.

**When not to use holding costs**:

- When the hard limits alone describe how you want the battery used
- When you want an absolute limit that is never crossed (use the min and max charge percentage instead)
- When you cannot estimate a cost relative to your grid price volatility

**Key difference from hard limits**: A holding cost creates an economic trade-off, not an absolute constraint.
The battery goes past it when conditions justify it, providing flexibility while still protecting against unnecessary wear.

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
2. **Check efficiency**: Confirm charge and discharge efficiencies are set (use the same value in both directions if you only have a round-trip figure)
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
2. Connect each battery to the network (typically via a [junction](junction.md))
3. HAEO will optimize all batteries together

This allows HAEO to:

- Balance charging across batteries
- Optimize total system cost
- Handle different battery characteristics

## Next steps

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
