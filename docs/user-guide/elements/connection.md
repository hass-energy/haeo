# Connections

Connections define explicit, **unidirectional** power paths between elements, through an ordered chain of limits, efficiency losses, and transfer prices.

!!! warning "Raw model element"

    Connection is only available when **Expose raw model elements** is enabled on your hub.
    This element is for explicit control over power flow paths when you are building the model yourself.
    Most users should rely on implicit connections created automatically by other elements.

!!! note "Implicit connections"

    Many elements create implicit connections automatically.
    You only need explicit Connection elements for additional power paths not covered by element defaults.

!!! note "Bidirectional paths"

    Each Connection flows from **source** to **target** only.
    To model flow in both directions (for example between two buses), add **two** Connection elements with swapped endpoints, each with its own segments.
    For AC/DC conversion between a battery or solar and the grid, consider the [Inverter](inverter.md) element instead.

!!! info "Upgrading from bidirectional connections"

    Earlier versions configured both directions on a single connection.
    On upgrade, each existing connection keeps its source-to-target settings.
    If any reverse setting (max power, price, or efficiency) was set, a second connection named `{name} ({target} to {source})` is created carrying those settings.
    No reverse connection is created when no reverse setting was set or the reverse max power was 0.
    If a connection with swapped endpoints already exists, the reverse settings are merged into it instead.
    Add a reverse connection yourself if power should flow both ways.

## Configuration

A connection is a chain, read top to bottom in the direction power flows: its **source**, then each **segment** in the order it applies, then its **target**.

| Field        | Type    | Required | Default | Description                                    |
| ------------ | ------- | -------- | ------- | ---------------------------------------------- |
| **Name**     | String  | Yes      | -       | Unique identifier for this connection          |
| **Source**   | Element | Yes      | -       | Element power flows from, at the top           |
| **Segments** | List    | No       | None    | What happens to the power on its way, in order |
| **Target**   | Element | Yes      | -       | Element power flows to, at the bottom          |

Each segment takes one [fixed value or sensor](../configuration.md#input-fields):

| Segment        | Value                                    | Effect on the power passing through it |
| -------------- | ---------------------------------------- | -------------------------------------- |
| **Limit**      | [sensor](../forecasts-and-sensors.md)    | Caps it at the maximum power (kW)      |
| **Price**      | [sensor(s)](../forecasts-and-sensors.md) | Charges the price on it (\$/kWh)       |
| **Efficiency** | [sensor](../forecasts-and-sensors.md)    | Loses the rest of it (0-100%)          |

Press **+** on a link in the chain to add a segment at that point, and use the arrows on a segment to move it earlier or later.
A connection with no segments carries any amount of power, with no losses and no cost.
The same kind of segment can appear more than once, such as a limit on each side of an efficiency.

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

!!! info "Upgrading from limit, price, and efficiency fields"

    Earlier versions had one **Max power**, **Price**, and **Efficiency** field per connection.
    On upgrade, each one that was set becomes a segment, in the order they always applied: the limit, then the price, then the efficiency.

### Order matters

A segment works on the power as it reaches that point in the chain.
A limit or price before an efficiency counts the power before its losses, and one after counts the power that is left.

Example: an efficiency of 95% followed by a 10 kW limit lets 10.5 kW enter the connection, so that 10 kW arrives.
The same limit before the efficiency lets 10 kW enter, so that 9.5 kW arrives.

### Connection endpoint selection

Elements attach to each other through endpoints: points in your network where power from several elements meets and is shared, such as a [Junction](junction.md).
The **Connection** field of each element, and the **Source** and **Target** of a connection, list only endpoints.

Elements that apply their own prices, forecasts, or limits on their own connection are not endpoints, because a connection made directly to them would bypass those.
Connect to the endpoint such an element is attached to instead.

If an existing configuration connects directly to an element that is not an endpoint, HAEO raises a repair issue listing each affected connection.

## Configuration examples

### One-way link between junctions

| Field        | Value                         |
| ------------ | ----------------------------- |
| **Name**     | DC bus to AC bus              |
| **Source**   | DC Bus                        |
| **Segments** | Limit: input_number.max_power |
| **Target**   | AC Bus                        |

### Bidirectional link (two connections)

Create one connection for each direction when both paths need limits or different parameters:

| Connection | Source | Segments                         | Target |
| ---------- | ------ | -------------------------------- | ------ |
| DC to AC   | DC Bus | Limit: input_number.dc_to_ac_max | AC Bus |
| AC to DC   | AC Bus | Limit: input_number.ac_to_dc_max | DC Bus |

Give each connection its own efficiency and price segments when the directions differ.

## Physical interpretation

**Unidirectional flow:**
Power optimized on this connection always travels from source to target.
Values are zero or positive in that direction.

**Reported power:**
The connection's power sensor reports the power entering its last limit, or entering the connection when it has no limit.
So a connection at its limit reports the limit.

**Transmission costs:**
Price segments model fees for using a power transfer path (wheeling charges, connection fees, peak demand charges).

## Common patterns

### Unlimited one-way connection

Leave out every segment for unlimited flow in the configured direction:

| Field      | Value      |
| ---------- | ---------- |
| **Name**   | Bus A to B |
| **Source** | Bus A      |
| **Target** | Bus B      |

### Conversion with efficiency

| Field        | Value                                                       |
| ------------ | ----------------------------------------------------------- |
| **Name**     | DC to AC                                                    |
| **Source**   | DC Bus                                                      |
| **Segments** | Limit: input_number.max_power, Efficiency: input_number.eff |
| **Target**   | AC Bus                                                      |

Add a second connection (AC → DC) with its own efficiency if reverse conversion is required.

### Availability windows

Use a time-varying sensor for a **Limit** segment to model device availability.
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

| Field        | Value                                  |
| ------------ | -------------------------------------- |
| **Name**     | Switchboard to EV                      |
| **Source**   | Switchboard                            |
| **Segments** | Limit: sensor.ev_charging_availability |
| **Target**   | EV Battery                             |

!!! note "Battery Section endpoint"

    `EV Battery` is a [Battery Section](battery_section.md).
    Power reaches it through the Switchboard, so the grid import price still applies to the charging energy.

The optimizer will only schedule charging when the sensor value is non-zero.

### Input entities

Each segment creates an input entity on the connection's device, named by its position in the chain.
Input entities appear as Number entities with the `config` entity category.
Their IDs combine the connection's name with the entity's name.

| Input                                         | Unit   | Description                         |
| --------------------------------------------- | ------ | ----------------------------------- |
| `number.{name}_segment_{position}_max_power`  | kW     | Maximum power of a limit segment    |
| `number.{name}_segment_{position}_efficiency` | %      | Efficiency of an efficiency segment |
| `number.{name}_segment_{position}_price`      | \$/kWh | Transfer price of a price segment   |

A segment set to a fixed value can be adjusted from its input entity at runtime.
A segment linked to sensors shows the values HAEO reads from them.
Moving a segment changes its position, and so the input entity it uses.

Input entities include a `forecast` attribute showing values for each optimization period.
See [How data updates work](../data-updates.md) for how input entities receive their values.

## Sensors created

### Sensor summary

A Connection element creates one device in Home Assistant.

The power sensor display name uses the configured source and target element names (for example, `{source} to {target} power`).

| Sensor                                     | Unit | Description                                                  |
| ------------------------------------------ | ---- | ------------------------------------------------------------ |
| `sensor.{name}_{source}_to_{target}_power` | kW   | Optimized power leaving the source, before efficiency losses |

For example, a connection named "DC to AC" from "DC Bus" to "AC Bus" has `sensor.dc_to_ac_dc_bus_to_ac_bus_power`.

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
