# Connections

Connections define how power flows between elements in your network with support for bidirectional flow, efficiency losses, and transmission costs.

!!! warning "Advanced Element"

    Connection is only available when **Advanced Mode** is enabled on your hub.
    This element is intended for advanced users who need explicit control over power flow paths.
    Most users should rely on implicit connections created automatically by other elements.

!!! note "Implicit connections"

    Many elements create implicit connections automatically.
    You only need explicit Connection elements for additional power paths not covered by element defaults.

## Configuration

| Field                        | Type                                     | Required | Default   | Description                                                            |
| ---------------------------- | ---------------------------------------- | -------- | --------- | ---------------------------------------------------------------------- |
| **Name**                     | String                                   | Yes      | -         | Unique identifier for this connection                                  |
| **Source**                   | Element                                  | Yes      | -         | Element where power can flow from (in source→target direction)         |
| **Target**                   | Element                                  | Yes      | -         | Element where power can flow to (in source→target direction)           |
| **Mirror segment order**     | Boolean                                  | No       | Off       | Use the same segment order for target→source flow                      |
| **Max Power Source→Target**  | [sensor](../forecasts-and-sensors.md)    | No       | Unlimited | Maximum power flow from source to target (kW)                          |
| **Max Power Target→Source**  | [sensor](../forecasts-and-sensors.md)    | No       | Unlimited | Maximum power flow from target to source (kW)                          |
| **Efficiency Source→Target** | [sensor](../forecasts-and-sensors.md)    | No       | 100%      | Efficiency percentage (0-100) for power transfer from source to target |
| **Efficiency Target→Source** | [sensor](../forecasts-and-sensors.md)    | No       | 100%      | Efficiency percentage (0-100) for power transfer from target to source |
| **Price Source→Target**      | [sensor(s)](../forecasts-and-sensors.md) | No       | 0         | Price (\$/kWh) for transferring power from source to target            |
| **Price Target→Source**      | [sensor(s)](../forecasts-and-sensors.md) | No       | 0         | Price (\$/kWh) for transferring power from target to source            |

!!! tip "Configuration tips"

    **Leaving fields unset**: When a direction should allow unlimited flow with no losses or costs, leave the corresponding fields empty rather than creating sensors with maximum or default values.

    **Segment-based behavior**: Connections compose internal segments for limits, efficiency, and pricing.
    You configure the fields above, and the model applies the corresponding segment behavior automatically.

    **Segment order**: Source→target uses the segment order you provide.
    Target→source uses the reverse order by default.
    Enable `Mirror segment order` to apply the same order in both directions.

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

## Configuration Example

Bidirectional connection between two network nodes:

| Field                       | Value                  |
| --------------------------- | ---------------------- |
| **Name**                    | DC Bus to AC Bus       |
| **Source**                  | DC Node                |
| **Target**                  | AC Node                |
| **Max Power Source→Target** | input_number.max_power |
| **Max Power Target→Source** | input_number.max_power |

!!! note "Advanced Mode required for standard elements"

    This example uses elements that are always available in connection selectors.
    To connect standard elements that create implicit connections, enable Advanced Mode on your hub.

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

| Field                       | Value            |
| --------------------------- | ---------------- |
| **Name**                    | DC Bus to AC Bus |
| **Source**                  | DC Node          |
| **Target**                  | AC Node          |
| **Max Power Source→Target** | _(leave empty)_  |
| **Max Power Target→Source** | _(leave empty)_  |

!!! note "Advanced Mode required for standard elements"

    This example uses elements that are always available in connection selectors.
    To connect standard elements that create implicit connections, enable Advanced Mode on your hub.

### Unidirectional Connection

Set one direction's limit to 0 to prevent flow:

| Field                       | Value                  |
| --------------------------- | ---------------------- |
| **Name**                    | DC Bus to AC Bus       |
| **Source**                  | DC Node                |
| **Target**                  | AC Node                |
| **Max Power Source→Target** | input_number.max_power |
| **Max Power Target→Source** | input_number.zero      |

!!! note

    Set `input_number.zero` value to `0` to prevent reverse flow.

### Bidirectional Connection with Efficiency

Model power conversion with efficiency losses:

| Field                        | Value                   |
| ---------------------------- | ----------------------- |
| **Name**                     | DC Bus to AC Bus        |
| **Source**                   | DC_Node                 |
| **Target**                   | AC_Node                 |
| **Max Power Source→Target**  | input_number.max_power  |
| **Max Power Target→Source**  | input_number.max_power  |
| **Efficiency Source→Target** | input_number.efficiency |
| **Efficiency Target→Source** | input_number.efficiency |

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

!!! note "Advanced Mode required"

    This example uses standard elements that require Advanced Mode to appear in connection selectors.

The optimizer will only schedule charging when the sensor value is non-zero.

### Input Entities

Each configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                                    | Unit   | Description                            |
| ---------------------------------------- | ------ | -------------------------------------- |
| `number.{name}_max_power_source_target`  | kW     | Maximum forward power (if configured)  |
| `number.{name}_max_power_target_source`  | kW     | Maximum reverse power (if configured)  |
| `number.{name}_efficiency_source_target` | %      | Forward efficiency (if configured)     |
| `number.{name}_efficiency_target_source` | %      | Reverse efficiency (if configured)     |
| `number.{name}_price_source_target`      | \$/kWh | Forward transfer price (if configured) |
| `number.{name}_price_target_source`      | \$/kWh | Reverse transfer price (if configured) |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Connection element creates 1 device in Home Assistant with the following sensors.
Not all sensors are created for every connection - only those relevant to the configuration.

The sensor display names use the actual source and target element names configured for the connection.
For example, a connection between two elements would show their actual names in the sensor name instead of generic "Source to Target".

| Sensor                                                                                     | Unit  | Description                             |
| ------------------------------------------------------------------------------------------ | ----- | --------------------------------------- |
| [`sensor.{name}_power_source_target`](#source-to-target-power)                             | kW    | Power flowing from source to target     |
| [`sensor.{name}_power_target_source`](#target-to-source-power)                             | kW    | Power flowing from target to source     |
| [`sensor.{name}_power_max_source_target`](#max-source-to-target-power)                     | kW    | Maximum forward power (when limited)    |
| [`sensor.{name}_power_max_target_source`](#max-target-to-source-power)                     | kW    | Maximum reverse power (when limited)    |
| [`sensor.{name}_shadow_power_max_source_target`](#max-source-to-target-power-shadow-price) | \$/kW | Value of additional forward capacity    |
| [`sensor.{name}_shadow_power_max_target_source`](#max-target-to-source-power-shadow-price) | \$/kW | Value of additional reverse capacity    |
| [`sensor.{name}_time_slice`](#time-slice-shadow-price)                                     | \$/kW | Value of relaxing time-slice constraint |

### Source to Target Power

The optimal power flowing from the source element to the target element.

Values are always positive or zero.
A value of 0 means no power is flowing in the forward direction (may be flowing in reverse or not at all).
The direction is determined by the connection configuration (source → target).

**Example**: A value of 3.5 kW means 3.5 kW is flowing from the source element to the target element at this time period.

### Target to Source Power

The optimal power flowing from the target element to the source element.

Values are always positive or zero.
A value of 0 means no power is flowing in the reverse direction (may be flowing forward or not at all).
This represents reverse flow through the connection (target → source).

**Example**: A value of 2.0 kW means 2.0 kW is flowing from the target element back to the source element at this time period.

### Max Source to Target Power

The configured maximum forward power limit from the sensor configuration.
Only created when a forward power limit is configured.

### Max Target to Source Power

The configured maximum reverse power limit from the sensor configuration.
Only created when a reverse power limit is configured.

### Max Source to Target Power Shadow Price

The marginal value of additional forward capacity (source → target).
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the forward power limit were increased by 1 kW at this time period.
Only created when a forward power limit is configured.

**Interpretation**:

- **Zero value**: Connection has spare capacity in the forward direction (not at limit)
- **Positive value**: Connection is at maximum forward capacity and constraining power flow
    - The value shows how much system cost would decrease per kW of additional forward capacity
    - Higher values indicate the forward capacity limit is causing significant cost increases
    - Helps identify bottlenecks where more forward capacity would be valuable

**Example**: A value of 0.08 means that if the connection could transfer 1 kW more in the forward direction, the total system cost would decrease by \$0.08 at this time period.

### Max Target to Source Power Shadow Price

The marginal value of additional reverse capacity (target → source).
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the reverse power limit were increased by 1 kW at this time period.
Only created when a reverse power limit is configured.

**Interpretation**:

- **Zero value**: Connection has spare capacity in the reverse direction (not at limit)
- **Positive value**: Connection is at maximum reverse capacity and constraining power flow
    - The value shows how much system cost would decrease per kW of additional reverse capacity
    - Higher values indicate the reverse capacity limit is causing significant cost increases
    - Helps identify bottlenecks where more reverse capacity would be valuable

**Example**: A value of 0.12 means that if the connection could transfer 1 kW more in the reverse direction, the total system cost would decrease by \$0.12 at this time period.

### Time Slice Shadow Price

The marginal value of relaxing the time-slicing constraint.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if simultaneous bidirectional power flow were less restricted at this time period.
Only created when both forward and reverse power limits are configured.

The time-slicing constraint prevents full power flow in both directions simultaneously: `P_forward/P_max_forward + P_reverse/P_max_reverse ≤ 1.0`.
This models real-world devices that share capacity between directions (e.g., an inverter that can't operate at full charge and discharge simultaneously).

**Interpretation**:

- **Zero value**: Connection is not constrained by time slicing (operating in only one direction or well below limits)
- **Positive value**: Time slicing is constraining bidirectional operation
    - The value shows how much system cost would decrease if the constraint were relaxed by 1% (allowing the sum to reach 1.01)
    - Higher values indicate the connection could benefit from being able to operate more simultaneously in both directions
    - Helps identify devices where increased bidirectional capacity would be valuable

**Example**: A value of 0.15 means that if the connection could operate slightly more simultaneously in both directions (sum ≤ 1.01 instead of ≤ 1.0), the total system cost would decrease by \$0.15 at this time period.

!!! warning "Unusual constraint binding"

    A positive time-slice shadow price is unusual and typically indicates misconfiguration.
    In most real-world scenarios, connections should not need to transfer power in both directions simultaneously.
    If this constraint is binding, it often suggests arbitrage opportunities caused by:

    - Inconsistent pricing across elements (e.g., different import/export prices creating profitable round-trip power flow)
    - Efficiency values greater than 100% allowing energy creation through cycling
    - Connection prices that don't reflect the true cost of bidirectional operation

    Review your element configurations to ensure prices, efficiencies, and power limits accurately represent the physical system.

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
