# Automation examples

This guide provides practical automation examples for the HAEO integration.
These automations help you respond to optimization events, manage energy systems, and create custom workflows based on optimization results.

## Overview

HAEO provides real-time optimization of your energy network.
You can create automations that:

- Respond to optimization completion or failure
- Apply HAEO's power recommendations to real hardware
- Curtail solar or flexible loads when optimization suggests
- Notify you when optimization outputs change significantly
- Stage safe hand-offs between optimization and manual control

## Example 1: Notification on optimization failure

This automation sends a notification when the optimization fails, helping you quickly identify and resolve issues.

```yaml
automation:
  - alias: 'HAEO: Notify on optimization failure'
    description: Send notification when energy optimization fails
    trigger:
      - platform: state
        entity_id: sensor.{network_name}_optimization_status
        to: failed
    action:
      - service: notify.persistent_notification
        data:
          title: Energy optimization failed
          message: >
            The HAEO energy optimization has failed.
            Please check the system logs for details.
```

### What this automation does

1. **Trigger**: Monitors the optimization status sensor
2. **Condition**: Activates when status changes to "failed"
3. **Action**: Creates a persistent notification in Home Assistant

### Customization options

- Add conditions to only notify during certain hours
- Add mobile app notifications using your configured notify service
- Create a counter to track failure frequency over time

## Example 2: Apply battery power recommendation

This automation writes HAEO's recommended battery power directly to a controllable setpoint entity when the optimization completes successfully.

```yaml
automation:
  - alias: 'HAEO: Apply battery charge power'
    description: Set battery charge power from HAEO recommendation
    trigger:
      - platform: state
        entity_id: sensor.{battery_name}_power_charge
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state not in ['unavailable', 'unknown'] }}
      - condition: template
        value_template: >
          {{ trigger.to_state.state | float(0) > 0 }}
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_charge_power_setpoint
        data:
          value: '{{ trigger.to_state.state | float(0) }}'

  - alias: 'HAEO: Apply battery discharge power'
    description: Set battery discharge power from HAEO recommendation
    trigger:
      - platform: state
        entity_id: sensor.{battery_name}_power_discharge
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state not in ['unavailable', 'unknown'] }}
      - condition: template
        value_template: >
          {{ trigger.to_state.state | float(0) > 0 }}
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_discharge_power_setpoint
        data:
          value: '{{ trigger.to_state.state | float(0) }}'
```

### What this automation does

1. **Triggers**: Separate automations for charge (`power_charge`) and discharge (`power_discharge`) sensors
2. **Safety checks**: Ensures sensor is available and value is positive (non-zero operation)
3. **Actions**: Writes the appropriate setpoint to battery control entities

### Customization options

- Replace `number.battery_charge_power_setpoint` and `number.battery_discharge_power_setpoint` with your battery's control entities
- Use [`numeric_state` triggers](https://www.home-assistant.io/docs/automation/trigger/#numeric-state-trigger) to only react to significant changes
- Add rate limiting with `for:` duration to debounce rapid updates
- Include logbook.log service for audit trail of applied changes

## Example 3: Curtail solar generation based on forecast

This automation caps inverter output when HAEO predicts excess solar that would force grid export at high prices.

```yaml
automation:
  - alias: 'HAEO: Solar curtailment'
    description: Limit inverter output when HAEO recommends curtailment
    trigger:
      - platform: state
        entity_id: sensor.{solar_name}_power
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state not in ['unavailable', 'unknown'] }}
    action:
      - service: number.set_value
        target:
          entity_id: number.solar_inverter_limit_kw
        data:
          value: '{{ trigger.to_state.state | float(0) }}'
```

### What this automation does

1. **Trigger**: Monitors `power` (optimized solar generation)
2. **Conditions**: Validates sensor availability
3. **Action**: Sets inverter power limit to match HAEO's optimized output

### Customization options

- Replace `number.solar_inverter_limit_kw` with your inverter's power limit control entity
- Add [`for:` duration on the trigger](https://www.home-assistant.io/docs/automation/trigger/#state-trigger) to debounce brief fluctuations
- Compare against your forecast sensor if you want to apply curtailment only when optimized output is below forecast
- Use `choose` action with multiple conditions for different curtailment levels (e.g., block export vs reduce power)

## Best practices

### Safely apply optimization recommendations

- Check sensor availability using `not in ['unavailable', 'unknown']` template conditions
- Compare recommendations against hardware limits and sensor feedback to detect drift
- Use [`choose`](https://www.home-assistant.io/docs/scripts/conditions/#choose-a-group-of-actions) blocks for fallback behaviors when values exceed safety thresholds
- Keep a manual override helper (e.g., `input_boolean.haeo_manual_override`) to skip automations when you need direct control

### Handle frequent optimization result changes

- Add `for:` options to state triggers or use templates that ignore small deltas to avoid thrashing hardware.
- Persist the last applied value in an [`input_number`](https://www.home-assistant.io/integrations/input_number/) and only write a new setpoint when the change is meaningful.
- Rate-limit notifications with [automation trace](https://www.home-assistant.io/docs/automation/trace/) insights to make sure informative alerts are not muted by constant updates.
- Group related actions with the [`script.turn_on`](https://www.home-assistant.io/integrations/script/) service so multiple automations share the same debounce logic.

### Protect real hardware

- Enforce min and max limits using dedicated `number` entities exposed by your inverter or charger.
- Add a final verification step that confirms the actuator accepted the change (for example, compare `sensor.{battery_name}_power_charge` after a short delay).
- Log every applied recommendation to the Logbook so you can audit changes if the device misbehaves.
- During commissioning, keep automations in "monitor only" mode by replacing actuator calls with notifications until you are confident in the behavior.

## Troubleshooting

### Automation not triggering

**Check these common issues:**

1. **Entity ID typo**: Verify exact sensor entity IDs in Developer Tools → States
2. **State format**: Some sensors use strings ("success"), others use numbers (50.5)
3. **Trigger conditions**: Ensure the trigger actually changes to the specified value
4. **Automation disabled**: Check that the automation toggle is on

### Getting the current state value

Use Developer Tools → States to inspect sensor values:

```
sensor.{network_name}_optimization_status: "success"
sensor.{battery_name}_power_charge: 3.2
sensor.{battery_name}_power_discharge: 0.0
sensor.{solar_name}_power: 4.5
```

### Debugging with traces

Enable automation traces to see execution history:

1. Go to Settings → Automations & Scenes
2. Click on your automation
3. Click the three dots → "Traces"
4. Review the execution path and variable values

## Additional resources

- [Home Assistant Automation Documentation](https://www.home-assistant.io/docs/automation/)
- [Template Documentation](https://www.home-assistant.io/docs/configuration/templating/)
- [Understanding Results](optimization.md)

## Need help?

If you have questions or need help creating automations:

- Check the [HAEO GitHub Discussions](https://github.com/hass-energy/haeo/discussions)
- Review existing automation examples from the community
- Ask in the Home Assistant Community forums with the `haeo` tag

## Next Steps

<div class="grid cards" markdown>

- :material-graph:{ .lg .middle } **Optimization results**

    ---

    Learn how to interpret the outputs you automate.

    [:material-arrow-right: Optimization guide](optimization.md)

- :material-chart-line:{ .lg .middle } **Forecasts and sensors**

    ---

    Ensure your data sources cover the planning horizon.

    [:material-arrow-right: Forecasts guide](forecasts-and-sensors.md)

- :material-battery-charging:{ .lg .middle } **Battery configuration**

    ---

    Review battery sensors and outputs used in automations.

    [:material-arrow-right: Battery guide](elements/battery.md)

- :material-weather-sunny:{ .lg .middle } **Solar configuration**

    ---

    Validate solar outputs and curtailment behavior.

    [:material-arrow-right: Solar guide](elements/solar.md)

</div>
