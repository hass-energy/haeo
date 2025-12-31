# Inverter

Inverters convert power between DC and AC systems.
They provide a DC bus for connecting batteries and solar panels, with bidirectional power conversion to an AC network.

!!! note "Connection endpoints"

    Inverter elements always appear in connection selectors regardless of Advanced Mode setting.

## Configuration

| Field                                      | Type                                  | Required | Default | Description                                            |
| ------------------------------------------ | ------------------------------------- | -------- | ------- | ------------------------------------------------------ |
| **[Name](#name)**                          | String                                | Yes      | -       | Unique identifier for this inverter                    |
| **[Connection](#connection)**              | Element                               | Yes      | -       | AC side node to connect to                             |
| **[Max Power DC→AC](#max-power-dc-to-ac)** | [sensor](../forecasts-and-sensors.md) | No       | -       | Maximum power when converting DC to AC (kW)            |
| **[Max Power AC→DC](#max-power-ac-to-dc)** | [sensor](../forecasts-and-sensors.md) | No       | -       | Maximum power when converting AC to DC (kW)            |
| **Efficiency DC→AC**                       | Number (%)                            | No       | 100     | Efficiency percentage when inverting DC to AC (0-100)  |
| **Efficiency AC→DC**                       | Number (%)                            | No       | 100     | Efficiency percentage when rectifying AC to DC (0-100) |

## Name

Unique identifier for this inverter within your HAEO configuration.
Used to create sensor entity IDs and identify the inverter in connections.

**Examples**: "Main Inverter", "Hybrid Inverter", "Solar Inverter"

## Connection

The AC side node where the inverter connects.
This is typically your home's main electrical bus or switchboard node.

Other elements (batteries, solar panels) connect to the inverter's DC bus by specifying the inverter name as their connection target.

## Max Power DC→AC

Maximum power the inverter can convert from DC to AC (inverting direction).
Leave empty for unlimited power.

Use a sensor to model time-varying power limits, or an input number helper for a constant value.

## Max Power AC→DC

Maximum power the inverter can convert from AC to DC (rectifying direction).
Leave empty for unlimited power.

Use a sensor to model time-varying power limits, or an input number helper for a constant value.

## Efficiency DC→AC

Efficiency percentage when converting DC to AC power (inverting).
Typical modern inverters achieve 95-98% efficiency.

**Default**: 100% (no losses)

## Efficiency AC→DC

Efficiency percentage when converting AC to DC power (rectifying).
Rectifying efficiency may differ from inverting efficiency.

**Default**: 100% (no losses)

## Configuration Examples

### Basic Hybrid Inverter

| Field                | Value         |
| -------------------- | ------------- |
| **Name**             | Main Inverter |
| **Connection**       | Home Bus      |
| **Efficiency DC→AC** | 97.0          |
| **Efficiency AC→DC** | 97.0          |

### With Power Limits

| Field                | Value                        |
| -------------------- | ---------------------------- |
| **Name**             | Hybrid Inverter              |
| **Connection**       | Home Bus                     |
| **Efficiency DC→AC** | 96.0                         |
| **Efficiency AC→DC** | 95.0                         |
| **Max Power DC→AC**  | input_number.inverter_rating |
| **Max Power AC→DC**  | input_number.inverter_rating |

### Asymmetric Power Ratings

Some inverters have different power ratings for inverting vs. rectifying.

| Field                | Value                         |
| -------------------- | ----------------------------- |
| **Name**             | Solar Inverter                |
| **Connection**       | AC Panel                      |
| **Efficiency DC→AC** | 97.5                          |
| **Efficiency AC→DC** | 96.0                          |
| **Max Power DC→AC**  | input_number.inverter_max_5kw |
| **Max Power AC→DC**  | input_number.inverter_max_3kw |

### Input Entities

Each configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                            | Unit | Description                              |
| -------------------------------- | ---- | ---------------------------------------- |
| `number.{name}_max_import_power` | kW   | Maximum AC→DC power (if configured)      |
| `number.{name}_max_export_power` | kW   | Maximum DC→AC power (if configured)      |
| `number.{name}_charge_soc_min`   | %    | Minimum SOC for charging (if configured) |
| `number.{name}_charge_soc_max`   | %    | Maximum SOC for charging (if configured) |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

An Inverter element creates 1 device in Home Assistant with the following sensors.
Not all sensors are created for every inverter - only those relevant to the configuration.

| Sensor                                                        | Unit  | Description                              |
| ------------------------------------------------------------- | ----- | ---------------------------------------- |
| [`sensor.{name}_power_dc_to_ac`](#dc-to-ac-power)             | kW    | Power flowing from DC to AC (inverting)  |
| [`sensor.{name}_power_ac_to_dc`](#ac-to-dc-power)             | kW    | Power flowing from AC to DC (rectifying) |
| [`sensor.{name}_power_active`](#active-power)                 | kW    | Net power (DC to AC - AC to DC)          |
| [`sensor.{name}_dc_bus_power_balance`](#dc-bus-power-balance) | \$/kW | DC bus power balance shadow price        |
| [`sensor.{name}_max_power_dc_to_ac`](#max-power-dc-to-ac)     | kW    | Maximum DC to AC power (when limited)    |
| [`sensor.{name}_max_power_ac_to_dc`](#max-power-ac-to-dc)     | kW    | Maximum AC to DC power (when limited)    |
| [`sensor.{name}_max_power_dc_to_ac_price`](#shadow-prices)    | \$/kW | Maximum DC to AC power shadow price      |
| [`sensor.{name}_max_power_ac_to_dc_price`](#shadow-prices)    | \$/kW | Maximum AC to DC power shadow price      |

### DC to AC Power

The optimal power flowing from the DC bus to the AC network (inverting direction).
Values are always positive or zero.

**Example**: A value of 3.5 kW means the inverter is converting 3.5 kW from DC to AC at this time period.

### AC to DC Power

The optimal power flowing from the AC network to the DC bus (rectifying direction).
Values are always positive or zero.

**Example**: A value of 2.0 kW means the inverter is converting 2.0 kW from AC to DC at this time period.

### Active Power

The net power flow through the inverter (DC to AC minus AC to DC).
Positive values indicate net DC to AC conversion.
Negative values indicate net AC to DC conversion.

**Example**: A value of 1.5 kW means the inverter is net converting 1.5 kW from DC to AC (e.g., 3.5 kW DC→AC and 2.0 kW AC→DC).

### DC Bus Power Balance

The marginal value of power balance at the DC bus.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the DC bus power balance constraint were relaxed.

**Interpretation**:

- **Zero value**: DC bus power is balanced (no constraint binding)
- **Nonzero value**: DC bus power balance is constraining the optimization
    - The value shows how much system cost would decrease if the balance constraint were relaxed
    - Helps identify when DC devices (batteries, solar) are not optimally balanced

### Max Power DC to AC

The configured maximum DC to AC power limit from the sensor configuration.
Only created when a DC to AC power limit is configured.

### Max Power AC to DC

The configured maximum AC to DC power limit from the sensor configuration.
Only created when an AC to DC power limit is configured.

### Shadow Prices

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

### Inverter not appearing in connection selectors

**Problem**: Other elements cannot select the inverter as a connection target.

**Solution**: Verify the inverter name matches exactly.
Connection selectors show all configured elements that can be used as endpoints.

### DC bus power balance issues

**Problem**: DC bus power balance shadow price is consistently high.

**Solution**: Check that DC devices (batteries, solar) are properly connected to the inverter's DC bus.
Verify power limits and efficiency values are realistic.

### Efficiency values too high

**Problem**: Optimization results seem unrealistic.

**Solution**: Typical modern inverters achieve 95-98% efficiency.
Set efficiency values slightly lower to account for real-world losses.
Avoid using 100% efficiency unless your inverter truly has no losses.

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect DC devices**

    ---

    Connect batteries and solar panels to the inverter's DC bus.

    [:material-arrow-right: Connections guide](connections.md)

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
