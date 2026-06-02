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

## Configuration

| Field           | Type                                     | Required | Default   | Description                                         |
| --------------- | ---------------------------------------- | -------- | --------- | --------------------------------------------------- |
| **Name**        | String                                   | Yes      | -         | Unique identifier for this connection               |
| **Source**      | Element                                  | Yes      | -         | Element power flows from                            |
| **Target**      | Element                                  | Yes      | -         | Element power flows to                              |
| **Max power**   | [sensor](../forecasts-and-sensors.md)    | No       | Unlimited | Maximum power along this path (kW)                  |
| **Efficiency**  | [sensor](../forecasts-and-sensors.md)    | No       | 100%      | Efficiency percentage (0-100) for this direction    |
| **Price**       | [sensor(s)](../forecasts-and-sensors.md) | No       | 0         | Price (\$/kWh) for power transferred along this path |

!!! tip "Configuration tips"

    **Leaving fields unset**: When a path should allow unlimited flow with no losses or costs, leave the optional fields empty rather than creating sensors with maximum or default values.

    **Segment-based behavior**: Connections compose internal segments for limits, efficiency, and pricing.
    You configure the fields above, and the model applies the corresponding segment behavior automatically.

    **Using constant values**: All sensor fields require sensor entities.

Use [input number helpers](https://www.home-assistant.io/integrations/input_number/) to configure constant values.

### Connection Endpoint Selection

The **Source** and **Target** fields show a dropdown of available elements that can be used as connection endpoints.
The list of available elements is filtered based on connectivity level and your hub's Advanced Mode setting.

**Why filtering?**
Standard elements (Grid, Battery, Solar, Load) create implicit connections automatically.
Explicit connections between these elements are usually unnecessary and can lead to configuration errors.
The filtering hides these elements by default to prevent common mistakes.

**Filtering behavior:**

- Advanced elements that require manual connection setup always appear in the selector regardless of Advanced Mode.
- Standard elements that create implicit connections automatically only appear when Advanced Mode is enabled.
- Connection elements never appear as endpoints to prevent invalid connection topologies.

This filtering ensures that connection endpoints are appropriate for your configuration level.
Each element's documentation describes its connectivity level and when it appears in connection selectors.

## Configuration Examples

### One-way link between nodes

| Field         | Value                  |
| ------------- | ---------------------- |
| **Name**      | DC bus to AC bus       |
| **Source**    | DC Node                |
| **Target**    | AC Node                |
| **Max power** | input_number.max_power |

### Bidirectional link (two connections)

Create one connection for each direction when both paths need limits or different parameters:

| Connection | Source  | Target  | **Max power**              |
| ---------- | ------- | ------- | -------------------------- |
| DC to AC   | DC Node | AC Node | input_number.dc_to_ac_max  |
| AC to DC   | AC Node | DC Node | input_number.ac_to_dc_max  |

Use separate **Efficiency** and **Price** values on each connection when the directions differ.

!!! note "Advanced Mode required for standard elements"

    Examples that use Grid, Battery, Solar, or Load as endpoints require Advanced Mode on your hub so those elements appear in the selector.

## Physical Interpretation

**Unidirectional flow:**
Power optimized on this connection always travels from source to target.
Values are zero or positive in that direction.

**Efficiency modeling:**
Power leaving the source is measured before losses.
Power arriving at the target is reduced by efficiency.
Example: 10 kW leaves the source with 95% efficiency → 9.5 kW arrives at the target.

**Transmission costs:**
Connection pricing models fees for using a power transfer path (wheeling charges, connection fees, peak demand charges).

## Common Patterns

### Unlimited one-way connection

Leave **Max power** unset for unlimited flow in the configured direction:

| Field      | Value       |
| ---------- | ----------- |
| **Name**   | Bus A to B  |
| **Source** | Bus A       |
| **Target** | Bus B       |

### Conversion with efficiency

| Field          | Value                   |
| -------------- | ----------------------- |
| **Name**       | DC to AC                |
| **Source**     | DC Node                 |
| **Target**     | AC Node                 |
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
| **Name**      | Grid to EV                      |
| **Source**    | Grid                            |
| **Target**    | EV_Battery                      |
| **Max power** | sensor.ev_charging_availability |

!!! note "Advanced Mode required"

    This example uses standard elements that require Advanced Mode to appear in connection selectors.

The optimizer will only schedule charging when the sensor value is non-zero.

### Input Entities

Each optional configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                                   | Unit   | Description                        |
| --------------------------------------- | ------ | ---------------------------------- |
| `number.{name}_max_power_source_target` | kW     | Maximum power (if configured)      |
| `number.{name}_efficiency_source_target`| %      | Efficiency (if configured)         |
| `number.{name}_price_source_target`     | \$/kWh | Transfer price (if configured)     |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Connection element creates one device in Home Assistant.

The power sensor display name uses the configured source and target element names (for example, `{source} to {target} power`).

| Sensor                         | Unit | Description                              |
| ------------------------------ | ---- | ---------------------------------------- |
| `{source} to {target} power`   | kW   | Optimized power from source to target    |

Power values are zero or positive.
A value of 0 means no power is flowing on this connection at that time period.

**Example**: A value of 3.5 kW means 3.5 kW is flowing from the source element to the target element at that time period.

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

See [troubleshooting guide](../troubleshooting.md#graph-isnt-connected-properly) for connection issues.

## Next Steps

<div class="grid cards" markdown>

- :material-home-lightning-bolt:{ .lg .middle } **Complete your network**

    ---

    Review all configured elements and ensure proper connections.

    [:material-arrow-right: Elements overview](index.md)

- :material-math-integral:{ .lg .middle } **Connection modeling**

    ---

    Understand the mathematical formulation of power flows.

    [:material-arrow-right: Connection modeling](../../modeling/device-layer/connection.md)

- :material-circle-outline:{ .lg .middle } **Node modeling**

    ---

    Learn about power balance at network nodes.

    [:material-arrow-right: Node modeling](../../modeling/device-layer/node.md)

- :material-chart-line:{ .lg .middle } **Understand optimization**

    ---

    See how HAEO optimizes power flow through your network.

    [:material-arrow-right: Optimization results](../optimization.md)

</div>
