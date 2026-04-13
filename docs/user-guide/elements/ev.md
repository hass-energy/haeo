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

- **Energy storage** with a battery capacity (kWh+)
- **Charge and discharge rates** for home charging (kW)
- **Trip calendar** from a Home Assistant calendar entity with distance in the location field
- **Connected sensor** indicating when the vehicle is plugged in at home
- **Odometer sensors** for mid-trip energy tracking
- **Optional public charging price** for modeling away-from-home charging costs

### Configuration process

EV configuration uses a sectioned flow where you enter the name, connection, trip entity selectors, and configure each input field.
For numeric fields, select "Entity" to link to a sensor, "Constant" to enter a fixed value, or "None" for optional fields.

Fields configured with "Constant" create input entities that you can adjust at runtime without reconfiguring.

## Configuration fields

| Field                                                    | Type       | Required | Default | Description                                      |
| -------------------------------------------------------- | ---------- | -------- | ------- | ------------------------------------------------ |
| **[Name](#name)**                                        | String     | Yes      | -       | Unique identifier (e.g., "Tesla Model 3")        |
| **[Connection](#connection)**                            | Select     | Yes      | -       | Node to connect to in your energy network        |
| **[Trip calendar](#trip-calendar)**                      | Entity     | Yes      | -       | Calendar entity with trip events                 |
| **[Connected sensor](#connected-sensor)**                | Entity     | Yes      | -       | Binary sensor reporting when plugged in          |
| **[Odometer](#odometer)**                                | Entity     | Yes      | -       | Sensor reporting current odometer reading        |
| **[Odometer at disconnect](#odometer-at-disconnect)**    | Entity     | Yes      | -       | Sensor reporting odometer when last disconnected |
| **[Battery capacity](#battery-capacity)**                | Energy     | Yes      | -       | Total usable battery capacity                    |
| **[Energy per distance](#energy-per-distance)**          | Ratio      | Yes      | -       | Energy consumption rate (kWh per distance unit)  |
| **[Current state of charge](#current-state-of-charge)**  | Percentage | Yes      | -       | Sensor reporting current SOC (0–100%)            |
| **[Max charge rate](#max-charge-and-discharge-rate)**    | Power      | No       | -       | Maximum home charging power                      |
| **[Max discharge rate](#max-charge-and-discharge-rate)** | Power      | No       | -       | Maximum V2G discharge power                      |
| **[Public charging price](#public-charging-price)**      | Price      | No       | -       | Cost per kWh for public charging                 |
| **[Max charge power](#power-limits)**                    | Power      | No       | -       | Overall max charge power limit                   |
| **[Max discharge power](#power-limits)**                 | Power      | No       | -       | Overall max discharge power limit                |
| **[Charge efficiency](#efficiency)**                     | Percentage | No       | -       | Efficiency when charging                         |
| **[Discharge efficiency](#efficiency)**                  | Percentage | No       | -       | Efficiency when discharging                      |

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
- **Location field**: Trip distance with unit, e.g., `50 km` or `30 mi`

If the location field is missing or cannot be parsed, the trip uses zero distance (the car is simply away with no energy requirement).

!!! tip "Distance format"

    The location field must contain a number followed by a unit.
    Supported units include `km`, `mi`, `miles`, `m`, and `meters`.
    HAEO converts all distances to your Home Assistant unit system.

### Connected sensor

Select a binary sensor that reports `on` when the EV is plugged in at home and `off` when disconnected.
This sensor determines when home charging and V2G are available.

### Odometer

Select the sensor reporting the vehicle's current odometer reading.
HAEO uses this to track how much energy the car has consumed mid-trip.

### Odometer at disconnect

Select the sensor reporting the odometer reading when the car was last disconnected.
Combined with the current odometer, this lets HAEO calculate energy already consumed during an ongoing trip and reduce the remaining requirement.

!!! note "Conservative mid-trip tracking"

    If the odometer does not update while driving (some vehicles only update when parked or connected), HAEO conservatively assumes no progress has been made.
    The full trip energy remains reserved until the odometer updates.

### Battery capacity

Enter the usable battery capacity in kWh from your vehicle's specifications.
The optimizer uses this value when calculating state of charge and trip energy requirements.

### Energy per distance

Enter the average energy consumption rate in kWh per distance unit (e.g., 0.15 kWh/km).
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
When configured, HAEO can model the cost of public charging during trips as an alternative to pre-charging at home.
This helps the optimizer decide whether to charge at home prices or let the trip use public infrastructure.

### Power limits

Additional power limits applied to the home charging connection.
These are combined with the charge/discharge rate limits, taking the minimum of both when both are set.

### Efficiency

Enter charge and discharge efficiencies as percentages (0–100%).
These apply to the home charging connection and account for conversion losses.

## Sensors created

The EV element creates one device with the following sensors:

### Power sensors

| Sensor              | Unit | Description                             |
| ------------------- | ---- | --------------------------------------- |
| Charge power        | kW   | Current charging power                  |
| Discharge power     | kW   | Current discharging power               |
| Active power        | kW   | Net power (discharge − charge)          |
| Public charge power | kW   | Power from public charging during trips |

### Energy sensors

| Sensor               | Unit | Description                     |
| -------------------- | ---- | ------------------------------- |
| Energy stored        | kWh  | Total energy in the EV battery  |
| State of charge      | %    | Battery percentage              |
| Trip energy required | kWh  | Energy needed for upcoming trip |

### Shadow price sensors

| Sensor                           | Unit   | Description                                |
| -------------------------------- | ------ | ------------------------------------------ |
| Power balance shadow price       | \$/kWh | Marginal value of EV battery energy        |
| Max charge power shadow price    | \$/kW  | Marginal value of relaxing charge limit    |
| Max discharge power shadow price | \$/kW  | Marginal value of relaxing discharge limit |

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
