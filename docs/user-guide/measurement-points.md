# Where values are measured

Every power value in HAEO refers to a specific point in a device's power chain.
HAEO uses a fixed convention for those points.
It does not detect how your system is wired or where your sensors measure.
The convention is chosen to match where batteries, inverters, and meters are commonly rated and measured,
so that for typical hardware HAEO's values line up with what your sensors report and what your devices accept as setpoints.

This page explains the convention so you can check that the values you configure mean what HAEO assumes they mean.
Each [element page](elements/index.md) states the point its inputs and sensors refer to.

## The convention

**An element's power limit and the power HAEO reports for it refer to the same point.**
When an element runs at its limit, its power sensor reads exactly the limit you configured.
Prices on that element's flow are charged at the same point wherever possible.

That point is on the outside of the device, where it is usually rated and metered.
For example, a battery's limits and power refer to its terminals, and an inverter's refer to its AC side.
This holds in both directions of flow: a battery's charge and discharge limits both refer to its terminals, whichever way power is moving.

**Losses happen inside the device.**
Efficiency describes the loss between the device's terminals and its inside, such as a battery's cells or an inverter's DC bus.
Values inside the device, such as stored energy and state of charge, are not power sensors.
You can work out device-side power from the reported power and the efficiency (see [Efficiency below 100%](#efficiency-below-100)).

**Elements without losses refer to a single point.**
Grid, solar, loads, and nodes have no efficiency of their own, so their limits, forecasts, and reported power all refer to the point where they connect.

**Connections you build follow the same rule.**
A connection carries power in one direction and models its losses inside itself.
Its power limit, price, and reported power all refer to the power entering the connection, before its losses.
The power leaving it is reduced by its efficiency.

These are modeling assumptions.
A real device may be rated or measured at a different point, report power from a different sensor, or have losses that a single efficiency figure does not capture.

## Using values from your hardware

When a datasheet figure or a sensor refers to the same point as HAEO's convention, you can usually use it without conversion.
When it refers to a different point, convert it first.
For example, if your battery's charge limit is specified on the cell side, divide it by the charge efficiency to get the terminal-side limit HAEO expects.

The same applies in the other direction.
Before comparing HAEO's power sensors with your own, or sending them to your hardware as setpoints in [automations](automations.md),
check that your sensor or setpoint refers to the same point, and convert if it does not.

## Efficiency below 100%

HAEO models energy as lost between each element's reference point and the device behind it.
For a battery with charge efficiency $\eta_c$, discharge efficiency $\eta_d$, and a period of $\Delta t$ hours:

$$
\Delta E_\text{stored} = \eta_c \times P_\text{charge} \times \Delta t - \frac{P_\text{discharge}}{\eta_d} \times \Delta t
$$

Charging at 5 kW with 95% efficiency for one hour stores 4.75 kWh.
Discharging at 5 kW with 95% efficiency for one hour draws 5.26 kWh from storage.

If HAEO's forecast state of charge drifts away from your battery's own state of charge while the reported power matches, your efficiency settings are the likely cause.

## Known limitations

A few prices do not yet sit at the same point as the power they apply to.
Policy prices on a battery's discharge or an inverter's DC to AC path are charged on the device side of the efficiency loss.
With 95% discharge efficiency, a 0.10 \$/kWh discharge cost works out to about 0.105 \$/kWh of power at the battery terminals.

## Changes from earlier versions

Earlier versions of HAEO placed some limits and sensors on the device side of the efficiency loss, so a sensor could read more than its configured limit.
If you set a battery charge limit, an inverter AC to DC limit, or a connection limit from a figure inside the device, re-check it against the convention above.
Connection prices also moved: they now apply to the power entering the connection, before its losses, rather than to the power delivered after them.

## Next steps

<div class="grid cards" markdown>

- :material-battery:{ .lg .middle } **Configure your elements**

    ---

    See the point each element's inputs and sensors refer to.

    [:material-arrow-right: Element configuration](elements/index.md)

- :material-chart-line:{ .lg .middle } **Understand results**

    ---

    Read the optimized schedule and the sensors HAEO creates.

    [:material-arrow-right: Understanding results](optimization.md)

- :material-robot:{ .lg .middle } **Automate your hardware**

    ---

    Send HAEO's setpoints to your battery and inverter.

    [:material-arrow-right: Automation examples](automations.md)

</div>
