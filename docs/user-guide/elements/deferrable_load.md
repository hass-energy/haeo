# Deferrable Load

Deferrable loads are appliances that must consume a set amount of energy within scheduled time windows, but are flexible about exactly when inside each window — pool pumps, hot water systems, irrigation, or an EV charger driven in energy mode.

You schedule the windows with a Home Assistant calendar, and HAEO decides when inside each window to run the load so the energy lands in the cheapest periods.
The requirement is not a hard rule: if an event physically cannot fit its energy, the shortfall is priced instead of breaking the optimization, and running past it is priced rather than forbidden.
A [buffer](buffer.md) that counts a deferrable load among its loads follows its planned power, so where HAEO schedules the load also sets the reserve it needs.

For mathematical details, see [Deferrable Load Modeling](../../modeling/device-layer/deferrable_load.md).

## Configuration

### Overview

A deferrable load in HAEO represents:

- **Run window calendar** from a Home Assistant calendar entity, with the required energy in each event's text
- **Optional delivered energy sensor** reporting how much the open window has already received
- **Shortfall price** for energy the window fails to receive
- **Overage price** for delivering more than required
- **Optional max power** for the physical device

## Configuration fields

| Field                                   | Type   | Required | Default | Description                                     |
| --------------------------------------- | ------ | -------- | ------- | ----------------------------------------------- |
| **[Name](#name)**                       | String | Yes      | -       | Unique identifier (e.g., "Pool Pump")           |
| **[Connection](#connection)**           | Select | Yes      | -       | Junction or inverter the load is attached to    |
| **[Run window calendar](#run-windows)** | Entity | Yes      | -       | Calendar entity with run window events          |
| **[Energy meter](#energy-meter)**       | Energy | No       | -       | Running total of the energy the device has used |
| **[Shortfall price](#pricing)**         | Price  | Yes      | 10      | Cost per kWh the window fails to receive        |
| **[Overage price](#pricing)**           | Price  | Yes      | 0       | Cost per kWh delivered beyond the requirement   |
| **[Max power](#max-power)**             | Power  | No       | -       | Maximum power the device can draw               |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Connection

Select the junction or inverter the load is attached to, typically your main switchboard.

### Run windows

Select one or more Home Assistant calendar entities that contain your run schedule.
Each calendar event is one window:

- **Start/end time**: When the load is allowed to run
- **Event text**: The energy the window must receive, with its unit (e.g., `8 kWh` or `500 Wh`)

The value is read from the first of the location, summary, or description fields that holds a number, and converted to kWh.
An event without a number is still a window, but needs no energy.
A number HAEO cannot use, such as one without a unit or a negative energy, is ignored and listed in a repair issue so you can fix the event.
Power can only flow to the load while a window is open.

Events may overlap.
Each event's energy must arrive between its own start and end: energy delivered before an event starts never counts toward it, and an event is due by its own end even when another event keeps running.
An event that sits entirely inside a longer one is the exception: it is still due its energy by its end, but that energy may arrive before it starts.
An event that runs past the end of the planning horizon is planned as if it ended at the horizon end.
If its energy cannot fit before then, the plan shows a shortfall that shrinks as the horizon moves forward.

!!! tip "Recurring schedules"

    Use recurring calendar events for daily or weekly routines — a pool pump
    that needs 8 kWh every day is one repeating event with `8 kWh` in the location.

### Energy meter

HAEO re-plans regularly, and each plan starts from the present.
Without a meter, a plan made halfway through a window asks for the window's full energy again, so the device runs longer than needed or a large shortfall is predicted near the window's end.

Select the device's energy sensor: one that counts the energy it has used, such as a smart plug's total energy.
HAEO reads how much it rose since the open window started from the sensor's long-term statistics, so the sensor never needs to reset when a window starts.
Sensors that reset on their own, such as an "energy today" sensor, also work, and a window that runs past midnight still counts all its energy.

Only sensors with statistics are offered: an energy sensor whose state class is `total` or `total_increasing`.
Statistics reach back a week, so a window that started earlier than that is credited only what the sensor counted within the week.

HAEO credits the rise only to the window that is open when the plan starts.
When events overlap, the window starts at the earliest of them, so the rise counts from there.
The **Energy since window started** input entity shows the rise HAEO is using, and reads zero while no window is open.

- **Below the window's energy**: only the remainder is planned.
- **Above the window's energy**: the window is treated as complete.
    The extra energy is already used, so it counts as overage but never changes the plan or makes it fail.

### Pricing

- **Shortfall price**: the cost per kWh that a window fails to receive by its end.
    The default of \$10/kWh effectively means "always run when physically possible" — lower it to let expensive periods win (e.g. a pool pump that may skip a day when energy costs more than the missed cleaning is worth).
- **Overage price**: the cost per kWh delivered beyond what the events that have started need.
    The default of zero lets the load take extra energy only when it saves money, such as when you are paid to use energy; raise it when running longer than needed has a cost (wear, water use).
    Overage is never forbidden, so a device that has already run past its requirement never makes the plan fail.

Both prices must be zero or more, since paying the optimizer to miss an event would make the plan meaningless.

Each event is settled on its own: a missed event stays priced even if energy arrives after it ends, and that energy only counts toward events still running.

### Max power

Set the power the device draws while running (e.g. 1.5 kW for a pool pump).
The optimizer spreads the window's energy across the window at up to this power.

## Sensors created

The deferrable load element creates one device with the following sensors:

| Sensor           | Unit | Description                                                |
| ---------------- | ---- | ---------------------------------------------------------- |
| Power            | kW   | Power drawn by the load                                    |
| Energy delivered | kWh  | Energy delivered in the current window, reset at its start |
| Energy shortfall | kWh  | Requirement the optimizer expects each window to miss      |
| Energy overage   | kWh  | Energy planned beyond each window's requirement            |

All sensors include a `forecast` attribute with optimized future values — drive your appliance's switch from the power sensor's forecast.

The run window calendar also creates four input entities showing what HAEO reads from it: **Run window** (whether each period is inside a window), **Window start** (where each window of overlapping events opens), **Energy opening** (the energy of the events starting at each time), and **Energy due** (the energy of the events ending at each time).

## Next steps

<div class="grid cards" markdown>

- :material-timer-outline:{ .lg .middle } **Deferrable load modeling**

    ---

    Mathematical formulation for deferrable loads.

    [:material-arrow-right: Deferrable load modeling](../../modeling/device-layer/deferrable_load.md)

- :material-car-electric:{ .lg .middle } **EV configuration**

    ---

    Trip-aware EV charging built on the same mechanism.

    [:material-arrow-right: EV guide](ev.md)

- :material-home-lightning-bolt:{ .lg .middle } **Automation examples**

    ---

    Use optimization results to control your appliances.

    [:material-arrow-right: Automations](../automations.md)

</div>
