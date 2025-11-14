# Connections

Connections define how power flows between elements in your network with support for bidirectional flow, efficiency losses, and transmission costs.

## Configuration Fields

| Field                        | Type                                                | Description                                                                                                               |
| ---------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Name**                     | text                                                | Unique name for this connection                                                                                           |
| **Source**                   | element                                             | Element where power can flow from (in the source→target direction)                                                        |
| **Target**                   | element                                             | Element where power can flow to (in the source→target direction)                                                          |
| **Max Power Source→Target**  | [sensor](../forecasts-and-sensors.md) (optional)    | Maximum power flow from source to target (kW). If not set, flow is unlimited. Set to 0 to prevent flow in this direction. |
| **Max Power Target→Source**  | [sensor](../forecasts-and-sensors.md) (optional)    | Maximum power flow from target to source (kW). If not set, flow is unlimited. Set to 0 to prevent flow in this direction. |
| **Efficiency Source→Target** | [sensor](../forecasts-and-sensors.md) (optional)    | Efficiency percentage (0-100) for power transfer from source to target. Defaults to 100% (no losses) if not set.          |
| **Efficiency Target→Source** | [sensor](../forecasts-and-sensors.md) (optional)    | Efficiency percentage (0-100) for power transfer from target to source. Defaults to 100% (no losses) if not set.          |
| **Price Source→Target**      | [sensor(s)](../forecasts-and-sensors.md) (optional) | Price in \$/kWh for transferring power from source to target. If not set, no cost is applied.                             |
| **Price Target→Source**      | [sensor(s)](../forecasts-and-sensors.md) (optional) | Price in \$/kWh for transferring power from target to source. If not set, no cost is applied.                             |

!!! tip "Using constant values"

    All sensor fields require sensor entities.
    Use [input number helpers](https://www.home-assistant.io/integrations/input_number/) to configure constant values.

## Configuration Example

Bidirectional connection between grid and battery:

```yaml
Name: Grid to Battery
Source: Grid
Target: Battery
Max Power Source→Target: input_number.grid_charge_limit
Max Power Target→Source: input_number.grid_discharge_limit
```

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

```yaml
Source: Solar
Target: Net
# No power limits - unlimited bidirectional flow
# Solar will only produce, so reverse flow won't occur naturally
```

### Unidirectional Connection

Set one direction's limit to 0 to prevent flow:

```yaml
Source: Solar
Target: Net
Max Power Source→Target: input_number.solar_max
Max Power Target→Source: input_number.zero  # Value = 0
```

### Hybrid Inverter

Model AC-DC conversion with efficiency:

```yaml
Source: DC_Net
Target: AC_Net
Max Power Source→Target: input_number.inverter_rating
Max Power Target→Source: input_number.inverter_rating
Efficiency Source→Target: input_number.inverter_efficiency
Efficiency Target→Source: input_number.inverter_efficiency
```

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

Connections create the following sensors:

| Sensor                   | Unit | Description                         |
| ------------------------ | ---- | ----------------------------------- |
| Power Flow Source→Target | kW   | Power flowing from source to target |
| Power Flow Target→Source | kW   | Power flowing from target to source |

## Troubleshooting

See [troubleshooting guide](../troubleshooting.md#graph-isnt-connected-properly) for connection issues.

## Related Documentation

- [Connection Modeling](../../modeling/connections.md)
- [Node Modeling](../../modeling/node.md)
- [Forecasts and Sensors](../forecasts-and-sensors.md)

## Next Steps

<div class="grid cards" markdown>

- :material-home-lightning-bolt:{ .lg .middle } **Complete your network**

    ---

    Review all configured elements and ensure proper connections.

    [:material-arrow-right: Elements overview](index.md)

- :material-chart-line:{ .lg .middle } **Understand optimization**

    ---

    See how HAEO optimizes power flow through your network.

    [:material-arrow-right: Optimization results](../optimization.md)

- :material-bug:{ .lg .middle } **Troubleshoot issues**

    ---

    Resolve connection errors and graph connectivity problems.

    [:material-arrow-right: Troubleshooting guide](../troubleshooting.md)

</div>
