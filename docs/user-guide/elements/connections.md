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

| Field                       | Value                           |
| --------------------------- | ------------------------------- |
| **Name**                    | Grid to EV                      |
| **Source**                  | Grid                            |
| **Target**                  | EV_Battery                      |
| **Max Power Source→Target** | sensor.ev_charging_availability |

The optimizer will only schedule charging when the sensor value is non-zero.

## Sensors Created

These sensors provide real-time visibility into power flow and capacity constraints between elements.

| Sensor                                                                                    | Unit  | Description                          |
| ----------------------------------------------------------------------------------------- | ----- | ------------------------------------ |
| [`sensor.{name}_power_flow_source_target`](#power-flow-source-target)                     | kW    | Power flowing from source to target  |
| [`sensor.{name}_power_flow_target_source`](#power-flow-target-source)                     | kW    | Power flowing from target to source  |
| [`sensor.{name}_connection_max_power_source_target`](#connection-max-power-source-target) | \$/kW | Value of additional forward capacity |
| [`sensor.{name}_connection_max_power_target_source`](#connection-max-power-target-source) | \$/kW | Value of additional reverse capacity |

### Power Flow Source Target

The optimal power flowing from the source element to the target element.

Values are always positive or zero.
A value of 0 means no power is flowing in the forward direction (may be flowing in reverse or not at all).
The direction is determined by the connection configuration (source → target).

**Example**: A value of 3.5 kW means 3.5 kW is flowing from the source element to the target element at this time period.

### Power Flow Target Source

The optimal power flowing from the target element to the source element.

Values are always positive or zero.
A value of 0 means no power is flowing in the reverse direction (may be flowing forward or not at all).
This represents reverse flow through the connection (target → source).

**Example**: A value of 2.0 kW means 2.0 kW is flowing from the target element back to the source element at this time period.

### Connection Max Power Source Target

The marginal value of additional forward capacity (source → target).
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the forward power limit were increased by 1 kW at this time period.

**Interpretation**:

- **Zero value**: Connection has spare capacity in the forward direction (not at limit)
- **Positive value**: Connection is at maximum forward capacity and constraining power flow
    - The value shows how much system cost would decrease per kW of additional forward capacity
    - Higher values indicate the forward capacity limit is causing significant cost increases
    - Helps identify bottlenecks where more forward capacity would be valuable

**Example**: A value of 0.08 means that if the connection could transfer 1 kW more in the forward direction, the total system cost would decrease by \$0.08 at this time period.

### Connection Max Power Target Source

The marginal value of additional reverse capacity (target → source).
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the reverse power limit were increased by 1 kW at this time period.

**Interpretation**:

- **Zero value**: Connection has spare capacity in the reverse direction (not at limit)
- **Positive value**: Connection is at maximum reverse capacity and constraining power flow
    - The value shows how much system cost would decrease per kW of additional reverse capacity
    - Higher values indicate the reverse capacity limit is causing significant cost increases
    - Helps identify bottlenecks where more reverse capacity would be valuable

**Example**: A value of 0.12 means that if the connection could transfer 1 kW more in the reverse direction, the total system cost would decrease by \$0.12 at this time period.

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

    [:material-arrow-right: Connection modeling](../../modeling/connections.md)

- :material-circle-outline:{ .lg .middle } **Node modeling**

    ---

    Learn about power balance at network nodes.

    [:material-arrow-right: Node modeling](../../modeling/node.md)

- :material-chart-line:{ .lg .middle } **Understand optimization**

    ---

    See how HAEO optimizes power flow through your network.

    [:material-arrow-right: Optimization results](../optimization.md)

</div>
