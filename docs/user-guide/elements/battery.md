# Battery

Batteries are energy storage devices that can charge (store energy) and discharge (release energy).
HAEO optimizes when to charge and discharge based on electricity prices, solar availability, and economic preferences.

Internally, HAEO represents each battery as a single storage element between its min and max charge.

For mathematical details, see [Battery Modeling](../../modeling/device-layer/battery.md).

## Configuration

### Overview

A battery in HAEO represents:

- **Energy storage** with a maximum capacity (kWh)
- **Power limits** for charging and discharging (kW)
- **State of Charge (SOC)** tracking via a Home Assistant sensor
- **Charge and discharge efficiency** losses during power conversion
- **Operating range** limits (min/max SOC)

### Configuration process

Battery configuration uses a sectioned flow where you enter the name, connection, and configure each input field.
For each field, select "Entity" to link to a sensor, "Constant" to enter a fixed value, or "None" for optional fields you don't need.

Fields configured with "Constant" create input entities that you can adjust at runtime without reconfiguring.
Optional fields set to "None" are omitted from the optimization entirely.

## Configuration fields

| Field                                                        | Type       | Required | Default | Description                                                |
| ------------------------------------------------------------ | ---------- | -------- | ------- | ---------------------------------------------------------- |
| **[Name](#name)**                                            | String     | Yes      | -       | Unique identifier (e.g., "Main Battery", "Garage Battery") |
| **[Capacity](#capacity)**                                    | Energy     | Yes      | -       | Total energy storage capacity                              |
| **[Current Charge Percentage](#current-charge-percentage)**  | Percentage | Yes      | -       | Home Assistant sensor reporting current SOC (0-100%)       |
| **[Min Charge Percentage](#min-and-max-charge-percentage)**  | Percentage | No       | 0       | Lowest SOC the battery is planned to reach (%)             |
| **[Max Charge Percentage](#min-and-max-charge-percentage)**  | Percentage | No       | 100     | Highest SOC the battery is planned to reach (%)            |
| **[Discharge efficiency](#charge-and-discharge-efficiency)** | Percentage | No       | 95      | Efficiency when discharging (battery to network)           |
| **[Charge efficiency](#charge-and-discharge-efficiency)**    | Percentage | No       | 95      | Efficiency when charging (network to battery)              |
| **[Max Charge Power](#max-charge-and-discharge-power)**      | Power      | No       | -       | Maximum charging power                                     |
| **[Max Discharge Power](#max-charge-and-discharge-power)**   | Power      | No       | -       | Maximum discharging power                                  |
| **[Salvage Value](#salvage-value)**                          | Price      | No       | 0       | Value assigned to stored energy at the horizon end         |
| **[Limit cost](#limit-cost)**                                | Price rate | Yes      | 100     | Holding cost per kWh outside the min and max charge        |

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

Set the range the battery operates in.
HAEO plans the battery to stay between these limits.
If you leave them unset, HAEO allows the full 0-100% range.
A typical starting point is 10-90% unless your manufacturer recommends otherwise.

HAEO treats these as limits it does not cross while it has any choice.
Internally, each kWh past a limit costs the [limit cost](#limit-cost), 100 \$/kWh for every hour it stays there by default, far more than any price difference the battery could earn from.
That keeps a plan possible when the battery already sits outside its limits, for example when it reads 5% with a 10% min charge.
HAEO then brings it back inside the range as quickly as it can rather than failing to optimize.

To let the battery go past a limit when it pays off, set the limit to the furthest level it may reach and add a [buffer](buffer.md) at the level it should normally keep.
For example, a min charge of 5% and a reserve buffer at a level of 10% with a holding cost behave like a preferred floor of 10% that HAEO dips below for a large enough price spike.

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

### Salvage value

Value in \$/kWh assigned to stored energy at the end of the optimization horizon.
This prevents the optimizer from draining the battery to zero when future value is still expected.

**Default**: 0 \$/kWh (no terminal value)

**How it works**: The optimizer credits the final stored energy by this amount.
Higher values encourage retaining energy for periods beyond the horizon.

### Limit cost

Holding cost in \$/kWh/h for each kWh outside the [min and max charge](#min-and-max-charge-percentage), for every hour it stays there.
It is in the collapsed **Advanced** section and defaults to 100 \$/kWh/h.

Keep it far above any price the battery could earn from, so the limits act as hard limits.
Raise it if your prices can spike high enough to make crossing a limit worthwhile for a short while.
Very large values make the optimization numerically harder, so stay within a few thousand.
It cannot be negative, and a sensor that reports a negative value stops the optimization with an error.

## Configuration examples

### Basic battery configuration

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

### Battery with an extended operating range

Earlier versions of HAEO configured undercharge and overcharge ranges on the battery.
These ranges are now [buffers](buffer.md) for the battery.
When HAEO updated, it moved each configured range across field for field:
the outer undercharge or overcharge percentage became the battery's min or max charge,
and the old min or max charge became the level of a reserve or headroom buffer with the old cost as its shortfall cost.

To let the battery reach 5-95% while preferring 10-90%:

1. Set the battery's **Min Charge Percentage** to 5% and **Max Charge Percentage** to 95%.
2. Add a reserve buffer with the battery as its storage, no loads or generation, a level of 10%, and a shortfall cost such as 0.03 \$/kWh/h.
3. Add a headroom buffer with the battery as its storage, no loads or generation, a level of 90%, and a shortfall cost such as 0.02 \$/kWh/h.

HAEO then uses the outer 5% at each end only when the price difference outweighs the holding cost for as long as the battery stays there.

### Input entities

Each configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                                     | Unit     | Description                          |
| ----------------------------------------- | -------- | ------------------------------------ |
| `number.{name}_capacity`                  | kWh      | Battery storage capacity             |
| `number.{name}_initial_charge_percentage` | %        | Current state of charge from sensor  |
| `number.{name}_min_charge_percentage`     | %        | Minimum SOC                          |
| `number.{name}_max_charge_percentage`     | %        | Maximum SOC                          |
| `number.{name}_max_power_target_source`   | kW       | Maximum charging power               |
| `number.{name}_max_power_source_target`   | kW       | Maximum discharging power            |
| `number.{name}_efficiency_source_target`  | %        | Discharge efficiency (if configured) |
| `number.{name}_efficiency_target_source`  | %        | Charge efficiency (if configured)    |
| `number.{name}_charge_cost`               | \$/kWh   | Charge cost (if configured)          |
| `number.{name}_discharge_cost`            | \$/kWh   | Discharge cost (if configured)       |
| `number.{name}_charge_limit_cost`         | \$/kWh/h | Limit cost                           |

The charge and discharge cost inputs are surfaced from the [policy](../../walkthroughs/power-policies.md) rules they create.
They appear on both the battery device and the Policies device; editing either updates the same stored value.

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors created

### Sensor summary

A Battery element creates a single device in Home Assistant:

- **Battery device** (`{name}`): Always created with total power, energy, SOC, and shadow price sensors

### Battery device sensors

These sensors appear on the battery device:

| Sensor                                                       | Unit   | Description                     |
| ------------------------------------------------------------ | ------ | ------------------------------- |
| [`sensor.{name}_power_charge`](#charge-power)                | kW     | Charging power                  |
| [`sensor.{name}_power_discharge`](#discharge-power)          | kW     | Discharging power               |
| [`sensor.{name}_energy_stored`](#energy-stored)              | kWh    | Current energy level            |
| [`sensor.{name}_state_of_charge`](#state-of-charge-sensor)   | %      | State of charge percentage      |
| [`sensor.{name}_power_balance`](#power-balance-shadow-price) | \$/kWh | Marginal value of energy stored |

### Charge power

The optimal charging power for this battery at each time period.

Values represent the average power during the period, measured at the battery terminals.
Positive values indicate energy flowing into the battery.
A value of 0 means the battery is not charging.
The energy stored rises by this power less the charge efficiency loss.

**Example**: A value of 3.2 kW means the battery is charging at an average rate of 3.2 kW during this period, limited by the configured max charge power or other system constraints.

### Discharge power

The optimal discharging power for this battery at each time period.

Values represent the average power during the period, measured at the battery terminals.
Positive values indicate energy flowing out of the battery.
A value of 0 means the battery is not discharging.
The energy stored falls by this power plus the discharge efficiency loss.

**Example**: A value of 2.5 kW means the battery is discharging at an average rate of 2.5 kW during this period, providing power to loads or exporting to the grid.

### Energy stored

The total energy stored in the battery.

This represents the absolute energy level in kWh.
Multiply by 100 and divide by capacity to get state of charge percentage.

**Example**: A value of 12.5 kWh in a 15 kWh battery means 83.3% state of charge.

### State of charge sensor

The battery's state of charge as a percentage (0-100%).

This is calculated from the energy stored divided by total capacity.
Provides a convenient percentage view of the battery level.

**Example**: A value of 75% means the battery has 75% of its capacity available.

### Power balance shadow price

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

## How it works internally

HAEO models batteries using a single storage element with separate charge and discharge connections:

1. **Battery element**: Tracks stored energy between empty and full, held between the min and max charge by a steep holding cost
2. **Network connections**: Separate charge and discharge connections apply efficiency and power limits

[Buffers](buffer.md) add requirements on top of the battery, measured from their level or from its min and max charge.

## Troubleshooting

### Battery not charging/discharging

If your battery remains idle:

1. **Check price forecasts**: HAEO needs price variation to optimize.
    See the [forecasts page](../forecasts-and-sensors.md) for details.
2. **Verify SOC sensor**: Ensure it's reporting correctly
3. **Review constraints**: Too-tight SOC limits may prevent operation
4. **Check connections**: Battery must be [connected](connections.md) to the network

### Unrealistic SOC predictions

If forecast SOC values seem wrong:

1. **Verify capacity**: Ensure capacity matches your actual battery
2. **Check efficiency**: Confirm charge and discharge efficiencies are set (use the same value in both directions if you only have a round-trip figure)
3. **Review power limits**: Ensure they match your battery rating

### SOC sensor issues

Common problems:

- **Not updating**: Check sensor entity in Developer Tools → States
- **Wrong units**: Must be 0-100%, not 0-1 decimal
- **Incorrect values**: Calibrate battery management system

See the [troubleshooting guide](../troubleshooting.md) for more solutions.

## Multiple batteries

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
