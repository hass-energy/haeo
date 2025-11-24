# Connections

Connections define how power flows between elements in your network with support for bidirectional flow, efficiency losses, and transmission costs.

## Configuration

| Field                        | Type                                     | Required | Default   | Description                                                            |
| ---------------------------- | ---------------------------------------- | -------- | --------- | ---------------------------------------------------------------------- |
| **Name**                     | String                                   | Yes      | -         | Unique identifier for this connection                                  |
| **Source**                   | Element                                  | Yes      | -         | Element where power can flow from (in source→target direction)         |
| **Target**                   | Element                                  | Yes      | -         | Element where power can flow to (in source→target direction)           |
| **Max Power Source→Target**  | [sensor](../forecasts-and-sensors.md)    | No       | Unlimited | Maximum power flow from source to target (kW)                          |
| **Max Power Target→Source**  | [sensor](../forecasts-and-sensors.md)    | No       | Unlimited | Maximum power flow from target to source (kW)                          |
| **Efficiency Source→Target** | [sensor](../forecasts-and-sensors.md)    | No       | 100%      | Efficiency percentage (0-100) for power transfer from source to target |
| **Efficiency Target→Source** | [sensor](../forecasts-and-sensors.md)    | No       | 100%      | Efficiency percentage (0-100) for power transfer from target to source |
| **Price Source→Target**      | [sensor(s)](../forecasts-and-sensors.md) | No       | 0         | Price (\$/kWh) for transferring power from source to target            |
| **Price Target→Source**      | [sensor(s)](../forecasts-and-sensors.md) | No       | 0         | Price (\$/kWh) for transferring power from target to source            |

!!! tip "Configuration tips"

    **Leaving fields unset**: When a direction should allow unlimited flow with no losses or costs, leave the corresponding fields empty rather than creating sensors with maximum or default values.

    **Using constant values**: All sensor fields require sensor entities.

Use [input number helpers](https://www.home-assistant.io/integrations/input_number/) to configure constant values.

## Configuration Example

Bidirectional connection between grid and battery:

| Field                       | Value                             |
| --------------------------- | --------------------------------- |
| **Name**                    | Grid to Battery                   |
| **Source**                  | Grid                              |
| **Target**                  | Battery                           |
| **Max Power Source→Target** | input_number.grid_charge_limit    |
| **Max Power Target→Source** | input_number.grid_discharge_limit |

## Physical Interpretation

**Bidirectional flow:**
Both directions are available for optimization.
The optimizer will choose the most cost-effective direction at each time step.

**Efficiency modeling:**
Power leaving a node is measured before losses.
Power arriving at a node is reduced by efficiency.
Example: 10kW leaves source with 95% efficiency → 9.5kW arrives at target.

**Asymmetric efficiency:**
Configure different efficiencies for each direction to model real-world devices.

**Transmission costs:**
Connection pricing models fees for using a power transfer path (wheeling charges, connection fees, peak demand charges).

## Common Patterns

### Unlimited Bidirectional Connection

Leave both power limits unset for unlimited flow in both directions:

| Field                       | Value           |
| --------------------------- | --------------- |
| **Name**                    | Solar to Main   |
| **Source**                  | Solar           |
| **Target**                  | Main Node       |
| **Max Power Source→Target** | _(leave empty)_ |
| **Max Power Target→Source** | _(leave empty)_ |

!!! note

    Solar will only produce, so reverse flow won't occur naturally.

### Unidirectional Connection

Set one direction's limit to 0 to prevent flow:

| Field                       | Value                  |
| --------------------------- | ---------------------- |
| **Name**                    | Solar to Main          |
| **Source**                  | Solar                  |
| **Target**                  | Main Node              |
| **Max Power Source→Target** | input_number.solar_max |
| **Max Power Target→Source** | input_number.zero      |

!!! note

    Set `input_number.zero` value to `0` to prevent reverse flow.

### Hybrid Inverter

Model AC-DC conversion with efficiency:

| Field                        | Value                            |
| ---------------------------- | -------------------------------- |
| **Name**                     | DC to AC Inverter                |
| **Source**                   | DC_Node                          |
| **Target**                   | AC_Node                          |
| **Max Power Source→Target**  | input_number.inverter_rating     |
| **Max Power Target→Source**  | input_number.inverter_rating     |
| **Efficiency Source→Target** | input_number.inverter_efficiency |
| **Efficiency Target→Source** | input_number.inverter_efficiency |

### Availability Windows

Use time-varying sensor to model device availability.
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

```yaml
Source: Grid
Target: EV_Battery
Max Power Source→Target: sensor.ev_charging_availability
```

The optimizer will only schedule charging when the sensor value is non-zero.

## Sensors Created

These sensors provide real-time visibility into power flow between elements.

| Sensor                                   | Unit | Description                                 |
| ---------------------------------------- | ---- | ------------------------------------------- |
| `sensor.{name}_power_flow_source_target` | kW   | Optimal power flowing from source to target |
| `sensor.{name}_power_flow_target_source` | kW   | Optimal power flowing from target to source |

Both sensors include a `forecast` attribute containing future optimized values for upcoming periods.

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

    [:material-arrow-right: Connection modeling](../../modeling/connections.md)

- :material-circle-outline:{ .lg .middle } **Node modeling**

    ---

    Learn about power balance at network nodes.

    [:material-arrow-right: Node modeling](../../modeling/node.md)

- :material-chart-line:{ .lg .middle } **Understand optimization**

    ---

    See how HAEO optimizes power flow through your network.

    [:material-arrow-right: Optimization results](../optimization.md)

- :material-bug:{ .lg .middle } **Troubleshoot issues**

    ---

    Resolve connection errors and graph connectivity problems.

    [:material-arrow-right: Troubleshooting guide](../troubleshooting.md)

</div>
