# Deferrable Load

Deferrable loads are appliances that must consume a set amount of energy within scheduled time windows, but are flexible about exactly when inside each window — pool pumps, hot water systems, irrigation, or an EV charger driven in energy mode.

You schedule the windows with a Home Assistant calendar, and HAEO decides when inside each window to run the load so the energy lands in the cheapest periods.
The requirement is not a hard rule: if a window physically cannot fit the energy, the shortfall is priced instead of breaking the optimization.

For mathematical details, see [Deferrable Load Modeling](../../modeling/device-layer/deferrable_load.md).

## Configuration

### Overview

A deferrable load in HAEO represents:

- **Run window calendar** from a Home Assistant calendar entity, with the required energy in each event's text
- **Shortfall price** for energy the window fails to absorb
- **Optional overage price** for absorbing more than required
- **Optional max power** for the physical device

## Configuration fields

| Field                                   | Type   | Required | Default | Description                                  |
| --------------------------------------- | ------ | -------- | ------- | -------------------------------------------- |
| **[Name](#name)**                       | String | Yes      | -       | Unique identifier (e.g., "Pool Pump")        |
| **[Connection](#connection)**           | Select | Yes      | -       | Node to connect to in your energy network    |
| **[Run window calendar](#run-windows)** | Entity | Yes      | -       | Calendar entity with run window events       |
| **[Shortfall price](#pricing)**         | Price  | Yes      | 10      | Cost per kWh the window fails to absorb      |
| **[Overage price](#pricing)**           | Price  | No       | -       | Cost per kWh absorbed beyond the requirement |
| **[Max power](#max-power)**             | Power  | No       | -       | Maximum power the device can draw            |

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Connection

Select the node in your energy network where the load is connected, typically your main switchboard.

### Run windows

Select a Home Assistant calendar entity that contains your run schedule.
Each calendar event is one window:

- **Start/end time**: When the load is allowed to run
- **Event text**: The energy the window must absorb, in kWh (e.g., `8`)

The number is read from the first of the location, summary, or description fields that parses as a plain number.
Events without a parsable number are ignored, as are negative numbers and values such as `nan` or `inf`.
Power can only flow to the load while a window is open.

!!! tip "Recurring schedules"

    Use recurring calendar events for daily or weekly routines — a pool pump
    that needs 8 kWh every day is one repeating event with `8` in the location.

### Pricing

- **Shortfall price**: the cost per kWh that a window fails to absorb by its end.
    The default of \$10/kWh effectively means "always run when physically possible" — lower it to let expensive periods win (e.g. a pool pump that may skip a day when energy costs more than the missed cleaning is worth).
- **Overage price**: optional cost per kWh absorbed beyond the total requirement.
    Useful when running longer than needed carries a cost (wear, water use).

Both prices must be zero or more.
A sensor that reports a negative price is treated as zero, since paying the optimizer to miss a window would make the plan meaningless.

A missed window stays priced even if a later window catches up — each window's requirement is due at its own deadline.

### Max power

Set the power the device draws while running (e.g. 1.5 kW for a pool pump).
The optimizer spreads the window's energy across the window at up to this power.

## Sensors created

The deferrable load element creates one device with the following sensors:

| Sensor           | Unit | Description                                    |
| ---------------- | ---- | ---------------------------------------------- |
| Power            | kW   | Power drawn by the load                        |
| Energy absorbed  | kWh  | Cumulative energy absorbed toward requirements |
| Energy shortfall | kWh  | Requirement the optimizer expects to miss      |

All sensors include a `forecast` attribute with optimized future values — drive your appliance's switch from the power sensor's forecast.

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
