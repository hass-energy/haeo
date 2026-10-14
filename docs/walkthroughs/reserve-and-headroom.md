# Reserve and headroom

This guide sets up a reserve and a headroom, the two ways to tell HAEO how much your batteries should hold.
It explains what each is for, walks through adding them, and shows the plan changing on the forecast card at every step.

## What are they for?

Without either, HAEO uses your battery purely for savings.
It happily plans to run the battery down to its minimum charge for an expensive evening, or fill it to the top on cheap power overnight.
That is the cheapest plan, but it is not always the plan you want.

A **reserve** keeps energy in your batteries.
You choose how long an outage to ride through and which loads to keep running, and HAEO keeps enough charge to cover them, less any solar that keeps producing.
Use a reserve when:

- **You have backup wiring**: your inverter can run some or all of your home off grid.
- **Outages are likely**: storm season, an unreliable grid, or a known planned outage.
- **Some loads matter more than others**: a fridge, medical equipment, or a sump pump you never want to lose.

**Headroom** is the mirror image: it keeps empty space in your batteries.
You choose your generation and how far ahead to look, and HAEO keeps enough room to absorb what is coming, less what your loads use.
Use headroom when:

- **Your solar cannot be curtailed**: once the house is covered and exports are at their limit, the battery is the only place left for the surplus.
    Headroom with your solar as its generation keeps enough room for what is forecast to come.
- **You want to look after the battery**: many batteries last longer when they spend less time near 100%.
    A fixed amount of headroom keeps the battery below full, and lets it go higher only when the energy is worth more than the holding cost.
- **You take part in a grid support program**: some demand response and grid stability programs ask you to keep capacity free to absorb power when the grid needs it.
    A fixed amount of headroom keeps that capacity free, and a sensor can raise it during the hours the program covers.

Both follow your forecasts, so they change through the day, and both are soft: HAEO can go past them when that is worth more than the shortfall cost you set.

## How they are worked out

For each point in the forecast, HAEO looks at the window that follows it: the outage length for a reserve, or how far ahead to look for headroom.
It adds up what your loads use and what your generation produces through that window, hour by hour.

- **A reserve** is the largest amount the batteries would need to supply at any time in the window.
- **Headroom** is the largest amount the batteries would need to absorb at any time in the window.

Loads count by the power HAEO plans for them, and generation by what it is forecast to produce.
A surplus earlier in the window offsets demand that comes after it, and the other way round.

The chart below shows a day with a 6-hour window.
The bars are the net demand each hour (loads less solar), and the line is the reserve the battery should hold at the start of each hour.

```mermaid
xychart-beta
    title "Net demand and 6-hour reserve"
    x-axis "Hour" [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    y-axis "kWh" -4 --> 11
    bar [0.6, 0.5, 0.5, 0.6, 1.2, 1.5, 0.7, -0.4, -1.6, -2.5, -3.0, -3.2, -3.2, -2.9, -2.0, -0.5, 1.4, 2.7, 2.5, 1.8, 1.2, 0.9, 0.7, 0.6]
    line [4.9, 5.0, 4.5, 4.0, 3.4, 2.2, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2, 5.9, 9.1, 10.5, 9.8, 7.7, 5.2, 3.4, 2.2, 1.3, 0.6]
```

- **Midday needs no reserve**: solar covers the house for the next six hours, so an outage then costs the battery nothing.
    This is when headroom matters most, since the battery needs room for the surplus.
- **Early afternoon looks ahead**: at 1 pm the window runs into the evening peak, so HAEO starts asking for a reserve while solar is still producing.
- **The evening peaks**: at 4 pm the next six hours are the most expensive part of the day for the battery, so the reserve is highest.

## Prerequisites

This guide builds on the [Sigenergy System walkthrough](sigenergy-system.md).
Complete that walkthrough first — the steps here assume your system is already configured.

```guide-setup
run_guide("sigenergy-system")
```

## The plan without a reserve

Before adding anything, here is what HAEO plans for the battery over the next two days.
The green dashed line is the battery's state of charge, and the bars are its charging and discharging alongside the house and solar.
The pale orange is what the solar could produce, and the darker orange what HAEO plans to use.

Two things stand out.
The battery runs down to its minimum each evening, so an outage then would leave nothing to run the house.
And it is already full when the solar arrives, so much of the solar goes unused.

```guide
show_forecast_card(
    page,
    hass,
    step="Plan without a reserve or headroom",
    elements=["Battery", "Constant Load", "Solar"],
    inputs=["Solar"],
    horizon="2d",
)
```

## Adding a reserve

### Step 1: Choose what the reserve covers

Click **Reserve** to add one, then pick its participants:

- **Loads**: the loads to keep running through an outage.
    This guide keeps the whole house running.
- **Generation**: the generation that keeps producing during an outage.
    Only include solar if your inverter keeps running it when the grid is down.
- **Batteries**: the batteries that hold the reserve.
    With more than one battery, they hold it together.

Then set the requirement and the cost of falling short:

- **Outage length**: 12 hours covers an outage overnight.
- **Extra reserve**: 2 kWh on top of what the loads need, as a buffer against the forecast being wrong.
- **Shortfall cost**: \$0.05 per kWh short, for every hour the shortfall lasts.

```guide
add_reserve(
    page,
    name="Backup",
    loads=["Constant Load"],
    generation=["Solar"],
    storage=["Battery"],
    window=ConstantInput(12.0),
    minimum=ConstantInput(2.0),
    shortfall_cost=ConstantInput(0.05),
)
```

!!! tip "Driving the extra reserve from a sensor"

    The extra reserve accepts a sensor as well as a constant.
    Point it at a helper or template sensor to raise the reserve ahead of a storm warning and drop it back to zero afterwards.

### Step 2: Check the new plan

The reserve now appears on the forecast card as a red dotted line in the state of charge lane.
The battery's state of charge should stay on or above it.
Compare it with the plan above: the battery now follows the line down through the evening, holding enough charge for an outage at every point instead of running down to its minimum.

```guide
validate_requirement(
    hass,
    name="Backup",
    participants={"loads": ["Constant Load"], "generation": ["Solar"], "storage": ["Battery"]},
)
show_forecast_card(page, hass, step="Plan with a 12 hour reserve", elements=["Battery", "Backup"], horizon="2d")
```

### Step 3: Try a shorter outage

The reserve has input entities for its outage length, extra reserve, and shortfall cost, so you can change them from a dashboard.
Shortening the outage to 4 hours lowers the line, and HAEO plans to use more of the battery.

```guide
set_input(hass, element="Backup", field="window", value=4.0)
show_forecast_card(page, hass, step="Plan with a 4 hour reserve", elements=["Battery", "Backup"], horizon="2d")
```

## Adding headroom

### Step 4: Keep room for solar

Click **Headroom** to add one.
Its participants work the same way, but for absorbing a surplus:

- **Loads**: the loads that use some of the generation before it reaches the battery.
- **Generation**: the generation the battery should have room for.
- **Batteries**: the batteries that keep the headroom.

This guide looks 1 hour ahead.
The solar in this system can produce far more in a few hours than its 32 kWh battery holds, so looking further ahead would ask for an empty battery before every sunny morning.
Choose a look-ahead the battery can meet: one where the required space stays well below its capacity.

```guide
add_headroom(
    page,
    name="Solar headroom",
    loads=["Constant Load"],
    generation=["Solar"],
    storage=["Battery"],
    window=ConstantInput(1.0),
    minimum=ConstantInput(0.0),
    shortfall_cost=ConstantInput(0.05),
)
```

### Step 5: Check the plan between both lines

Headroom appears as a purple dotted line: the battery's state of charge should stay on or below it.
The line dips ahead of the solar, so instead of being full when the solar arrives, the battery leaves room and stores more of it.
With both added, the plan keeps the battery between the two lines, holding enough for an outage while leaving room for the solar that is coming.

```guide
validate_requirement(
    hass,
    name="Solar headroom",
    participants={"loads": ["Constant Load"], "generation": ["Solar"], "storage": ["Battery"]},
)
show_forecast_card(
    page,
    hass,
    step="Plan with a reserve and headroom",
    elements=["Battery", "Backup", "Solar headroom", "Solar"],
    inputs=["Solar"],
    horizon="2d",
)
```

### Step 6: See them in the network

The topology card marks the batteries holding a reserve with 🛡 and those keeping headroom with ⤒.
Hover over an element to see which reserves and headroom it holds or is counted in.

```guide
show_topology_card(page, hass, step="Network with a reserve and headroom")
```

## What to expect

### New devices

Each reserve and headroom appears as its own device with these sensors:

| Sensor                             | What it shows                                                         |
| ---------------------------------- | --------------------------------------------------------------------- |
| Required energy / Required space   | What the batteries should hold or keep free at each point (kWh)       |
| Available energy / Available space | What the batteries can deliver or absorb at each point, after losses  |
| Energy shortfall / Space shortfall | How far the batteries fall short (kWh)                                |
| Reserve / Headroom state of charge | The combined state of charge the batteries should stay above or below |

They also have input entities for the window, extra amount, and shortfall cost.

### Changes to the plan

- **A reserve exports less before the evening** and may charge from the grid ahead of it.
- **Headroom discharges ahead of solar** and holds off on charging from the grid when solar will fill the battery.
- **Both give way when it pays**: HAEO goes past a line when the energy is worth more than the shortfall cost for as long as it lasts.
    When a reserve and a headroom ask for more than the battery can do at once, the shortfall costs decide which gives way.

The lines are a combined state of charge: with several batteries, their total charge should stay on the right side of the line, while any one battery may cross it.

### The last hours of the forecast

HAEO cannot see past the end of the forecast, so a window starting near the end is cut short.
Both requirements taper off over the last window of the forecast.
Each time the forecast moves forward they are recomputed, so this only affects the far end of the plan.

## Tuning

### Window

A longer outage needs a bigger reserve, and a longer look-ahead needs more headroom.
If a line sits at 0% or 100% for long stretches, the battery cannot meet it.
Shorten the window, change which loads and generation it covers, or accept that the shortfall will be priced.

### Shortfall cost

The shortfall cost decides how firmly HAEO holds the line.
It is charged per kWh short, for every hour the shortfall lasts.

| Shortfall cost | Behavior                                                |
| -------------- | ------------------------------------------------------- |
| 0.005 \$/kWh/h | A soft preference — gives way to most price differences |
| 0.05 \$/kWh/h  | Held unless a price spike is well worth it              |
| 1 \$/kWh/h     | Treated as nearly untouchable                           |

### A fixed amount

A reserve or headroom with no loads or generation holds just its extra amount.
A fixed reserve keeps the battery above a level unless dipping lower is worth the cost, and a fixed headroom keeps it below full the same way.

- **To look after the battery**, set the extra headroom to the top slice you want to avoid, such as 10% of the capacity, with a low shortfall cost.
    HAEO then fills the top slice only when the energy is worth more than the holding cost for as long as it stays there.
- **For a grid support program**, set the extra headroom to the capacity you have committed, with a high shortfall cost.
    If the commitment only covers some hours, drive the extra headroom from a sensor that is zero outside them.

### More than one

You can add several of each.
For example, a reserve covering only essential loads over a 24-hour outage, and another covering the whole house over 4 hours.
Each is priced on its own, so the batteries hold enough for whichever needs more at each point.

## Troubleshooting

### The battery always sits on the wrong side of a line

The requirement may be more than the battery can hold, or meeting it may cost more than the shortfall.
Check the required energy or space sensor against your battery's capacity, and raise the shortfall cost if you want HAEO to try harder.

### A line is at zero all day

Check that the reserve or headroom includes your loads and generation.
A reserve with much more solar than load, or headroom with much more load than solar, needs nothing.

## Next steps

<div class="grid cards" markdown>

- :material-shield-check:{ .lg .middle } **Reserve reference**

    ---

    Every reserve field in detail.

    [:material-arrow-right: Reserve configuration](../user-guide/elements/reserve.md)

- :material-format-vertical-align-top:{ .lg .middle } **Headroom reference**

    ---

    Every headroom field in detail.

    [:material-arrow-right: Headroom configuration](../user-guide/elements/headroom.md)

- :material-calculator:{ .lg .middle } **How they are modeled**

    ---

    The formulation behind reserves and headroom.

    [:material-arrow-right: Reserve and headroom modeling](../modeling/device-layer/reserve.md)

</div>
