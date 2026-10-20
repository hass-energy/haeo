# EV

Electric vehicles (EVs) are mobile energy storage devices that alternate between being connected to your home network and away on trips.
HAEO optimizes when to charge and discharge your EV based on electricity prices, trip schedules, and system constraints.

Internally, HAEO models the EV as a battery with a calendar-driven trip system.
When the car is home and connected, it can charge from or discharge to your home network (V2G).
When the car is away on a trip, it consumes energy based on distance traveled and can optionally model public charging costs.

For mathematical details, see [EV Modeling](../../modeling/device-layer/ev.md).

## Configuration

### Overview

An EV in HAEO represents:

- **Energy storage** with a battery capacity (kWh)
- **Charge and discharge rates** for home charging (kW)
- **Trip calendar** from a Home Assistant calendar entity with a distance in each event
- **Plugged in sensor** indicating when the vehicle is connected to your home charger
- **Optional odometer** telling how far the car has gone on the current trip
- **Optional public charging price** for modeling away-from-home charging costs

### Configuration process

EV configuration uses a sectioned flow where you enter the name, connection, trip entity selectors, and configure each input field.
The choices offered depend on the field:

- **Current state of charge** and **plugged in** accept only "Entity", since they must track the live car.
- **Odometer** accepts "Entity" or "None".
- **Trip calendar** accepts a calendar entity or "None".
- The remaining numeric fields accept "Entity" to link to a sensor or "Constant" to enter a fixed value, and optional ones also accept "None".

Fields configured with "Constant" create input entities that you can adjust at runtime without reconfiguring.

## Configuration fields

| Field                                                    | Type       | Required | Default  | Description                                     |
| -------------------------------------------------------- | ---------- | -------- | -------- | ----------------------------------------------- |
| **[Name](#name)**                                        | String     | Yes      | -        | Unique identifier (e.g., "Tesla Model 3")       |
| **[Connection](#connection)**                            | Select     | Yes      | -        | Junction or inverter the charger is attached to |
| **[Trip calendar](#trip-calendar)**                      | Entity     | No       | -        | Calendar entity with trip events                |
| **[Plugged in](#plugged-in)**                            | Entity     | Yes      | -        | Binary sensor reporting when plugged in         |
| **[Odometer](#odometer)**                                | Entity     | No       | -        | Sensor reporting the car's odometer             |
| **[Battery capacity](#battery-capacity)**                | Energy     | Yes      | -        | Total usable battery capacity                   |
| **[Energy per distance](#energy-per-distance)**          | Ratio      | Yes      | -        | Energy consumption rate (e.g. kWh/km)           |
| **[Current state of charge](#current-state-of-charge)**  | Percentage | Yes      | -        | Sensor reporting current SOC (0–100%)           |
| **[Max charge rate](#max-charge-and-discharge-rate)**    | Power      | Yes      | -        | Maximum home charging power                     |
| **[Max discharge rate](#max-charge-and-discharge-rate)** | Power      | No       | -        | Maximum V2G discharge power                     |
| **[Public charging price](#public-charging-price)**      | Price      | No       | \$10/kWh | Cost per kWh for public charging                |
| **[Max charge power](#power-limits)**                    | Power      | No       | -        | Overall max charge power limit                  |
| **[Max discharge power](#power-limits)**                 | Power      | No       | -        | Overall max discharge power limit               |
| **[Charge efficiency](#efficiency)**                     | Percentage | No       | 95%      | Efficiency when charging                        |
| **[Discharge efficiency](#efficiency)**                  | Percentage | No       | 95%      | Efficiency when discharging                     |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Connection

Select the junction or inverter the EV charger is attached to.
This is typically your main switchboard junction, or an inverter for a DC charger.

### Trip calendar

Select one or more Home Assistant calendar entities that contain your trip schedule.
Each calendar event represents a trip:

- **Start/end time**: When the car leaves and returns home
- **Distance**: Trip distance with unit in the location, summary, or description, e.g., `50 km` or `30 mi`

Without a trip calendar, the EV behaves like a stationary battery that can only charge (or discharge) while plugged in — no trip requirements are modeled.
An event whose text contains no distance, such as `School pickup`, still marks the car away for its duration but asks for no trip energy.

!!! tip "Distance format"

    The distance is read from the first of the location, summary, or description fields that holds only a number followed by a length unit, such as `50 km` or `30 mi`.
    A field with other text around the distance, such as `Commute 50 km`, is not read as a distance.
    All distances are converted to kilometres.
    A number HAEO cannot use as a distance, such as one without a unit, is ignored and listed in a repair issue so you can fix the event.

The trip calendar creates five input entities showing what HAEO reads from it: **Away** (whether each period is inside a trip), **Trip start** (where each trip of overlapping events begins), **Trip distance opening** (the distance of the events starting at each time), **Trip distance due** (the distance of the events ending at each time), and **Trip distance per period** (each trip's distance spread evenly over its duration).

HAEO plans each trip to use its energy at that steady pace, as driving does, so the forecast shows the battery running down across the trip rather than all at once.

### Plugged in

Select a binary sensor that reports `on` when the EV is plugged in at home and `off` when disconnected.
You need one to automate charging anyway, so it is required.
The trip calendar is authoritative for future availability; this sensor pins the *current* state, so an early return or unplanned absence is reflected immediately.
If you select more than one entity, the car counts as plugged in when any of them reports `on`.

While a trip event is open, the sensor and the [odometer](#odometer) together tell where the trip is:

- **Plugged in, not driven yet**: the car has not left.
    It is home for the current interval, and the trip still happens in the rest of the event, with its energy due by the event's end.
- **Plugged in after driving**: the car is back.
    The trip is over, and the car counts as home until the event's scheduled end.
- **Unplugged**: the car is on the trip, and the energy for the distance driven so far counts toward it.
    Unplugging again after coming back resumes the same trip, so ducking home in the middle of a day of driving does not ask for the whole trip's energy again.

Without an odometer HAEO cannot tell an early return from not having left, so a car plugged in during a trip event is always treated as not having left yet.

### Odometer

Select the sensor reporting the vehicle's odometer.
Any length unit Home Assistant supports (for example `km`, `mi`, or `m`) is accepted and converted to kilometres.

HAEO reads how far the odometer rose since the open trip event began from the sensor's long-term statistics, so the reading is not needed at the moment the car leaves.
The car does not drive while it waits at home, so this is the distance driven on the trip.
The **Distance since trip started** input entity shows it, and reads zero while no trip event is open.

Only sensors with statistics are offered: a distance sensor whose state class is `total` or `total_increasing`, as vehicle integrations usually set for their odometer.
If yours has no state class, set `state_class: total_increasing` on it with a [customization](https://www.home-assistant.io/docs/configuration/customizing-devices/); statistics then start from that point.

That energy has already left the battery, which the current state of charge shows, so HAEO never draws it again.

- **Less than planned**: the rest of the trip's energy stays due by the trip's end.
- **More than planned**: the trip counts as complete; the extra distance is not charged as public charging and never makes the plan fail.

!!! note "Odometers that update late"

    Many vehicle integrations only update the odometer when the car reports in, for example after parking.
    Until it updates, HAEO assumes no progress, and a car that has just plugged in back home counts as not having left until the odometer catches up.

### Keeping a margin

To keep some energy in the pack for an unplanned detour, add a [buffer](buffer.md) with the EV as both a load and storage, and set its level to the margin you want, such as 20%.
The buffer counts the EV's trips as its load and the pack as where the energy is held.
The same EV can also take part in a home or whole-system reserve alongside your home battery.

### Battery capacity

Enter the usable battery capacity in kWh from your vehicle's specifications.
The optimizer uses this value when calculating state of charge and trip energy requirements.

### Energy per distance

Enter the average energy consumption rate, or select a sensor reporting it.
Sensors in `Wh/km`, `kWh/km`, or `kWh/100km` are accepted and converted to kWh/km; constants are entered in kWh/km (e.g., 0.15 kWh/km).
Distance-per-energy units such as `km/kWh` or `mi/kWh` are not supported.
HAEO multiplies this by trip distance to determine how much energy each trip requires.

### Current state of charge

Select the Home Assistant sensor reporting the EV's current battery percentage (0–100%).
HAEO uses this as the starting point for optimization.

### Max charge and discharge rate

Set the maximum charging and discharging rates for home charging.
Both are measured at the charger, before charging losses, so a 7.4 kW charger is entered as 7.4 kW and its charge power sensor reads 7.4 kW at full rate.

- **Max charge rate**: How fast the car can charge from the grid (e.g., 7.4 kW for a typical home charger)
- **Max discharge rate**: How fast the car can export power via V2G (leave blank if V2G is not supported)

### Public charging price

Set the cost per kWh for public charging away from home.
Trip requirements are not hard constraints: any shortfall against a trip's energy requirement is priced at this rate, modeling a public top-up during the trip, so a trip can never make the optimization infeasible.
When this field is not set, a deliberately high default of \$10/kWh is used, which strongly discourages a shortfall.
The optimizer still compares it against the effective cost of home charging, so if import prices or policy costs push that above \$10/kWh it can deliberately leave a shortfall rather than pre-charge.
Set a realistic price to let the optimizer genuinely trade off pre-charging at home against topping up publicly; the expected top-up appears in the trip energy shortfall sensor.

### Power limits

Additional power limits applied to the home charging connection.
These are combined with the charge/discharge rate limits, taking the minimum of both when both are set.

### Efficiency

Enter charge and discharge efficiencies as percentages (0–100%).
These apply to the home charging connection and account for conversion losses.

## Sensors created

The EV element creates one device with the following sensors:

### Power sensors

| Sensor          | Unit | Description                    |
| --------------- | ---- | ------------------------------ |
| Charge power    | kW   | Current charging power         |
| Discharge power | kW   | Current discharging power      |
| Active power    | kW   | Net power (discharge − charge) |

### Energy sensors

| Sensor                | Unit | Description                                                    |
| --------------------- | ---- | -------------------------------------------------------------- |
| Energy stored         | kWh  | Total energy in the EV battery                                 |
| State of charge       | %    | Battery percentage                                             |
| Trip energy delivered | kWh  | Energy used by the current trip, reset at each trip start      |
| Trip energy shortfall | kWh  | Expected public top-up energy for each trip, at the trip's end |

### Shadow price sensors

| Sensor                           | Unit   | Description                                |
| -------------------------------- | ------ | ------------------------------------------ |
| Max charge power shadow price    | \$/kWh | Marginal value of relaxing charge limit    |
| Max discharge power shadow price | \$/kWh | Marginal value of relaxing discharge limit |

## Next steps

<div class="grid cards" markdown>

- :material-car-electric:{ .lg .middle } **EV modeling**

    ---

    Mathematical formulation for EV energy modeling.

    [:material-arrow-right: EV modeling](../../modeling/device-layer/ev.md)

- :material-battery:{ .lg .middle } **Battery configuration**

    ---

    Configure stationary battery storage.

    [:material-arrow-right: Battery guide](battery.md)

- :material-power-plug:{ .lg .middle } **Grid configuration**

    ---

    Configure grid import/export and pricing.

    [:material-arrow-right: Grid guide](grid.md)

</div>
