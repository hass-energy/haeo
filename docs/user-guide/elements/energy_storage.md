# Energy Storage

Energy Storage is an advanced element that provides direct access to the model layer Energy Storage element.
Unlike the standard Battery element which creates multiple partitions and an internal node,
this element creates a single energy storage partition that must be connected manually via Connection elements.

!!! warning "Advanced Element"

    Energy Storage is only available when **Advanced Mode** is enabled on your hub.
    This element is intended for advanced users who need direct control over storage modeling.
    Most users should use the standard [Battery](battery.md) element instead.

!!! note "Connection endpoints"

    Energy Storage elements always appear in connection selectors regardless of Advanced Mode setting.

For mathematical details, see [Energy Storage Modeling](../../modeling/device-layer/energy_storage.md).

## Configuration

### Overview

An Energy Storage element represents:

- **Single storage partition** with capacity and initial charge
- **No implicit connections** - must be connected explicitly via Connection elements
- **Direct model access** - maps directly to the model layer Energy Storage element without additional composition

Unlike the standard Battery element, Energy Storage does not create:

- Multiple SOC partitions (undercharge, normal, overcharge)
- Internal node for power routing
- Implicit connections to other elements

You must manually create Connection elements to connect the Energy Storage to your network.

## Configuration Fields

| Field                                 | Type                                  | Required | Default | Description                                  |
| ------------------------------------- | ------------------------------------- | -------- | ------- | -------------------------------------------- |
| **[Name](#name)**                     | String                                | Yes      | -       | Unique identifier (e.g., "Energy Storage 1") |
| **[Capacity](#capacity)**             | [sensor](../forecasts-and-sensors.md) | Yes      | -       | Storage capacity in kWh (can vary over time) |
| **[Initial Charge](#initial-charge)** | [sensor](../forecasts-and-sensors.md) | Yes      | -       | Initial energy stored (kWh)                  |

### Name

Choose a descriptive, friendly name.
Home Assistant uses it for sensor names, so avoid symbols or abbreviations you would not want to see in the UI.

### Capacity

Select a Home Assistant sensor that reports the storage capacity in kWh.
The sensor can provide a constant value or a forecast with time-varying capacity.

The optimizer uses this value to enforce state of charge constraints.

### Initial Charge

Select a Home Assistant sensor that reports the initial energy stored in kWh.
This represents the storage's state of charge at the start of the optimization window.

The sensor should provide a single current value (not a forecast).

## Configuration Example

Basic energy storage configuration:

| Field              | Value                   |
| ------------------ | ----------------------- |
| **Name**           | Energy Storage 1        |
| **Capacity**       | sensor.storage_capacity |
| **Initial Charge** | sensor.storage_energy   |

After creating the Energy Storage element, you must create Connection elements to connect it to other elements in your network (nodes, grids, etc.).

## Sensors Created

An Energy Storage element creates 1 device in Home Assistant with the following sensors.

| Sensor                                                             | Unit   | Description                                 |
| ------------------------------------------------------------------ | ------ | ------------------------------------------- |
| [`sensor.{name}_energy_storage_power_charge`](#power-charge)       | kW     | Power being charged into the storage        |
| [`sensor.{name}_energy_storage_power_discharge`](#power-discharge) | kW     | Power being discharged from the storage     |
| [`sensor.{name}_energy_storage_power_active`](#power-active)       | kW     | Net active power (discharge - charge)       |
| [`sensor.{name}_energy_storage_energy_stored`](#energy-stored)     | kWh    | Current energy stored                       |
| [`sensor.{name}_energy_storage_power_balance`](#power-balance)     | \$/kW  | Shadow price of power at storage terminals  |
| [`sensor.{name}_energy_storage_energy_in_flow`](#energy-in-flow)   | \$/kWh | Shadow price of charging constraint         |
| [`sensor.{name}_energy_storage_energy_out_flow`](#energy-out-flow) | \$/kWh | Shadow price of discharging constraint      |
| [`sensor.{name}_energy_storage_soc_max`](#soc-max)                 | \$/kWh | Shadow price of maximum capacity constraint |
| [`sensor.{name}_energy_storage_soc_min`](#soc-min)                 | \$/kWh | Shadow price of minimum capacity constraint |

### Power Charge

The optimal power being charged into the storage at each time period.
Values are always positive or zero.

**Example**: A value of 3.5 kW means the storage is charging at 3.5 kW at this time period.

### Power Discharge

The optimal power being discharged from the storage at each time period.
Values are always positive or zero.

**Example**: A value of 2.0 kW means the storage is discharging at 2.0 kW at this time period.

### Power Active

The net active power (discharge - charge) at each time period.
Positive values indicate net discharge, negative values indicate net charge.

**Example**: A value of -1.5 kW means the storage is charging at 1.5 kW net (discharge is less than charge).

### Energy Stored

The current energy stored at each time boundary.
Values range from 0 to the configured capacity.

**Example**: A value of 7.5 kWh means the storage currently holds 7.5 kWh of energy.

### Power Balance

The marginal value of power at the storage terminals.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would change if you could inject or extract 1 kW of power at the storage terminals.

**Interpretation**:

- **Positive value**: Power at the storage is valuable (system would benefit from more charging capacity)
- **Negative value**: Power at the storage is costly (system would benefit from more discharging capacity)
- **Zero value**: Storage power balance is not constraining the optimization

**Example**: A value of 0.15 means that if the storage could accept 1 kW more power, the total system cost would decrease by \$0.15 at this time period.

### Energy In Flow

The marginal value of relaxing the charging constraint.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would change if the storage could charge more energy.

**Interpretation**:

- **Zero value**: Charging constraint is not limiting
- **Nonzero value**: Storage charging is constrained and relaxing the constraint would reduce costs

**Example**: A value of 0.05 means that if the storage could charge 1 kWh more, the total system cost would decrease by \$0.05 at this time period.

### Energy Out Flow

The marginal value of relaxing the discharging constraint.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would change if the storage could discharge more energy.

**Interpretation**:

- **Zero value**: Discharging constraint is not limiting
- **Nonzero value**: Storage discharging is constrained and relaxing the constraint would reduce costs

**Example**: A value of 0.08 means that if the storage could discharge 1 kWh more, the total system cost would decrease by \$0.08 at this time period.

### SOC Max

The marginal value of additional storage capacity.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the storage had 1 kWh more capacity.

**Interpretation**:

- **Zero value**: Storage is not at maximum capacity
- **Negative value**: Storage is full and more capacity would reduce costs
- **Positive value**: Storage capacity constraint is not binding

**Example**: A value of -0.12 means that if the storage had 1 kWh more capacity, the total system cost would decrease by \$0.12 at this time period.

### SOC Min

The marginal value of deeper discharge capability.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the storage could discharge 1 kWh deeper (below current minimum).

**Interpretation**:

- **Zero value**: Storage is not at minimum capacity
- **Positive value**: Storage is empty and the ability to extract more energy would reduce costs
- **Negative value**: Storage minimum capacity constraint is not binding

**Example**: A value of 0.10 means that if the storage could discharge 1 kWh deeper, the total system cost would decrease by \$0.10 at this time period.

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

### Energy Storage Not Visible

**Problem**: The Energy Storage element type does not appear in the element selection list.

**Solution**: Enable Advanced Mode in your hub configuration.
Energy Storage is only available when Advanced Mode is enabled.

### No Power Flow

**Problem**: Energy Storage shows zero power even when connected.

**Solution**: Verify that Connection elements are properly configured to connect the Energy Storage to other elements (nodes, grids, etc.).
Energy Storage does not create implicit connections like the standard Battery element.

### Connection Errors

**Problem**: Cannot create connections to or from the Energy Storage.

**Solution**: Ensure the Energy Storage name matches exactly in both the Connection source and target fields.
Check that the Energy Storage element exists before creating connections.

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect Energy Storage to other elements using Connection elements.

    [:material-arrow-right: Connections guide](connections.md)

- :material-battery-charging:{ .lg .middle } **Standard Battery element**

    ---

    Consider using the standard Battery element for most use cases with automatic connections.

    [:material-arrow-right: Battery guide](battery.md)

- :material-math-integral:{ .lg .middle } **Energy Storage modeling**

    ---

    Understand how Energy Storage maps to the model layer Energy Storage element.

    [:material-arrow-right: Energy Storage modeling](../../modeling/device-layer/energy_storage.md)

- :material-cog-outline:{ .lg .middle } **Advanced mode**

    ---

    Learn about advanced mode and other advanced elements.

    [:material-arrow-right: Configuration guide](../configuration.md#advanced-mode)

</div>
