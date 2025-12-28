# Battery Section

Battery Section is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection elements.

!!! warning "Advanced Element"

    Battery Section is only available when **Advanced Mode** is enabled on your hub.
    This element is intended for advanced users who need direct control over battery modeling.
    Most users should use the standard [Battery](battery.md) element instead.

!!! note "Connection endpoints"

    Battery Section elements always appear in connection selectors regardless of Advanced Mode setting.

For mathematical details, see [Battery Section Modeling](../../modeling/device-layer/battery_section.md).

## Configuration

### Overview

A Battery Section element represents:

- **Single battery section** with capacity and initial charge
- **No implicit connections** - must be connected explicitly via Connection elements
- **Direct model access** - maps directly to the model layer Battery element without additional composition

Unlike the standard Battery element, Battery Section does not create:

- Multiple SOC sections (undercharge, normal, overcharge)
- Internal node for power routing
- Implicit connections to other elements

You must manually create Connection elements to connect the Battery Section to your network.

## Configuration Fields

| Field                                 | Type                                  | Required | Default | Description                                   |
| ------------------------------------- | ------------------------------------- | -------- | ------- | --------------------------------------------- |
| **[Name](#name)**                     | String                                | Yes      | -       | Unique identifier (e.g., "Battery Section 1") |
| **[Capacity](#capacity)**             | [sensor](../forecasts-and-sensors.md) | Yes      | -       | Battery capacity in kWh (can vary over time)  |
| **[Initial Charge](#initial-charge)** | [sensor](../forecasts-and-sensors.md) | Yes      | -       | Initial energy stored in battery (kWh)        |

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Capacity

Select a Home Assistant sensor that reports the battery capacity in kWh.
The sensor can provide a constant value or a forecast with time-varying capacity.

The optimizer uses this value to enforce state of charge constraints.

### Initial Charge

Select a Home Assistant sensor that reports the initial energy stored in the battery in kWh.
This represents the battery's state of charge at the start of the optimization window.

The sensor should provide a single current value (not a forecast).

## Configuration Example

Basic battery section configuration:

| Field              | Value                   |
| ------------------ | ----------------------- |
| **Name**           | Battery Section 1       |
| **Capacity**       | sensor.battery_capacity |
| **Initial Charge** | sensor.battery_energy   |

After creating the Battery Section element, you must create Connection elements to connect it to other elements in your network (nodes, grids, etc.).

## Sensors Created

A Battery Section element creates 1 device in Home Assistant with the following sensors.

| Sensor                                                              | Unit   | Description                                 |
| ------------------------------------------------------------------- | ------ | ------------------------------------------- |
| [`sensor.{name}_battery_section_power_charge`](#power-charge)       | kW     | Power being charged into the battery        |
| [`sensor.{name}_battery_section_power_discharge`](#power-discharge) | kW     | Power being discharged from the battery     |
| [`sensor.{name}_battery_section_power_active`](#power-active)       | kW     | Net active power (discharge - charge)       |
| [`sensor.{name}_battery_section_energy_stored`](#energy-stored)     | kWh    | Current energy stored in the battery        |
| [`sensor.{name}_battery_section_power_balance`](#power-balance)     | \$/kW  | Shadow price of power at battery terminals  |
| [`sensor.{name}_battery_section_energy_in_flow`](#energy-in-flow)   | \$/kWh | Shadow price of charging constraint         |
| [`sensor.{name}_battery_section_energy_out_flow`](#energy-out-flow) | \$/kWh | Shadow price of discharging constraint      |
| [`sensor.{name}_battery_section_soc_max`](#soc-max)                 | \$/kWh | Shadow price of maximum capacity constraint |
| [`sensor.{name}_battery_section_soc_min`](#soc-min)                 | \$/kWh | Shadow price of minimum capacity constraint |

### Power Charge

The optimal power being charged into the battery at each time period.
Values are always positive or zero.

**Example**: A value of 3.5 kW means the battery is charging at 3.5 kW at this time period.

### Power Discharge

The optimal power being discharged from the battery at each time period.
Values are always positive or zero.

**Example**: A value of 2.0 kW means the battery is discharging at 2.0 kW at this time period.

### Power Active

The net active power (discharge - charge) at each time period.
Positive values indicate net discharge, negative values indicate net charge.

**Example**: A value of -1.5 kW means the battery is charging at 1.5 kW net (discharge is less than charge).

### Energy Stored

The current energy stored in the battery at each time boundary.
Values range from 0 to the configured capacity.

**Example**: A value of 7.5 kWh means the battery currently stores 7.5 kWh of energy.

### Power Balance

The marginal value of power at the battery terminals.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would change if you could inject or extract 1 kW of power at the battery terminals.

**Interpretation**:

- **Positive value**: Power at the battery is valuable (system would benefit from more charging capacity)
- **Negative value**: Power at the battery is costly (system would benefit from more discharging capacity)
- **Zero value**: Battery power balance is not constraining the optimization

**Example**: A value of 0.15 means that if the battery could accept 1 kW more power, the total system cost would decrease by \$0.15 at this time period.

### Energy In Flow

The marginal value of relaxing the charging constraint.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would change if the battery could charge more energy.

**Interpretation**:

- **Zero value**: Charging constraint is not limiting
- **Nonzero value**: Battery charging is constrained and relaxing the constraint would reduce costs

**Example**: A value of 0.05 means that if the battery could charge 1 kWh more, the total system cost would decrease by \$0.05 at this time period.

### Energy Out Flow

The marginal value of relaxing the discharging constraint.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would change if the battery could discharge more energy.

**Interpretation**:

- **Zero value**: Discharging constraint is not limiting
- **Nonzero value**: Battery discharging is constrained and relaxing the constraint would reduce costs

**Example**: A value of 0.08 means that if the battery could discharge 1 kWh more, the total system cost would decrease by \$0.08 at this time period.

### SOC Max

The marginal value of additional storage capacity.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the battery had 1 kWh more capacity.

**Interpretation**:

- **Zero value**: Battery is not at maximum capacity
- **Negative value**: Battery is full and more capacity would reduce costs
- **Positive value**: Battery capacity constraint is not binding

**Example**: A value of -0.12 means that if the battery had 1 kWh more capacity, the total system cost would decrease by \$0.12 at this time period.

### SOC Min

The marginal value of deeper discharge capability.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the battery could discharge 1 kWh deeper (below current minimum).

**Interpretation**:

- **Zero value**: Battery is not at minimum capacity
- **Positive value**: Battery is empty and the ability to extract more energy would reduce costs
- **Negative value**: Battery minimum capacity constraint is not binding

**Example**: A value of 0.10 means that if the battery could discharge 1 kWh deeper, the total system cost would decrease by \$0.10 at this time period.

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

### Battery Section Not Visible

**Problem**: The Battery Section element type does not appear in the element selection list.

**Solution**: Enable Advanced Mode in your hub configuration.
Battery Section is only available when Advanced Mode is enabled.

### No Power Flow

**Problem**: Battery Section shows zero power even when connected.

**Solution**: Verify that Connection elements are properly configured to connect the Battery Section to other elements (nodes, grids, etc.).
Battery Section does not create implicit connections like the standard Battery element.

### Connection Errors

**Problem**: Cannot create connections to or from the Battery Section.

**Solution**: Ensure the Battery Section name matches exactly in both the Connection source and target fields.
Check that the Battery Section element exists before creating connections.

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect Battery Section to other elements using Connection elements.

    [:material-arrow-right: Connections guide](connections.md)

- :material-battery-charging:{ .lg .middle } **Standard Battery element**

    ---

    Consider using the standard Battery element for most use cases with automatic connections.

    [:material-arrow-right: Battery guide](battery.md)

- :material-math-integral:{ .lg .middle } **Battery Section modeling**

    ---

    Understand how Battery Section maps to the model layer Battery element.

    [:material-arrow-right: Battery Section modeling](../../modeling/device-layer/battery_section.md)

- :material-cog-outline:{ .lg .middle } **Advanced mode**

    ---

    Learn about advanced mode and other advanced elements.

    [:material-arrow-right: Configuration guide](../configuration.md#advanced-mode)

</div>
