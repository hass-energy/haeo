# Buffer

A buffer tells HAEO how much your batteries should hold back from saving money.
It comes in two kinds:

- **A reserve** keeps energy in your batteries to run your home through a grid outage.
- **Headroom** keeps empty space in your batteries to absorb the generation that is coming.

You choose which loads and generation the buffer covers, which batteries hold it, and how far ahead it looks.
HAEO then plans charging and discharging so the batteries hold the buffer, unless going past it is worth more than the cost you set for falling short.

Use a reserve when your inverter can run some or all of your home off grid, when outages are likely, or when some loads matter more than others.
Use headroom when:

- **Your solar cannot be curtailed**: once the house is covered and exports are at their limit, the battery is the only place left for the surplus.
- **You want to look after the battery**: many batteries last longer when they spend less time near 100%, and headroom keeps it below full unless filling it pays.
- **You take part in a grid support program** that asks you to keep capacity free to absorb power when the grid needs it.

You can add as many buffers as you like, for example a reserve for essential loads over a long outage and another for the whole house over a short one.

## Configuration

| Field                                 | Type                                     | Required | Default | Description                                                      |
| ------------------------------------- | ---------------------------------------- | -------- | ------- | ---------------------------------------------------------------- |
| **[Name](#name)**                     | String                                   | Yes      | -       | Unique identifier for this buffer                                |
| **[Kind](#kind)**                     | Reserve or headroom                      | Yes      | -       | Whether the buffer keeps energy or empty space                   |
| **[Loads](#loads)**                   | Elements                                 | No       | -       | Loads the buffer covers                                          |
| **[Generation](#generation)**         | Elements                                 | No       | -       | Generation the buffer covers                                     |
| **[Batteries](#batteries)**           | Elements                                 | Yes      | -       | Batteries that hold the buffer together                          |
| **[Window](#window)**                 | [sensor](../forecasts-and-sensors.md)    | Yes      | 12      | How far ahead the buffer looks (hours)                           |
| **[Level](#level)**                   | [sensor(s)](../forecasts-and-sensors.md) | No       | -       | Charge level the buffer is measured from (%)                     |
| **[Shortfall cost](#shortfall-cost)** | Price rate                               | Yes      | 0.05    | Holding cost per stored kWh past the buffer, per hour (\$/kWh/h) |

## Name

Unique identifier for this buffer within your HAEO configuration.

**Examples**: "Backup", "Essential loads", "Solar headroom", "Battery care"

## Kind

- **Reserve** keeps the batteries charged enough: the buffer is energy to deliver.
- **Headroom** keeps them empty enough: the buffer is space to absorb.

The other fields mean the same for both kinds, mirrored.

## Loads

The loads the buffer covers.
A reserve keeps them running through an outage, and for headroom they use some of the generation before it reaches the batteries.
Loads count by the power HAEO plans for them, so a load whose timing HAEO chooses moves the buffer with its schedule.
A load that HAEO plans to leave short, such as an EV trip it expects you to top up publicly, still counts by the energy it needs, so leaving it short cannot shrink the buffer.

## Generation

The generation the buffer covers.
For a reserve it is generation that keeps producing during an outage, such as solar with an inverter that keeps running off grid.
For headroom it is the generation the batteries should have room for.

Generation counts by what it is forecast to produce, not what HAEO plans to use.
That way curtailing solar in the plan cannot remove the need for room it was meant to guarantee.
Within a window, a surplus offsets a need that comes after it, but not one before it.

## Batteries

The batteries that hold the buffer, which can be any element that stores energy, such as a battery or a battery section.
They hold it together, so a buffer needing 8 kWh is met by any mix of charge or empty space across them.

## Window

How far ahead the buffer looks: the outage to cover for a reserve, or the generation to make room for with headroom.
At every point in the forecast, HAEO works out how much the loads would need less the generation, or the generation would produce less the loads, over a window starting then.
The buffer at that point is the largest amount the batteries would need to supply or absorb at any time in that window.

Near the end of the forecast the window is cut short where the forecast ends, so the buffer tapers off.

If your generation can produce far more in a few hours than your batteries hold, a long headroom window asks for an empty battery.
Choose one where the required space stays well below your battery's capacity.

The window can come from a sensor, read as its current value for the whole plan.
Point it at a helper to lengthen the outage a reserve covers while a storm warning is active, for example.
Sensors reporting seconds, minutes, or days are converted to hours.

## Level

The charge level the buffer is measured from, as a percentage of the batteries' combined capacity.
A reserve keeps the batteries above it, plus whatever the loads need, and headroom keeps them below it, less whatever the generation needs.
Leave it unset to measure from the batteries' [min or max charge](battery.md#min-and-max-charge-percentage).

A level never reaches past a battery's own min or max charge: a reserve level below the min charge is measured from the min charge, and a headroom level above the max charge from the max charge.

With no loads or generation, a buffer holds the batteries on one side of its level:

- **To keep a floor HAEO can dip below**, add a reserve with a level such as 15% and a moderate shortfall cost.
- **To look after the battery**, add headroom with a level such as 90% and a low shortfall cost.
- **For a grid support program**, add headroom with a level that leaves the committed capacity free and a high shortfall cost.
    Drive the level from a sensor that is 100% outside the program's hours if the commitment does not cover the whole day.

## Shortfall cost

The holding cost for each kWh stored in the batteries past the buffer, for every hour it stays there.
It cannot be negative, and a sensor that reports a negative value stops the optimization with an error.
The cost is a rate that accrues over time, not a one-off charge per kWh used:

$$
\text{cost} = \text{rate} \times \text{kWh short} \times \text{hours short}
$$

With a shortfall cost of 0.02 \$/kWh/h, using 1 kWh of a reserve and leaving it short for 72 hours costs \$1.44, while refilling it after 3 hours costs only \$0.06.
A short dip that is refilled soon is cheap, so HAEO tends to use a reserve for short price spikes and refill it soon afterwards.
Headroom works the same way: a short spell full that is drained soon is cheap, while a battery left full is expensive.

To choose a rate, decide what one kWh of buffer should cost if it stays used for a typical duration, then divide by that duration.
For example, if using the reserve for a day should cost about the same as a \$0.50/kWh price difference, use \$0.50/kWh ÷ 24 h ≈ 0.02 \$/kWh/h.
Typical values are 0.005-0.05 \$/kWh/h.
Set it high to treat the buffer as nearly untouchable.

The cost stops at the end of the forecast horizon, so a shortfall that starts near the end costs little.
Use the battery's [salvage value](battery.md#salvage-value) to value the energy left at the end of the horizon.

## Input entities

Each field you configure creates an input entity on the buffer's device.
Input entities appear as Number entities with the `config` entity category.
Their IDs combine the buffer's name with the entity's name, so a buffer named "Backup Reserve" has `number.backup_reserve_window`.

| Input                          | Unit     | Description           |
| ------------------------------ | -------- | --------------------- |
| `number.{name}_window`         | h        | Window                |
| `number.{name}_level`          | %        | Level (if configured) |
| `number.{name}_shortfall_cost` | \$/kWh/h | Shortfall cost        |

A field set to "Constant" can be adjusted from its input entity at runtime.

## Sensors created

| Sensor                                 | Unit | Description                                                                |
| -------------------------------------- | ---- | -------------------------------------------------------------------------- |
| `sensor.{name}_required_energy`        | kWh  | Energy the batteries should hold or keep free past the level at each point |
| `sensor.{name}_available_energy`       | kWh  | Energy the batteries hold or keep free past the level at each point        |
| `sensor.{name}_energy_shortfall`       | kWh  | How far the batteries fall short of the required energy                    |
| `sensor.{name}_buffer_state_of_charge` | %    | The combined state of charge the batteries should stay above or below      |

The energy sensors measure energy stored in the batteries, so they compare directly with the batteries' own stored energy.
The buffer state of charge adds the required energy to the level for a reserve, or takes it away for headroom, as a share of the batteries' combined capacity.
The [forecast card](../lovelace-card.md) draws it as a dotted line alongside your batteries' state of charge.

## Next steps

<div class="grid cards" markdown>

- :material-battery:{ .lg .middle } **Configure batteries**

    ---

    Set up the batteries that hold the buffer.

    [:material-arrow-right: Battery configuration](battery.md)

- :material-battery-lock:{ .lg .middle } **Buffers walkthrough**

    ---

    Set up a reserve and headroom step by step and see the plan change.

    [:material-arrow-right: Buffers walkthrough](../../walkthroughs/buffers.md)

- :material-calculator:{ .lg .middle } **How buffers are modeled**

    ---

    See how HAEO turns a buffer into optimization constraints.

    [:material-arrow-right: Buffer modeling](../../modeling/device-layer/buffer.md)

</div>
