# Connections

Connections define explicit, **unidirectional** power paths between elements, with optional capacity limits, efficiency losses, and transfer pricing.

!!! warning "Advanced Element"

    Connection is only available when **Advanced Mode** is enabled on your hub.
    This element is intended for advanced users who need explicit control over power flow paths.
    Most users should rely on implicit connections created automatically by other elements.

!!! note "Implicit connections"

    Many elements create implicit connections automatically.
    You only need explicit Connection elements for additional power paths not covered by element defaults.

!!! note "Bidirectional paths"

    Each Connection flows from **source** to **target** only.
    To model flow in both directions (for example between two buses), add **two** Connection elements with swapped endpoints and independent limits, efficiency, and pricing.
    For AC/DC conversion between a battery or solar and the grid, consider the [Inverter](inverter.md) element instead.

!!! info "Upgrading from bidirectional connections"

    Earlier versions configured both directions on a single connection.
    On upgrade, each existing connection keeps its source-to-target settings.
    If any reverse setting (max power, price, or efficiency) was set, a second connection named `{name} ({target} to {source})` is created carrying those settings.
    No reverse connection is created when no reverse setting was set or the reverse max power was 0.
    If a connection with swapped endpoints already exists, the reverse settings are merged into it instead.
    Add a reverse connection yourself if power should flow both ways.

## Configuration

| Field          | Type                                     | Required | Default   | Description                                      |
| -------------- | ---------------------------------------- | -------- | --------- | ------------------------------------------------ |
| **Name**       | String                                   | Yes      | -         | Unique identifier for this connection            |
| **Source**     | Element                                  | Yes      | -         | Element power flows from                         |
| **Target**     | Element                                  | Yes      | -         | Element power flows to                           |
| **Max power**  | [sensor](../forecasts-and-sensors.md)    | No       | Unlimited | Maximum power arriving at the target (kW)        |
| **Efficiency** | [sensor](../forecasts-and-sensors.md)    | No       | 100%      | Efficiency percentage (0-100) for this direction |
| **Price**      | [sensor(s)](../forecasts-and-sensors.md) | No       | 0         | Price (\$/kWh) for power arriving at the target  |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

!!! tip "Configuration tips"

    **Leaving fields unset**: When a path should allow unlimited flow with no losses or costs, leave the optional fields empty rather than creating sensors with maximum or default values.

    **Segment-based behavior**: Connections compose internal segments for limits, efficiency, and pricing.
    You configure the fields above, and the model applies the corresponding segment behavior automatically.

    **Using constant values**: All sensor fields require sensor entities.

Use [input number helpers](https://www.home-assistant.io/integrations/input_number/) to configure constant values.

### Connection Endpoint Selection

The **Source** and **Target** fields show a dropdown of available elements that can be used as connection endpoints.
Only elements that act as a junction for power flow appear in the list.

| Element                               | Appears as an endpoint             |
| ------------------------------------- | ---------------------------------- |
| [Junction](junction.md)               | Always                             |
| [Node](node.md)                       | Always                             |
| [Inverter](inverter.md) (its DC bus)  | Always                             |
| [Battery Section](battery_section.md) | Only when Advanced Mode is enabled |
| Grid, Battery, Solar, Load            | Never                              |
| Connection, Policy                    | Never                              |

**Why Grid, Battery, Solar, and Load are never endpoints:**
These elements apply their prices, forecasts, power limits, and efficiencies on their own connection to the junction or inverter they are connected to.
A connection made directly to one of them would bypass all of that.
For example, a connection out of a Grid would be free, unlimited import that ignores the import price, and a connection into a Load would be a free sink that ignores the load forecast.
Connect to the junction or inverter the element is attached to instead, so its own limits and prices still apply.

If an existing configuration already connects an element directly to a Grid, Battery, Solar, or Load, HAEO raises a repair issue listing each affected connection.
Reconfigure those elements to connect to the corresponding junction or inverter, and the issue clears automatically.

## Configuration Examples

### One-way link between junctions

| Field         | Value                  |
| ------------- | ---------------------- |
| **Name**      | DC bus to AC bus       |
| **Source**    | DC Bus                 |
| **Target**    | AC Bus                 |
| **Max power** | input_number.max_power |

### Bidirectional link (two connections)

Create one connection for each direction when both paths need limits or different parameters:

| Connection | Source | Target | **Max power**             |
| ---------- | ------ | ------ | ------------------------- |
| DC to AC   | DC Bus | AC Bus | input_number.dc_to_ac_max |
| AC to DC   | AC Bus | DC Bus | input_number.ac_to_dc_max |

Use separate **Efficiency** and **Price** values on each connection when the directions differ.

## Physical Interpretation

**Unidirectional flow:**
Power optimized on this connection always travels from source to target.
Values are zero or positive in that direction.

**Where each setting applies:**
**Max power**, **Price**, and the reported connection power all apply to the power entering the connection, before its losses.
Efficiency losses are applied after them, so the power arriving at the target is reduced by the efficiency.
Example: with 95% efficiency and a **Max power** of 10 kW, the connection reports 10 kW at its limit, 9.5 kW arrives at the target, and **Price** is charged on 10 kW.

**Transmission costs:**
Connection pricing models fees for using a power transfer path (wheeling charges, connection fees, peak demand charges).

## Common Patterns

### Unlimited one-way connection

Leave **Max power** unset for unlimited flow in the configured direction:

| Field      | Value      |
| ---------- | ---------- |
| **Name**   | Bus A to B |
| **Source** | Bus A      |
| **Target** | Bus B      |

### Conversion with efficiency

| Field          | Value                   |
| -------------- | ----------------------- |
| **Name**       | DC to AC                |
| **Source**     | DC Bus                  |
| **Target**     | AC Bus                  |
| **Max power**  | input_number.max_power  |
| **Efficiency** | input_number.efficiency |

Add a second connection (AC → DC) with its own efficiency if reverse conversion is required.

### Availability windows

Use a time-varying sensor for **Max power** to model device availability.
Example: EV only available for charging 6 PM to 8 AM.

Create a template sensor:

```yaml
template:
  - sensor:
      - name: EV Charging Availability
        unit_of_measurement: W
        state: >
          {% set hour = now().hour %}
          {% if hour >= 18 or hour < 8 %}
            7200
          {% else %}
            0
          {% endif %}
```

Then configure the connection:

| Field         | Value                           |
| ------------- | ------------------------------- |
| **Name**      | Switchboard to EV               |
| **Source**    | Switchboard                     |
| **Target**    | EV Battery                      |
| **Max power** | sensor.ev_charging_availability |

!!! note "Battery Section endpoint"

    `EV Battery` is a [Battery Section](battery_section.md), which appears in connection selectors only when Advanced Mode is enabled.
    Power reaches it through the Switchboard, so the grid import price still applies to the charging energy.

The optimizer will only schedule charging when the sensor value is non-zero.

### Input Entities

Each optional configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                                    | Unit   | Description                    |
| ---------------------------------------- | ------ | ------------------------------ |
| `number.{name}_max_power_source_target`  | kW     | Maximum power (if configured)  |
| `number.{name}_efficiency_source_target` | %      | Efficiency (if configured)     |
| `number.{name}_price_source_target`      | \$/kWh | Transfer price (if configured) |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Connection element creates one device in Home Assistant.

The power sensor display name uses the configured source and target element names (for example, `{source} to {target} power`).

| Sensor                       | Unit | Description                                                  |
| ---------------------------- | ---- | ------------------------------------------------------------ |
| `{source} to {target} power` | kW   | Optimized power leaving the source, before efficiency losses |

Power values are zero or positive.
A value of 0 means no power is flowing on this connection at that time period.

**Example**: A value of 3.5 kW means 3.5 kW is flowing from the source element to the target element at that time period.

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

See [troubleshooting guide](../troubleshooting.md#graph-isnt-connected-properly) for connection issues.

## Next steps

<div class="grid cards" markdown>

- :material-home-lightning-bolt:{ .lg .middle } **Complete your network**

    ---

    Review all configured elements and ensure proper connections.

    [:material-arrow-right: Elements overview](index.md)

- :material-math-integral:{ .lg .middle } **Connection modeling**

    ---

    Understand the mathematical formulation of power flows.

    [:material-arrow-right: Connection modeling](../../modeling/device-layer/connection.md)

- :material-circle-outline:{ .lg .middle } **Junction modeling**

    ---

    Learn about power balance where connections meet.

    [:material-arrow-right: Junction modeling](../../modeling/device-layer/junction.md)

- :material-chart-line:{ .lg .middle } **Understand optimization**

    ---

    See how HAEO optimizes power flow through your network.

    [:material-arrow-right: Optimization results](../optimization.md)

</div>
