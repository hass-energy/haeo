# Automation examples

This guide explains how to control your battery and inverter systems using HAEO's optimization results.

## Overview

HAEO solves the optimization problem and produces **control limit recommendations** that you can apply directly to your hardware.
These sensors synthesize the optimal power flows, constraint shadow prices, and configured limits into a single value (in kW) that can be used as a hardware setpoint.

## Control Limit Recommendations

HAEO provides recommendation sensors for each controllable limit in your system.
Each sensor provides:

- **Current value**: The recommended limit right now (kW)
- **Forecast attribute**: Recommended limits for future time periods

### Available Recommendation Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| `sensor.{battery}_charge_limit_recommendation` | kW | Recommended battery charging power limit |
| `sensor.{battery}_discharge_limit_recommendation` | kW | Recommended battery discharging power limit |
| `sensor.{inverter}_charge_limit_recommendation` | kW | Recommended inverter AC→DC power limit |
| `sensor.{inverter}_discharge_limit_recommendation` | kW | Recommended inverter DC→AC power limit |
| `sensor.{grid}_import_limit_recommendation` | kW | Recommended grid import power limit |
| `sensor.{grid}_export_limit_recommendation` | kW | Recommended grid export power limit |

!!! note "Conditional availability"

    Grid recommendation sensors only appear when you have configured import/export limits.
    Battery and inverter recommendations are always available.

### How Recommendations Are Calculated

Each recommendation combines three pieces of information:

1. **Optimal power flow**: What power the optimizer wants to flow
2. **Shadow price**: Whether the configured limit is constraining the solution
3. **Configured limit**: Your hardware's maximum capacity

The synthesis logic:

| Optimal Power | Shadow Price | Recommendation |
|--------------|--------------|----------------|
| 0 | (any) | 0 kW — No flow desired, block this direction |
| > 0 | 0 | Max limit — Flow desired with headroom available |
| > 0 | > 0 | Power value — At binding constraint, use exact rate |

This means:

- **Zero recommendation**: HAEO doesn't want any power flowing in this direction right now
- **Maximum recommendation**: HAEO wants power to flow and you have headroom
- **Intermediate recommendation**: You're at the constraint limit; use the exact optimal rate

## Basic Automation Pattern

The simplest automation directly applies the recommendation to your hardware:

```yaml
automation:
  - alias: "HAEO: Apply Battery Charge Limit"
    trigger:
      - platform: state
        entity_id: sensor.main_battery_charge_limit_recommendation
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_max_charging_limit
        data:
          value: "{{ states('sensor.main_battery_charge_limit_recommendation') | float(0) }}"
```

This pattern works for any recommendation sensor paired with its corresponding hardware control.

## Complete Battery Control

Apply both charge and discharge limits:

```yaml
automation:
  - alias: "HAEO: Apply Battery Limits"
    trigger:
      - platform: state
        entity_id:
          - sensor.main_battery_charge_limit_recommendation
          - sensor.main_battery_discharge_limit_recommendation
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_max_charging_limit
        data:
          value: "{{ states('sensor.main_battery_charge_limit_recommendation') | float(0) }}"
      - service: number.set_value
        target:
          entity_id: number.battery_max_discharging_limit
        data:
          value: "{{ states('sensor.main_battery_discharge_limit_recommendation') | float(0) }}"
```

## Grid Export Control

When you have a grid export limit configured, HAEO provides an export limit recommendation:

```yaml
automation:
  - alias: "HAEO: Apply Grid Export Limit"
    trigger:
      - platform: state
        entity_id: sensor.main_grid_export_limit_recommendation
    action:
      - service: number.set_value
        target:
          entity_id: number.grid_export_limitation
        data:
          value: "{{ states('sensor.main_grid_export_limit_recommendation') | float(0) }}"
```

!!! tip "Negative export prices"

    When export prices go negative, the recommendation will be 0 kW—HAEO handles the price signal automatically.
    You don't need separate curtailment logic.

## Inverter Power Limits

For hybrid inverters, apply both direction limits:

```yaml
automation:
  - alias: "HAEO: Apply Inverter Limits"
    trigger:
      - platform: state
        entity_id:
          - sensor.main_inverter_charge_limit_recommendation
          - sensor.main_inverter_discharge_limit_recommendation
    action:
      - service: number.set_value
        target:
          entity_id: number.inverter_ac_to_dc_limit
        data:
          value: "{{ states('sensor.main_inverter_charge_limit_recommendation') | float(0) }}"
      - service: number.set_value
        target:
          entity_id: number.inverter_dc_to_ac_limit
        data:
          value: "{{ states('sensor.main_inverter_discharge_limit_recommendation') | float(0) }}"
```

## Complete System Example

A complete automation for a system with battery, inverter, and grid export control:

```yaml
automation:
  - alias: "HAEO: Complete System Control"
    description: Apply all HAEO recommendations to hardware
    trigger:
      - platform: state
        entity_id:
          - sensor.main_battery_charge_limit_recommendation
          - sensor.main_battery_discharge_limit_recommendation
          - sensor.main_inverter_charge_limit_recommendation
          - sensor.main_inverter_discharge_limit_recommendation
          - sensor.main_grid_export_limit_recommendation
    condition:
      - condition: state
        entity_id: input_boolean.haeo_auto_control
        state: "on"
    action:
      # Battery limits
      - service: number.set_value
        target:
          entity_id: number.battery_max_charging_limit
        data:
          value: "{{ states('sensor.main_battery_charge_limit_recommendation') | float(0) }}"
      - service: number.set_value
        target:
          entity_id: number.battery_max_discharging_limit
        data:
          value: "{{ states('sensor.main_battery_discharge_limit_recommendation') | float(0) }}"
      # Inverter limits
      - service: number.set_value
        target:
          entity_id: number.inverter_ac_to_dc_limit
        data:
          value: "{{ states('sensor.main_inverter_charge_limit_recommendation') | float(0) }}"
      - service: number.set_value
        target:
          entity_id: number.inverter_dc_to_ac_limit
        data:
          value: "{{ states('sensor.main_inverter_discharge_limit_recommendation') | float(0) }}"
      # Grid export limit
      - service: number.set_value
        target:
          entity_id: number.grid_export_limitation
        data:
          value: "{{ states('sensor.main_grid_export_limit_recommendation') | float(0) }}"
    mode: single
```

## Sigenergy Example

For Sigenergy systems:

```yaml
automation:
  - alias: "HAEO: Sigenergy Control"
    description: Apply HAEO recommendations to Sigenergy system
    trigger:
      - platform: state
        entity_id:
          - sensor.main_battery_charge_limit_recommendation
          - sensor.main_battery_discharge_limit_recommendation
          - sensor.main_grid_export_limit_recommendation
    action:
      - service: number.set_value
        target:
          entity_id: number.sigen_plant_ess_max_charging_limit
        data:
          value: "{{ states('sensor.main_battery_charge_limit_recommendation') | float(0) }}"
      - service: number.set_value
        target:
          entity_id: number.sigen_plant_ess_max_discharging_limit
        data:
          value: "{{ states('sensor.main_battery_discharge_limit_recommendation') | float(0) }}"
      - service: number.set_value
        target:
          entity_id: number.sigen_plant_grid_export_limitation
        data:
          value: "{{ states('sensor.main_grid_export_limit_recommendation') | float(0) }}"
    mode: single
```

## Operating Modes

Some systems require setting an operating mode in addition to power limits.
The combination of charge and discharge recommendations determines the appropriate mode:

| Charge Recommendation | Discharge Recommendation | Mode |
|----------------------|-------------------------|------|
| > 0 | 0 | Forced Charging |
| 0 | > 0 | Forced Discharging |
| > 0 | > 0 | Self-Consumption |
| 0 | 0 | Standby |

```yaml
automation:
  - alias: "HAEO: Battery Mode Selection"
    trigger:
      - platform: state
        entity_id:
          - sensor.main_battery_charge_limit_recommendation
          - sensor.main_battery_discharge_limit_recommendation
    variables:
      charge: "{{ states('sensor.main_battery_charge_limit_recommendation') | float(0) }}"
      discharge: "{{ states('sensor.main_battery_discharge_limit_recommendation') | float(0) }}"
    action:
      - choose:
          # Self-consumption: both directions allowed
          - conditions:
              - condition: template
                value_template: "{{ charge > 0 and discharge > 0 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.battery_mode
                data:
                  option: "Maximum Self Consumption"
          # Forced charging: only charge allowed
          - conditions:
              - condition: template
                value_template: "{{ charge > 0 and discharge == 0 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.battery_mode
                data:
                  option: "Command Charging (PV First)"
          # Forced discharging: only discharge allowed
          - conditions:
              - condition: template
                value_template: "{{ charge == 0 and discharge > 0 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.battery_mode
                data:
                  option: "Command Discharging (PV First)"
          # Standby: neither direction allowed
          - conditions:
              - condition: template
                value_template: "{{ charge == 0 and discharge == 0 }}"
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.battery_mode
                data:
                  option: "Standby"
```

## Optimization Status Monitoring

Monitor for optimization failures:

```yaml
automation:
  - alias: "HAEO: Optimization Status Monitor"
    trigger:
      - platform: state
        entity_id: sensor.main_network_optimization_status
        to: "error"
    action:
      - service: notify.notify
        data:
          title: "HAEO Optimization Failed"
          message: >
            HAEO optimization encountered an error at {{ now().strftime('%H:%M') }}.
            Check logs for details.
```

## Best Practices

### Safety Controls

Add a manual override switch to disable automations:

```yaml
input_boolean:
  haeo_auto_control:
    name: "HAEO Auto Control"
    icon: mdi:robot
```

Use this in your automation conditions (shown in the complete system example above).

### Debouncing

Add a `for:` duration to avoid rapid changes:

```yaml
trigger:
  - platform: state
    entity_id: sensor.main_battery_charge_limit_recommendation
    for:
      seconds: 30
```

### Validation

Check that sensors are available before applying values:

```yaml
condition:
  - condition: template
    value_template: >
      {{ states('sensor.main_battery_charge_limit_recommendation') not in ['unavailable', 'unknown'] }}
```

### Rate Limiting

Use `mode: single` to prevent overlapping automation runs.

### Logging

Track changes with logbook entries:

```yaml
action:
  - service: logbook.log
    data:
      name: "HAEO"
      message: >
        Applied charge limit: {{ states('sensor.main_battery_charge_limit_recommendation') }} kW
```

## Understanding Shadow Prices

For advanced diagnostics, HAEO also provides shadow price sensors.
Shadow prices indicate whether a constraint is limiting the optimal solution.

See [Shadow Prices](../modeling/shadow-prices.md) for detailed documentation.

### Key Shadow Price Sensors

| Sensor | Interpretation |
|--------|---------------|
| `sensor.{battery}_power_max_charge_price` | Battery charging is constrained |
| `sensor.{battery}_power_max_discharge_price` | Battery discharging is constrained |
| `sensor.{grid}_import_limit_shadow_price` | Grid import is constrained |
| `sensor.{grid}_export_limit_shadow_price` | Grid export is constrained |

A **non-zero** shadow price means the constraint is binding—the optimizer wants more capacity than configured.

### Constraint Alerting

Get notified when constraints consistently limit optimization:

```yaml
automation:
  - alias: "HAEO: Binding Constraint Alert"
    trigger:
      - platform: numeric_state
        entity_id:
          - sensor.main_battery_power_max_charge_price
          - sensor.main_battery_power_max_discharge_price
        above: 0.10
        for:
          hours: 1
    action:
      - service: notify.notify
        data:
          title: "HAEO: Constraint Binding"
          message: >
            {{ trigger.to_state.attributes.friendly_name }}
            has been limiting optimization for 1 hour.
            Shadow price: ${{ trigger.to_state.state | round(2) }}/kW
```

## Troubleshooting

### Automation Not Triggering

1. Verify entity IDs in Developer Tools → States
2. Check that sensors have numeric states
3. Ensure the automation is enabled
4. Review automation traces for errors

### Unexpected Recommendations

1. Check that input sensors (prices, forecasts) have valid values
2. Verify optimization status is "success"
3. Review shadow prices to understand constraints
4. Check the forecast attribute for future recommendations

### Hardware Not Responding

1. Test manual control via Developer Tools → Services
2. Verify remote control is enabled on the physical device
3. Check that values are within hardware limits

## Next Steps

<div class="grid cards" markdown>

-   :material-chart-line:{ .lg .middle } **Shadow Prices**

    ---

    Understand constraint shadow prices and marginal values.

    [:material-arrow-right: Shadow prices](../modeling/shadow-prices.md)

-   :material-battery-charging:{ .lg .middle } **Battery Configuration**

    ---

    Configure battery elements for optimization.

    [:material-arrow-right: Battery configuration](elements/battery.md)

-   :material-transmission-tower:{ .lg .middle } **Grid Configuration**

    ---

    Configure grid connections and limits.

    [:material-arrow-right: Grid configuration](elements/grid.md)

-   :material-help-circle:{ .lg .middle } **Understanding Results**

    ---

    Learn how to interpret optimization outputs.

    [:material-arrow-right: Understanding results](optimization.md)

</div>
