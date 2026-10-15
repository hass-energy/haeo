# Buffers: reserve and headroom

This guide sets up two buffers, the way to tell HAEO how much your batteries should hold back.
A buffer comes in two kinds: a reserve and headroom.
The guide explains what each is for, walks through adding them, and shows the plan changing on the forecast card at every step.

## What are they for?

Without a buffer, HAEO uses your battery purely for savings.
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
    Headroom at a level such as 90% keeps the battery below it, and lets it go higher only when the energy is worth more than the holding cost.
- **You take part in a grid support program**: some demand response and grid stability programs ask you to keep capacity free to absorb power when the grid needs it.
    Headroom at a level that leaves that capacity free keeps it free, and a sensor can lower the level during the hours the program covers.

Both follow your forecasts, so they change through the day, and both are soft: HAEO can go past them when that is worth more than the shortfall cost you set.

## How they are worked out

For each point in the forecast, HAEO looks at the window that follows it: the outage length for a reserve, or how far ahead to look for headroom.
It adds up what your loads use and what your generation produces through that window, hour by hour.

- **A reserve** is the largest amount the batteries would need to supply at any time in the window.
- **Headroom** is the largest amount the batteries would need to absorb at any time in the window.

Loads count by the power HAEO plans for them, and generation by what it is forecast to produce.
A surplus earlier in the window offsets demand that comes after it, and the other way round.

Both are measured from a level.
A reserve sits on top of its level, and headroom below it.
With no level set, they are measured from the battery's min or max charge.

## Prerequisites

This guide builds on the [Sigenergy System walkthrough](sigenergy-system.md).
Complete that walkthrough first — the steps here assume your system is already configured.

```guide-setup
run_guide("sigenergy-system")
```

## The plan without a reserve

Before adding anything, here is what HAEO plans over the next two days.
The green dashed line is the battery's state of charge, and the bars are its charging and discharging alongside the house, solar, and grid.
The pale orange is what the solar could produce, and the darker orange what HAEO plans to use.
The lines on the price axis are the grid's import and export prices.

The battery runs down to its minimum each evening, so an outage then would leave nothing to run the house.
And it charges all the way to full most days, which wears it faster than it needs to.

```guide
show_forecast_card(
    page,
    hass,
    step="Plan without a reserve or headroom",
    elements=["Battery", "Grid", "House load", "Solar"],
    inputs=["Solar", "Grid"],
    horizon="2d",
)
```

## Adding a reserve

Click **Buffer** to add one, choose **Reserve: keep energy** as its kind, then pick its participants:

- **Loads**: the loads to keep running through an outage.
    This guide keeps the whole house running.
- **Generation**: the generation that keeps producing during an outage.
    Only include solar if your inverter keeps running it when the grid is down.
- **Batteries**: the batteries that hold the reserve.
    With more than one battery, they hold it together.

Then set the requirement and the cost of falling short:

- **Window**: 12 hours covers an outage overnight.
- **Level**: 15%, so the reserve sits on top of 15% charge rather than the battery's 10% min charge, as a margin against the forecast being wrong.
- **Shortfall cost**: \$0.05 per kWh short, for every hour the shortfall lasts.

```guide
add_buffer(
    page,
    name="Backup",
    kind="reserve",
    loads=["House load"],
    generation=["Solar"],
    storage=["Battery"],
    window=ConstantInput(12.0),
    level=ConstantInput(15.0),
    shortfall_cost=ConstantInput(0.05),
)
validate_buffer(
    hass,
    name="Backup",
    kind="reserve",
    participants={"loads": ["House load"], "generation": ["Solar"], "storage": ["Battery"]},
)
```

!!! tip "Driving the level from a sensor"

    The level accepts a sensor as well as a constant.
    Point it at a helper or template sensor to raise the reserve ahead of a storm warning and drop it back afterwards.

## Adding headroom

This headroom keeps the top 10% of the battery free, so it spends less time full.
It covers no loads or generation, so it simply keeps the battery below its level of 90%.
A low shortfall cost lets HAEO fill the top of the battery when the energy is worth it, such as when it will soon be needed.

Click **Buffer** to add another, choose **Headroom: keep empty space** as its kind, pick the battery, and set:

- **Window**: 1 hour.
    With no loads or generation it does not change what the headroom holds.
- **Level**: 90%.
- **Shortfall cost**: \$0.02 per kWh past the headroom, for every hour it lasts.

```guide
add_buffer(
    page,
    name="Battery care",
    kind="headroom",
    storage=["Battery"],
    window=ConstantInput(1.0),
    level=ConstantInput(90.0),
    shortfall_cost=ConstantInput(0.02),
)
validate_buffer(hass, name="Battery care", kind="headroom", participants={"storage": ["Battery"]})
```

## Comparing the plans

Use the arrows to flick between the plans with neither, each one, and both.

- **The reserve** appears as a red dotted line, which the battery's state of charge should stay on or above.
    The battery now follows the line down through the evening, holding enough for an outage at every point instead of running down to its minimum.
    Overnight the line rests on its 15% level.
- **A shorter outage** lowers the line, and HAEO plans to use more of the battery.
- **The headroom** appears as a purple dotted line at 90%, which the battery's state of charge should stay on or below.
    The battery now waits on the line through the day instead of sitting at full.
    It only tops up past it for a short spell before the evening, when the energy is about to be used and the holding cost is small.
- **With both**, the plan keeps the battery between the two lines.

Each buffer has input entities for its window, level, and shortfall cost, so you can change them from a dashboard as these plans do.
A buffer that is switched off in a plan stays in the legend, greyed out.

```guide
# Every plan lists both buffers, turning off the ones it leaves out, so the legends match
elements = ["Battery", "Grid", "House load", "Solar", "Backup", "Battery care"]


def show_plan(step, hidden=()):
    show_forecast_card(
        page, hass, step=step, elements=elements, inputs=["Solar", "Grid"], hidden=list(hidden), horizon="2d"
    )


set_input(hass, element="Backup", field="shortfall_cost", value=0.0)
set_input(hass, element="Battery care", field="shortfall_cost", value=0.0)
show_plan("Without a reserve or headroom", hidden=["Backup", "Battery care"])

set_input(hass, element="Backup", field="shortfall_cost", value=0.05)
show_plan("With a 12 hour reserve", hidden=["Battery care"])

set_input(hass, element="Backup", field="window", value=4.0)
show_plan("With a 4 hour reserve", hidden=["Battery care"])

set_input(hass, element="Backup", field="shortfall_cost", value=0.0)
set_input(hass, element="Battery care", field="shortfall_cost", value=0.02)
show_plan("Keeping the top 10% free", hidden=["Backup"])

set_input(hass, element="Backup", field="shortfall_cost", value=0.05)
show_plan("With a 4 hour reserve and the top 10% free")
```

## Seeing them in the network

The topology card marks the batteries holding a reserve with 🛡 and those keeping headroom with ⤒.
Hover over an element to see which buffers it holds or is counted in.

```guide
show_topology_card(page, hass, step="Network with a reserve and headroom")
```

## What to expect

### New devices

Each buffer appears as its own device with these sensors:

| Sensor                 | What it shows                                                                  |
| ---------------------- | ------------------------------------------------------------------------------ |
| Required energy        | What the batteries should hold or keep free past the level at each point (kWh) |
| Available energy       | What the batteries hold or keep free past the level at each point (kWh)        |
| Energy shortfall       | How far the batteries fall short (kWh)                                         |
| Buffer state of charge | The combined state of charge the batteries should stay above or below          |

The energy sensors measure energy stored in the batteries.
Each buffer also has input entities for its window, level, and shortfall cost.

### Changes to the plan

- **A reserve exports less before the evening** and may charge from the grid ahead of it.
- **Headroom stops short of full**, and with generation included, discharges ahead of it to leave room.
- **Both give way when it pays**: HAEO goes past a line when the energy is worth more than the shortfall cost for as long as it lasts.
    When a reserve and a headroom ask for more than the battery can do at once, the shortfall costs decide which gives way.

The lines are a combined state of charge: with several batteries, their total charge should stay on the right side of the line, while any one battery may cross it.

### The last hours of the forecast

HAEO cannot see past the end of the forecast, so a window starting near the end is cut short.
Both requirements taper off over the last window of the forecast.
Each time the forecast moves forward they are recomputed, so this only affects the far end of the plan.

## Tuning

### Window

A longer window needs a bigger reserve or more headroom.
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

### A fixed level

A buffer with no loads or generation holds the batteries on one side of its level.
A reserve keeps the battery above its level unless dipping lower is worth the cost, and headroom keeps it below its level the same way.

- **To look after the battery**, add headroom at the level you want to stay under, such as 90%, with a low shortfall cost.
    HAEO then fills the top slice only when the energy is worth more than the holding cost for as long as it stays there.
- **For a grid support program**, add headroom at a level that leaves the capacity you have committed free, with a high shortfall cost.
    If the commitment only covers some hours, drive the level from a sensor that is 100% outside them.

### More than one

You can add several buffers of each kind.
For example, a reserve covering only essential loads over a 24-hour outage, and another covering the whole house over 4 hours.
Each is priced on its own, so the batteries hold enough for whichever needs more at each point.

## Troubleshooting

### The battery always sits on the wrong side of a line

The requirement may be more than the battery can hold, or meeting it may cost more than the shortfall.
Check the required energy or space sensor against your battery's capacity, and raise the shortfall cost if you want HAEO to try harder.

### A line is at zero all day

Check that the buffer includes your loads and generation, or set a level.
A reserve with much more solar than load, or headroom with much more load than solar, needs nothing.

## Next steps

<div class="grid cards" markdown>

- :material-shield-check:{ .lg .middle } **Buffer reference**

    ---

    Every buffer field in detail.

    [:material-arrow-right: Buffer configuration](../user-guide/elements/buffer.md)

- :material-calculator:{ .lg .middle } **How they are modeled**

    ---

    The formulation behind reserves and headroom.

    [:material-arrow-right: Buffer modeling](../modeling/device-layer/buffer.md)

</div>
