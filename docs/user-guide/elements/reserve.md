# Reserve

A reserve keeps enough energy in your batteries to run your home through a grid outage.
You choose which loads to keep running, which generation keeps producing, which batteries hold the reserve, and how long an outage to cover.
HAEO then plans charging and discharging so the batteries hold that energy, unless using it is worth more than the cost you set for falling short.

You can add as many reserves as you like, for example one for essential loads over a long outage and another for the whole house over a short one.
To keep empty space for incoming generation instead, use [headroom](headroom.md), which works the same way in reverse.

## Configuration

| Field                                 | Type                                     | Required | Default | Description                                          |
| ------------------------------------- | ---------------------------------------- | -------- | ------- | ---------------------------------------------------- |
| **[Name](#name)**                     | String                                   | Yes      | -       | Unique identifier for this reserve                   |
| **[Loads](#loads)**                   | Elements                                 | No       | -       | Loads to keep running through an outage              |
| **[Generation](#generation)**         | Elements                                 | No       | -       | Generation that keeps producing through an outage    |
| **[Batteries](#batteries)**           | Elements                                 | Yes      | -       | Batteries that hold the reserve together             |
| **[Outage length](#outage-length)**   | Hours                                    | Yes      | 12      | How long an outage the reserve covers                |
| **[Extra reserve](#extra-reserve)**   | [sensor(s)](../forecasts-and-sensors.md) | Yes      | 0       | Energy to hold on top of what the loads need (kWh)   |
| **[Shortfall cost](#shortfall-cost)** | Price rate                               | Yes      | 0.05    | Holding cost per kWh short of the reserve (\$/kWh/h) |

## Name

Unique identifier for this reserve within your HAEO configuration.

**Examples**: "Backup", "Essential loads", "Storm reserve"

## Loads

The loads the reserve keeps running.
They count by the power HAEO plans for them, so a load whose timing HAEO chooses moves the reserve with its schedule.

## Generation

The generation that keeps producing during an outage, such as solar with an inverter that keeps running off grid.
Generation counts by what it is forecast to produce, and offsets the loads it overlaps.
A surplus counts toward a shortfall that comes after it within the outage, but not toward one before it.

## Batteries

The batteries that hold the reserve.
They hold it together, so a reserve needing 8 kWh is met by any mix of charge across them.
Each battery counts the energy it can deliver above its lowest allowed charge, after its discharge efficiency.

## Outage length

How long an outage the reserve covers.
At every point in the forecast, HAEO works out how much energy the loads would need, less the generation, over an outage starting then and lasting this long.
The reserve at that point is the largest amount the batteries would need to supply at any time during that outage.

Near the end of the forecast the outage is cut short where the forecast ends, so the reserve tapers off.

## Extra reserve

Energy to hold on top of what the loads need, in kWh.
Use a constant for a fixed buffer, or a sensor to change it over time, for example to raise the reserve ahead of a storm.

## Shortfall cost

The holding cost for each kWh the batteries fall short of the reserve, for every hour the shortfall lasts.
The cost is a rate that accrues over time, not a one-off charge per kWh used:

$$
\text{cost} = \text{rate} \times \text{kWh short} \times \text{hours short}
$$

With a shortfall cost of 0.02 \$/kWh/h, using 1 kWh of the reserve and leaving it short for 72 hours costs \$1.44, while refilling it after 3 hours costs only \$0.06.
A short dip that is refilled soon is cheap, so HAEO tends to use the reserve for short price spikes and refill it soon afterwards.

To choose a rate, decide what one kWh of reserve should cost if it stays used for a typical duration, then divide by that duration.
For example, if using the reserve for a day should cost about the same as a \$0.50/kWh price difference, use \$0.50/kWh ÷ 24 h ≈ 0.02 \$/kWh/h.
Typical values are 0.005-0.05 \$/kWh/h.
Set it high to treat the reserve as nearly untouchable.

The cost stops at the end of the forecast horizon, so a shortfall that starts near the end costs little.
Use the battery's [salvage value](battery.md#salvage-value) to value the energy left at the end of the horizon.

## Sensors created

| Sensor                  | Unit | Description                                                  |
| ----------------------- | ---- | ------------------------------------------------------------ |
| Required energy         | kWh  | Energy the batteries should hold at each point               |
| Available energy        | kWh  | Energy the batteries can deliver at each point               |
| Energy shortfall        | kWh  | How far the batteries fall short of the required energy      |
| Reserve state of charge | %    | The combined state of charge the batteries should stay above |

The reserve state of charge adds the batteries' lowest allowed charge to the required energy, stored after their discharge losses, as a share of their combined capacity.
With batteries of different efficiencies it uses their capacity-weighted average efficiency.
The [forecast card](../lovelace-card.md) draws it as a line alongside your batteries' state of charge.

## Next steps

<div class="grid cards" markdown>

- :material-battery:{ .lg .middle } **Configure batteries**

    ---

    Set up the batteries that hold the reserve.

    [:material-arrow-right: Battery configuration](battery.md)

- :material-battery-lock:{ .lg .middle } **Backup reserve walkthrough**

    ---

    Set up a reserve step by step and see what to expect.

    [:material-arrow-right: Reserve and headroom walkthrough](../../walkthroughs/reserve-and-headroom.md)

- :material-calculator:{ .lg .middle } **How the reserve is modeled**

    ---

    See how HAEO turns the reserve into optimization constraints.

    [:material-arrow-right: Reserve modeling](../../modeling/device-layer/reserve.md)

</div>
