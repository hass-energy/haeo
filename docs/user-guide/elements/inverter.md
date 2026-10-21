# Inverter

Inverters convert power between DC and AC systems.
They provide a DC bus for connecting batteries and solar panels, with bidirectional power conversion to an AC network.

## Configuration

| Field                                         | Type                                  | Required | Default | Description                                                                          |
| --------------------------------------------- | ------------------------------------- | -------- | ------- | ------------------------------------------------------------------------------------ |
| **[Name](#name)**                             | String                                | Yes      | -       | Unique identifier for this inverter                                                  |
| **[Connection](#connection)**                 | Element                               | Yes      | -       | [Endpoint](connection.md#connection-endpoint-selection) on the AC side to connect to |
| **[Max Power DC to AC](#max-power-dc-to-ac)** | [sensor](../forecasts-and-sensors.md) | No       | -       | Maximum power when converting DC to AC (kW)                                          |
| **[Max Power AC to DC](#max-power-ac-to-dc)** | [sensor](../forecasts-and-sensors.md) | No       | -       | Maximum power when converting AC to DC (kW)                                          |
| **Efficiency DC to AC**                       | Number (%)                            | No       | 100     | Efficiency percentage when inverting DC to AC (0-100)                                |
| **Efficiency AC to DC**                       | Number (%)                            | No       | 100     | Efficiency percentage when rectifying AC to DC (0-100)                               |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

## Name

Unique identifier for this inverter within your HAEO configuration.
Used to create sensor entity IDs and identify the inverter in connections.

**Examples**: "Main Inverter", "Hybrid Inverter", "Solar Inverter"

## Connection

The AC side node where the inverter connects.
This is typically your home's main electrical bus, such as the Switchboard junction.

Other elements (batteries, solar panels) connect to the inverter's DC bus by specifying the inverter name as their connection target.

## Max power DC to AC

Maximum power the inverter can convert from DC to AC (inverting direction).
Leave empty for unlimited power.

Enter the inverter's rated AC power.
The limit applies on the AC side, so a 5 kW limit means at most 5 kW reaches the AC network, and the DC bus supplies that plus the conversion loss.

Use a sensor to model time-varying power limits, or an input number helper for a constant value.

## Max power AC to DC

Maximum power the inverter can convert from AC to DC (rectifying direction).
Leave empty for unlimited power.

Enter the inverter's rated AC power for charging from the AC side.
The limit applies on the AC side, so a 5 kW limit means at most 5 kW is drawn from the AC network, and the DC bus receives that less the conversion loss.

Use a sensor to model time-varying power limits, or an input number helper for a constant value.

## Efficiency DC to AC

Efficiency percentage when converting DC to AC power (inverting).
Typical modern inverters achieve 95-98% efficiency.

**Default**: 100% (no losses)

## Efficiency AC to DC

Efficiency percentage when converting AC to DC power (rectifying).
Rectifying efficiency may differ from inverting efficiency.

**Default**: 100% (no losses)

## Configuration examples

### Basic hybrid inverter

| Field                   | Value         |
| ----------------------- | ------------- |
| **Name**                | Main Inverter |
| **Connection**          | Home Bus      |
| **Efficiency DC to AC** | 97.0          |
| **Efficiency AC to DC** | 97.0          |

### With power limits

| Field                   | Value                        |
| ----------------------- | ---------------------------- |
| **Name**                | Hybrid Inverter              |
| **Connection**          | Home Bus                     |
| **Efficiency DC to AC** | 96.0                         |
| **Efficiency AC to DC** | 95.0                         |
| **Max Power DC to AC**  | input_number.inverter_rating |
| **Max Power AC to DC**  | input_number.inverter_rating |

### Asymmetric power ratings

Some inverters have different power ratings for inverting vs. rectifying.

| Field                   | Value                         |
| ----------------------- | ----------------------------- |
| **Name**                | Solar Inverter                |
| **Connection**          | AC Panel                      |
| **Efficiency DC to AC** | 97.5                          |
| **Efficiency AC to DC** | 96.0                          |
| **Max Power DC to AC**  | input_number.inverter_max_5kw |
| **Max Power AC to DC**  | input_number.inverter_max_3kw |

### Input entities

Each field you configure creates an input entity on the inverter's device.
Input entities appear as Number entities with the `config` entity category.
Their IDs combine the inverter's name with the entity's name, so an inverter named "Inverter" has `number.inverter_max_dc_to_ac_power`.

| Input                               | Unit | Description                            |
| ----------------------------------- | ---- | -------------------------------------- |
| `number.{name}_max_dc_to_ac_power`  | kW   | Maximum DC to AC power (if configured) |
| `number.{name}_max_ac_to_dc_power`  | kW   | Maximum AC to DC power (if configured) |
| `number.{name}_dc_to_ac_efficiency` | %    | Efficiency DC to AC (if configured)    |
| `number.{name}_ac_to_dc_efficiency` | %    | Efficiency AC to DC (if configured)    |

A field set to "Constant" can be adjusted from its input entity at runtime.
A field linked to sensors shows the values HAEO reads from them.

Input entities include a `forecast` attribute showing values for each optimization period.
See [How data updates work](../data-updates.md) for how input entities receive their values.

## Sensors created

### Sensor summary

An Inverter element creates 1 device in Home Assistant with the following sensors.
The max power shadow price sensors are only created when the corresponding power limit is configured.

| Sensor                                                                                  | Unit   | Description                              |
| --------------------------------------------------------------------------------------- | ------ | ---------------------------------------- |
| [`sensor.{name}_dc_to_ac_power`](#dc-to-ac-power)                                       | kW     | Power flowing from DC to AC (inverting)  |
| [`sensor.{name}_ac_to_dc_power`](#ac-to-dc-power)                                       | kW     | Power flowing from AC to DC (rectifying) |
| [`sensor.{name}_active_power`](#active-power)                                           | kW     | Net power (DC to AC - AC to DC)          |
| [`sensor.{name}_dc_bus_power_balance_shadow_price`](#dc-bus-power-balance-shadow-price) | \$/kWh | DC bus power balance shadow price        |
| [`sensor.{name}_max_dc_to_ac_power_shadow_price`](#shadow-prices)                       | \$/kWh | Maximum DC to AC power shadow price      |
| [`sensor.{name}_max_ac_to_dc_power_shadow_price`](#shadow-prices)                       | \$/kWh | Maximum AC to DC power shadow price      |

### DC to AC power

The optimal power flowing from the DC bus to the AC network (inverting direction), measured on the AC side.
Values are always positive or zero.

**Example**: A value of 3.5 kW means the inverter is converting 3.5 kW from DC to AC at this time period.

### AC to DC power

The optimal power flowing from the AC network to the DC bus (rectifying direction), measured on the AC side.
Values are always positive or zero.

**Example**: A value of 2.0 kW means the inverter is converting 2.0 kW from AC to DC at this time period.

### Active power

The net power flow through the inverter (DC to AC minus AC to DC), measured on the AC side.
Positive values indicate net DC to AC conversion.
Negative values indicate net AC to DC conversion.

**Example**: A value of 1.5 kW means the inverter is net converting 1.5 kW from DC to AC (e.g., 3.5 kW DC to AC and 2.0 kW AC to DC).

### DC bus power balance shadow price

The marginal value of power balance at the DC bus.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the DC bus power balance constraint were relaxed.

**Interpretation**:

- **Zero value**: DC bus power is balanced (no constraint binding)
- **Nonzero value**: DC bus power balance is constraining the optimization
    - The value shows how much system cost would decrease if the balance constraint were relaxed
    - Helps identify when DC devices (batteries, solar) are not optimally balanced

### Shadow prices

The marginal value of additional power capacity in each direction.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

These shadow prices show how much the total system cost would decrease if the power limit were increased by 1 kW at this time period.
Only created when the corresponding power limit is configured.

**Interpretation**:

- **Zero value**: Inverter has spare capacity in this direction (not at limit)
- **Positive value**: Inverter is at maximum capacity and constraining power flow
    - The value shows how much system cost would decrease per kW of additional capacity
    - Higher values indicate the power limit is causing significant cost increases

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

### DC bus power balance issues

**Problem**: DC bus power balance shadow price is consistently high.

**Solution**: Check that DC devices (batteries, solar) are properly connected to the inverter's DC bus.
Verify power limits and efficiency values are realistic.

### Efficiency values too high

**Problem**: Optimization results seem unrealistic.

**Solution**: Typical modern inverters achieve 95-98% efficiency.
Set efficiency values slightly lower to account for real-world losses.
Avoid using 100% efficiency unless your inverter truly has no losses.

## Next steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect DC devices**

    ---

    Connect batteries and solar panels to the inverter's DC bus.

    [:material-arrow-right: Connections guide](connection.md)

- :material-battery-charging:{ .lg .middle } **Configure battery**

    ---

    Set up battery storage connected to the inverter.

    [:material-arrow-right: Battery setup](battery.md)

- :material-weather-sunny:{ .lg .middle } **Add solar panels**

    ---

    Connect solar generation to the inverter's DC bus.

    [:material-arrow-right: Solar configuration](solar.md)

- :material-math-integral:{ .lg .middle } **Inverter modeling**

    ---

    Understand the mathematical formulation of inverter operation.

    [:material-arrow-right: Inverter modeling](../../modeling/device-layer/inverter.md)

</div>
