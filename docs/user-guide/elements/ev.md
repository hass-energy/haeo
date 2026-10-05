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
- **Connected sensor** indicating when the vehicle is plugged in at home
- **Odometer sensors** for mid-trip energy tracking
- **Optional public charging price** for modeling away-from-home charging costs

### Configuration process

EV configuration uses a sectioned flow where you enter the name, connection, trip entity selectors, and configure each input field.
The choices offered depend on the field:

- **Current state of charge** accepts only "Entity", since it must track the live battery level.
- **Connected sensor**, **odometer**, and **odometer at disconnect** accept "Entity" or "None".
    A constant connected state would pin the current interval permanently.
- **Trip calendar** accepts a calendar entity or "None".
- The remaining numeric fields accept "Entity" to link to a sensor or "Constant" to enter a fixed value, and optional ones also accept "None".

Fields configured with "Constant" create input entities that you can adjust at runtime without reconfiguring.

## Configuration fields

| Field                                                    | Type       | Required | Default               | Description                                      |
| -------------------------------------------------------- | ---------- | -------- | --------------------- | ------------------------------------------------ |
| **[Name](#name)**                                        | String     | Yes      | -                     | Unique identifier (e.g., "Tesla Model 3")        |
| **[Connection](#connection)**                            | Select     | Yes      | -                     | Node to connect to in your energy network        |
| **[Trip calendar](#trip-calendar)**                      | Entity     | No       | -                     | Calendar entity with trip events                 |
| **[Connected sensor](#connected-sensor)**                | Entity     | No       | -                     | Binary sensor reporting when plugged in          |
| **[Odometer](#odometer)**                                | Entity     | No       | -                     | Sensor reporting current odometer reading        |
| **[Odometer at disconnect](#odometer-at-disconnect)**    | Entity     | No       | -                     | Sensor reporting odometer when last disconnected |
| **[Reserve state of charge](#reserve)**                  | Percentage | No       | -                     | Buffer to keep in the pack while away            |
| **[Reserve shortfall price](#reserve)**                  | Price      | No       | Public charging price | Cost per kWh of dipping below the reserve        |
| **[Battery capacity](#battery-capacity)**                | Energy     | Yes      | -                     | Total usable battery capacity                    |
| **[Energy per distance](#energy-per-distance)**          | Ratio      | Yes      | -                     | Energy consumption rate (e.g. kWh/km)            |
| **[Current state of charge](#current-state-of-charge)**  | Percentage | Yes      | -                     | Sensor reporting current SOC (0–100%)            |
| **[Max charge rate](#max-charge-and-discharge-rate)**    | Power      | Yes      | -                     | Maximum home charging power                      |
| **[Max discharge rate](#max-charge-and-discharge-rate)** | Power      | No       | -                     | Maximum V2G discharge power                      |
| **[Public charging price](#public-charging-price)**      | Price      | No       | \$10/kWh              | Cost per kWh for public charging                 |
| **[Max charge power](#power-limits)**                    | Power      | No       | -                     | Overall max charge power limit                   |
| **[Max discharge power](#power-limits)**                 | Power      | No       | -                     | Overall max discharge power limit                |
| **[Charge efficiency](#efficiency)**                     | Percentage | No       | 95%                   | Efficiency when charging                         |
| **[Discharge efficiency](#efficiency)**                  | Percentage | No       | 95%                   | Efficiency when discharging                      |

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Connection

Select the node in your energy network where the EV charger is connected.
This is typically your main switchboard or an inverter's DC bus.

### Trip calendar

Select a Home Assistant calendar entity that contains your trip schedule.
Each calendar event represents a trip:

- **Start/end time**: When the car leaves and returns home
- **Distance**: Trip distance with unit in the location, summary, or description, e.g., `50 km` or `30 mi`

Without a trip calendar, the EV behaves like a stationary battery that can only charge (or discharge) while plugged in — no trip requirements are modeled.
Events whose text contains no parsable distance are ignored entirely.

!!! tip "Distance format"

    The distance is read from the first of the location, summary, or description fields that contains a number followed by a unit.
    Supported units include `km`, `mi`, `miles`, `m`, and `meters`; all distances are normalized to kilometres.

### Connected sensor

Select a binary sensor that reports `on` when the EV is plugged in at home and `off` when disconnected.
The trip calendar is authoritative for future availability; this sensor pins the *current* state, so an early return or unplanned absence is reflected immediately.
If the sensor reports the car plugged in while a trip event is still open, HAEO assumes the car has not left yet.
It is home for the current interval, and the trip still happens in the rest of the event, with its energy due by the event's end.

HAEO treats the trip as done early only when Home Assistant's history shows the sensor unplugged at some point since the trip event started.
When the [odometer](#odometer) and [odometer at disconnect](#odometer-at-disconnect) sensors are configured, the car must also have driven since it disconnected, so a brief unplug without driving does not count.
A trip done early counts the car as home until the event's scheduled end, and the rest of the trip asks for no energy or public charging.
Readings of `unavailable` or `unknown`, such as during a Home Assistant restart, never count as unplugged.

This history comes from the [recorder](https://www.home-assistant.io/integrations/recorder/), which Home Assistant enables by default, and covers the last seven days.
If the recorder is disabled or excludes the connected sensor, a car plugged in during a trip event is always treated as not yet departed.

This field takes a sensor or nothing; there is no constant option.
Without a connected sensor the trip calendar governs the current interval too: the car counts as away whenever a trip event overlaps the current interval and as plugged in otherwise.
Without either a trip calendar or a connected sensor, the EV is treated as always plugged in.

### Odometer

Select the sensor reporting the vehicle's current odometer reading.
HAEO uses this to track how much energy the car has consumed mid-trip.
Any length unit Home Assistant supports (for example `km`, `mi`, or `m`) is accepted and converted to kilometres.

### Odometer at disconnect

Select the sensor reporting the odometer reading when the car was last disconnected.
Combined with the current odometer, this lets HAEO calculate energy already consumed during an ongoing trip and reduce the remaining requirement.
It uses the same length unit conversion as the odometer.

The distance driven since disconnect is credited only to the trip whose calendar window is open now.
That energy has already left the battery, which the current state of charge shows, so HAEO never draws it again.

- **Less than planned**: the rest of the trip's energy stays reserved until the trip's end.
- **More than planned**: the trip counts as complete; the extra distance is not charged as public charging and never makes the plan fail.
- **Outside any trip window**: the distance is ignored.
- **Negative, missing, or invalid readings** (for example a reset sensor): no distance is credited.

Distance never carries over to later trips, so each later trip still reserves its full energy.

!!! note "Conservative mid-trip tracking"

    If the odometer does not update while driving (some vehicles only update when parked or connected), HAEO conservatively assumes no progress has been made.
    The full trip energy remains reserved until the odometer updates.

### Reserve

Optionally keep a buffer in the pack while the car is away, so an unplanned detour does not leave you stranded.
The reserve is priced like a demand charge: for each trip, the cost is on the **lowest battery level hit during the trip window**, not on every interval spent below the reserve.
Dropping 5 kWh below the reserve for one hour or for the whole trip costs the same — one charge per trip on the depth of the dip.

- **Reserve state of charge**: the buffer as a percentage of battery capacity (e.g. 20%)
- **Reserve shortfall price**: the cost per kWh of dipping below the reserve; when unset, the public charging price applies (the cost of restoring the buffer away from home)

When configured, a **Reserve shortfall** sensor shows the expected dip below the reserve for each trip.

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

Set the maximum charging and discharging rates for home charging:

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

| Sensor                | Unit | Description                                                                 |
| --------------------- | ---- | --------------------------------------------------------------------------- |
| Energy stored         | kWh  | Total energy in the EV battery                                              |
| State of charge       | %    | Battery percentage                                                          |
| Trip energy delivered | kWh  | Energy used by the current trip, reset at each trip start                   |
| Trip energy shortfall | kWh  | Expected public top-up energy for each trip, at the trip's end              |
| Reserve shortfall     | kWh  | Expected dip below the reserve per trip (only when a reserve is configured) |

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
