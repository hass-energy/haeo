# Headroom

Headroom keeps enough empty space in your batteries to absorb the generation that is coming.
You choose which generation to make room for, which loads use some of it first, which batteries keep the room, and how far ahead to look.
HAEO then plans charging and discharging so the batteries have that room, unless filling them is worth more than the cost you set for falling short.

Headroom is the mirror image of a [reserve](reserve.md): a reserve keeps energy for what your loads will need, and headroom keeps space for what your generation will produce.
Use it when:

- **Your solar cannot be curtailed**: once the house is covered and exports are at their limit, the battery is the only place left for the surplus.
- **You want to look after the battery**: keeping it off 100% can extend its life, and a fixed headroom keeps it below full unless filling it pays.
- **You take part in a grid support program** that asks you to keep capacity free to absorb power when the grid needs it.

## Configuration

| Field                                 | Type                                     | Required | Default | Description                                           |
| ------------------------------------- | ---------------------------------------- | -------- | ------- | ----------------------------------------------------- |
| **[Name](#name)**                     | String                                   | Yes      | -       | Unique identifier for this headroom                   |
| **[Loads](#loads)**                   | Elements                                 | No       | -       | Loads that use some of the generation first           |
| **[Generation](#generation)**         | Elements                                 | No       | -       | Generation the batteries should have room for         |
| **[Batteries](#batteries)**           | Elements                                 | Yes      | -       | Batteries that keep the headroom together             |
| **[Look-ahead](#look-ahead)**         | Hours                                    | Yes      | 12      | How far ahead to keep room for                        |
| **[Extra headroom](#extra-headroom)** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | 0       | Empty space to keep on top (kWh)                      |
| **[Shortfall cost](#shortfall-cost)** | Price rate                               | Yes      | 0.05    | Holding cost per kWh short of the headroom (\$/kWh/h) |

## Name

Unique identifier for this headroom within your HAEO configuration.

**Examples**: "Solar headroom", "Battery care", "Grid support"

## Loads

The loads that use some of the generation before it reaches the batteries.
They count by the power HAEO plans for them, so a load whose timing HAEO chooses can soak up solar and lower the headroom.

## Generation

The generation the batteries should have room for, such as solar.
Generation counts by what it is forecast to produce, not what HAEO plans to use.
That way curtailing solar in the plan cannot remove the need for room it was meant to guarantee.

## Batteries

The batteries that keep the headroom.
They keep it together, so headroom needing 8 kWh is met by any mix of empty space across them.
Each battery counts the energy it can absorb below its highest allowed charge, before its charge losses.

## Look-ahead

How far ahead to keep room for.
At every point in the forecast, HAEO works out how much the generation would produce, less what the loads use, over the following look-ahead.
The headroom at that point is the largest amount the batteries would need to absorb at any time in it.

If your generation can produce far more in a few hours than your batteries hold, a long look-ahead asks for an empty battery.
Choose one where the required space stays well below your battery's capacity.

## Extra headroom

Empty space to keep on top of what the generation needs, in kWh.
On its own, with no loads or generation, it keeps the battery below full with a cost for going higher.

- **To look after the battery**, set it to the top slice you want to avoid, such as 10% of the capacity, with a low shortfall cost.
- **For a grid support program**, set it to the capacity you have committed, with a high shortfall cost.
    Use a sensor that is zero outside the program's hours if the commitment does not cover the whole day.

## Shortfall cost

The holding cost for each kWh the batteries fall short of the headroom, for every hour the shortfall lasts.
It accrues like the [reserve shortfall cost](reserve.md#shortfall-cost): a short spell full that is drained soon is cheap, while a battery left full is expensive.
For example, with a shortfall cost of 0.02 \$/kWh/h, holding 1 kWh past the headroom for 10 hours costs \$0.20.

## Sensors created

| Sensor                   | Unit | Description                                                  |
| ------------------------ | ---- | ------------------------------------------------------------ |
| Required space           | kWh  | Space the batteries should keep free at each point           |
| Available space          | kWh  | Energy the batteries can absorb at each point                |
| Space shortfall          | kWh  | How far the batteries fall short of the required space       |
| Headroom state of charge | %    | The combined state of charge the batteries should stay below |

The headroom state of charge takes the required space, stored after charge losses, away from the batteries' highest allowed charge, as a share of their combined capacity.
The [forecast card](../lovelace-card.md) draws it as a purple dotted line alongside your batteries' state of charge.

## Next steps

<div class="grid cards" markdown>

- :material-battery-lock:{ .lg .middle } **Reserve and headroom walkthrough**

    ---

    Set up headroom step by step and see the plan change.

    [:material-arrow-right: Reserve and headroom walkthrough](../../walkthroughs/reserve-and-headroom.md)

- :material-calculator:{ .lg .middle } **How headroom is modeled**

    ---

    The formulation behind reserves and headroom.

    [:material-arrow-right: Reserve and headroom modeling](../../modeling/device-layer/reserve.md)

</div>
