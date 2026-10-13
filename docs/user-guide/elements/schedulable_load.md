# Schedulable Load

Schedulable loads are appliances that run a fixed program once started — dishwashers, washing machines, dryers.
They draw a known power for a known time and cannot pause halfway, but they are flexible about when they start.

You schedule windows with a Home Assistant calendar, and HAEO picks the start inside each window that puts the run in the cheapest periods.
Each run must finish before its window ends.
Missing a window is not a hard rule: if the run cannot fit, the miss is priced instead of breaking the optimization.

For mathematical details, see [Schedulable Load Modeling](../../modeling/device-layer/schedulable_load.md).

## Configuration

### Overview

A schedulable load in HAEO represents:

- **Run window calendar** from a Home Assistant calendar entity, one run per event
- **Run profile**: the power the appliance draws and how long one run takes
- **Optional running sensor** reporting whether the appliance is running now
- **Missed run price** for a window that receives no run
- **Start decision** in the advanced section, choosing how strictly each start is all or nothing

## Configuration fields

| Field                                   | Type     | Required | Default   | Description                                  |
| --------------------------------------- | -------- | -------- | --------- | -------------------------------------------- |
| **[Name](#name)**                       | String   | Yes      | -         | Unique identifier (e.g., "Dishwasher")       |
| **[Connection](#connection)**           | Select   | Yes      | -         | Junction or inverter the load is attached to |
| **[Run window calendar](#run-windows)** | Entity   | Yes      | -         | Calendar entity with run window events       |
| **[Running](#running)**                 | Entity   | No       | -         | Sensor that is on while the appliance runs   |
| **[Power](#run-profile)**               | Power    | Yes      | -         | Power drawn while running                    |
| **[Run duration](#run-profile)**        | Duration | Yes      | -         | How long one run takes                       |
| **[Missed run price](#pricing)**        | Price    | Yes      | 10        | Cost per kWh of a run a window misses        |
| **[Start decision](#start-decision)**   | Select   | Yes      | Start now | Which starts are all or nothing              |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Connection

Select the junction or inverter the load is attached to, typically your main switchboard.

### Run windows

Select a Home Assistant calendar entity that contains your schedule.
Each calendar event is one window that receives one run, and the whole run must fit between the event's start and end.
The event text is not used.

Overlapping events merge into one window that receives one run.
Events that only touch, with one ending exactly when the next starts, stay separate windows with a run each.
A window that runs past the end of the planning horizon is planned as if it ended at the horizon end.
If the run cannot fit before then, the plan shows a missed run until the horizon moves far enough forward.

!!! tip "Recurring schedules"

    Use a recurring event for routines — a dishwasher loaded after dinner that
    must be done by breakfast is one daily event from 20:00 to 07:00.

### Running

HAEO re-plans regularly, and each plan starts from the present.
Without this sensor, a plan made while the appliance is running does not know a run is in progress and may plan another one.

Select a binary sensor or input boolean that is on while the appliance runs.
Many appliance integrations provide one; otherwise a [threshold sensor](https://www.home-assistant.io/integrations/threshold/) on the appliance's power works.
HAEO looks up when the sensor last turned on from Home Assistant's history, so you do not need to build anything else.

- **Running now**: the rest of the run is planned from the present, and no new run starts until it finishes.
- **Ran during the open window**: the window is treated as done, even after the appliance stops.
- **Ran before the open window started**: the window still needs its own run.

### Run profile

- **Power**: the power the appliance draws while running, in kW.
- **Run duration**: how long one run takes.
    Entities may report seconds, minutes, hours, or days; constants are entered in hours.

The profile is the same for every run.
Use an entity if you change programs, for example a helper you set when you pick the eco cycle.

### Pricing

The **missed run price** is the cost per kWh of a run that a window does not receive, so a 2 kWh run missed at the default \$10/kWh costs \$20.
The default effectively means "always run when physically possible".
Lower it to let expensive energy win, for example a load that may skip a day when running costs more than the run is worth.

The price must be zero or more.
A sensor that reports a negative price is treated as zero.

### Start decision

HAEO plans by linear programming, which can split a run across several starts when that looks cheaper on paper — half a run now and half later.
A split plan cannot be carried out, so the start decision controls which starts must be all or nothing:

- **Start now** (default): the decision to start in the current period is all or nothing.
    That is the only decision acted on before HAEO plans again, and it costs almost no extra solve time.
- **All starts**: every planned start is all or nothing.
    The whole forecast is a valid schedule, but the solve is slower.
- **Linear**: no start is forced to be all or nothing.
    Fastest, and usually fine when nothing else limits the appliance's power.

## Sensors created

The schedulable load element creates one device with the following sensors:

| Sensor        | Unit | Description                                                     |
| ------------- | ---- | --------------------------------------------------------------- |
| Power         | kW   | Power drawn by the load                                         |
| Start         | -    | 1 when a run should start now; the forecast shows planned starts |
| Energy missed | kWh  | Energy of runs the optimizer expects windows to miss            |

All sensors include a `forecast` attribute with optimized future values.
Start the appliance when the **Start** sensor reads 1, for example with an automation that turns on its smart plug or sends its remote start command.

## Next steps

<div class="grid cards" markdown>

- :material-dishwasher:{ .lg .middle } **Schedulable load modeling**

    ---

    How the profile, windows, and running sensor become the model.

    [:material-arrow-right: Schedulable load modeling](../../modeling/device-layer/schedulable_load.md)

- :material-timer-outline:{ .lg .middle } **Deferrable load configuration**

    ---

    For loads that need an amount of energy rather than a fixed run.

    [:material-arrow-right: Deferrable load guide](deferrable_load.md)

- :material-home-lightning-bolt:{ .lg .middle } **Automation examples**

    ---

    Use optimization results to control your appliances.

    [:material-arrow-right: Automations](../automations.md)

</div>
