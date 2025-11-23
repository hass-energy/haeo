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
        entity_id: sensor.haeo_network_optimization_status
        to: failed
    action:
      - service: notify.persistent_notification
        data:
          title: Energy optimization failed
          message: >
            The HAEO energy optimization has failed.
            Please check the system logs for details.
      - service: notify.mobile_app_phone
        data:
          title: HAEO Alert
          message: Energy optimization failed - check Home Assistant
          data:
            priority: high
            ttl: 0
```

### What this automation does

1. **Trigger**: Monitors the optimization status sensor
2. **Condition**: Activates when status changes to "failed"
3. **Actions**:
    - Creates a persistent notification in Home Assistant
    - Sends a mobile notification with high priority
    - Uses TTL=0 to ensure delivery even if phone is offline

### Customization options

- Add conditions to only notify during certain hours
- Include the failure reason in the message if available
- Send to multiple notification services
- Create a counter to track failure frequency

## Example 2: Apply battery power recommendation

This automation writes HAEO's recommended battery power directly to a controllable setpoint entity when the optimization completes successfully.

```yaml
automation:
  - alias: 'HAEO: Apply battery power recommendation'
    description: Set battery power limit to the optimization recommendation
    trigger:
      - platform: state
        entity_id: sensor.haeo_battery_recommended_power
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state not in ['unavailable', 'unknown'] }}
      - condition: state
        entity_id: sensor.haeo_network_optimization_status
        state: success
      - condition: template
        value_template: >
          {{
            (trigger.to_state.state | float(0))
             | abs <= states('number.battery_max_safe_power')
             | float(5)
          }}
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_power_setpoint
        data:
          value: '{{ trigger.to_state.state | float(0) }}'
      - service: logbook.log
        data:
          name: HAEO battery dispatch
          message: >-
            Applied
            {{ trigger.to_state.state | float(0) | round(2) }}
            kW limit to
            {{ state_attr('number.battery_power_setpoint', 'friendly_name') }}.
      - service: notify.mobile_app_phone
        data:
          title: Battery output updated
          message: >-
            Battery now set to
            {{ trigger.to_state.state | float(0) | round(2) }}
            kW based on HAEO recommendation.
```

### What this automation does

1. **Trigger**: Runs whenever `sensor.haeo_battery_recommended_power` changes.
2. **Safety checks**: Ensures the optimization succeeded, the recommendation is valid, and the value stays within a user-defined `number.battery_max_safe_power` control.
3. **Actions**: Writes the new setpoint, records a log entry, and sends a confirmation notification.

### Customization options

- Replace `number.battery_power_setpoint` with the entity that controls your battery inverter or dispatch service.
- Use [`numeric_state` triggers](https://www.home-assistant.io/docs/automation/trigger/#numeric-state-trigger) if you only want to react to significant changes.
- Swap the notification for an input boolean or scene activation if you prefer silent updates.

## Example 3: Curtail solar generation based on forecast

This automation caps inverter output when HAEO predicts excess solar that would force grid export at high prices.

```yaml
automation:
  - alias: 'HAEO: Solar curtailment when forecast is high'
    description: Limit inverter output according to HAEO recommendation
    trigger:
      - platform: state
        entity_id: sensor.haeo_solar_recommended_power
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state not in ['unavailable', 'unknown'] }}
      - condition: state
        entity_id: sensor.haeo_network_optimization_status
        state: success
      - condition: template
        value_template: >
          {{
            trigger.to_state.state
            | float(0) < states('sensor.haeo_solar_power')
            | float(0)
          }}
    action:
      - choose:
          - conditions:
              - condition: template
                value_template: >
                  {{ trigger.to_state.state | float(0) <= 0.5 }}
            sequence:
              - service: switch.turn_on
                target:
                  entity_id: switch.solar_inverter_export_block
              - service: notify.mobile_app_phone
                data:
                  title: Solar curtailed
                  message: Inverter export fully blocked due to negative pricing
                    forecast.
        default:
          - service: select.select_option
            target:
              entity_id: select.solar_inverter_mode
            data:
              option: limited
          - service: number.set_value
            target:
              entity_id: number.solar_inverter_limit_kw
            data:
              value: >-
                {{
                  [
                    trigger.to_state.state | float(0),
                    states('number.solar_inverter_limit_max') | float(15)
                  ] | min
                }}
          - service: notify.mobile_app_phone
            data:
              title: Solar limit updated
              message: >-
                Inverter capped at
                {{ trigger.to_state.state | float(0) | round(2) }} kW
                to follow HAEO recommendation.
```

### What this automation does

1. **Trigger**: Monitors `sensor.haeo_solar_recommended_power` for new curtailment values.
2. **Conditions**: Validates the recommendation and checks actual solar output.
3. **Actions**: Either blocks export entirely when the recommendation is near zero, or sets a numeric cap via inverter entities and notifies you.

### Customization options

- Replace the inverter entities with services from your specific hardware vendor.
- Add [`for:` options on the trigger](https://www.home-assistant.io/docs/automation/trigger/#state-trigger) to debounce brief fluctuations.
- Combine with grid price sensors to only curtail when export prices go negative.

## Best practices

### Safely apply optimization recommendations

- Always confirm `sensor.haeo_network_optimization_status` shows `success` before writing recommendations to hardware.
- Compare the recommendation against live feedback sensors such as `sensor.haeo_battery_power` to detect drift or actuator limits.
- Use [`choose`](https://www.home-assistant.io/docs/scripts/conditions/#choose-a-group-of-actions) blocks to define fallback behaviors when recommendations exceed your safety thresholds.
- Keep a manual override helper (for example, `input_boolean.haeo_manual_override`) and add it as a condition to skip automations when you need manual control.

### Handle frequent optimization result changes

- Add `for:` options to state triggers or use templates that ignore small deltas to avoid thrashing hardware.
- Persist the last applied value in an [`input_number`](https://www.home-assistant.io/integrations/input_number/) and only write a new setpoint when the change is meaningful.
- Rate-limit notifications with [automation trace](https://www.home-assistant.io/docs/automation/trace/) insights to make sure informative alerts are not muted by constant updates.
- Group related actions with the [`script.turn_on`](https://www.home-assistant.io/integrations/script/) service so multiple automations share the same debounce logic.

### Protect real hardware

- Enforce min and max limits using dedicated `number` entities exposed by your inverter or charger.
- Add a final verification step that confirms the actuator accepted the change (for example, compare `sensor.haeo_battery_power` after a short delay).
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
sensor.haeo_network_optimization_status: "success"
sensor.haeo_battery_recommended_power: 3.2
sensor.haeo_battery_power: 3.0
sensor.haeo_solar_recommended_power: 4.5
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
- [HAEO Sensor Reference](../reference/sensors.md)
- [Optimization Status Values](../reference/sensors.md#sensor-states)

## Need help?

If you have questions or need help creating automations:

- Check the [HAEO GitHub Discussions](https://github.com/hass-energy/haeo/discussions)
- Review existing automation examples from the community
- Ask in the Home Assistant Community forums with the `haeo` tag
