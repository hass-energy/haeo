# How data updates work

This guide explains how HAEO keeps its recommendations current.
Use it to understand where the data comes from, what prompts an optimisation, and how to give the system a gentle nudge when needed.

## How HAEO receives data

HAEO reads the entities you select when you build the energy network in Home Assistant.
Those entities supply the latest measurements, forecasts, and prices that shape the optimisation.
Whenever Home Assistant updates one of those sources, HAEO sees the new information almost immediately.

## What triggers an optimisation

HAEO runs a new optimisation when any of the following happens:

- Fresh data arrives from a tracked entity.
- The regular schedule reaches the next planned check-in.
- You request a manual refresh from the Home Assistant interface or an automation.

To avoid starting several runs in quick succession, HAEO briefly waits for related updates to settle before it recomputes.
If another change appears while a run is already in progress, HAEO queues a follow-up pass so the final result still reflects every update.

## Manual refresh options

Sometimes you want the latest recommendation right away.
You can trigger a manual refresh from the entity details page or by calling the standard Home Assistant update service for any HAEO sensor.
Manual refreshes skip the waiting period and start a new optimisation as soon as they are invoked.

## Troubleshooting stale data

If the values stop moving, check whether the upstream entities are still reporting and confirm that HAEO is loaded without issues in the Integrations screen.
A quick manual refresh is a good way to test whether the optimiser can run with the data currently available.
Persistent problems usually point to missing inputs or external services that need attention.

Monitor your system occasionally to ensure updates finish comfortably within the time windows that matter for your automations.
Long optimisation runs usually mean the problem has become quite large, so start by simplifying inputs before you tweak the look-ahead horizon.
Review the [horizon guidance](configuration.md#horizon-hours) before changing that value.

## Debugging updates

### Enable debug logging

To see detailed update information:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.haeo: debug
```

**Logged information:**

- Update trigger sources
- Data collection timing
- Optimization solve time
- Result processing steps
- Error details and stack traces

### Check coordinator status

Use developer tools to inspect coordinator state:

1. Navigate to Developer Tools → States
2. Find coordinator sensors (e.g., `sensor.haeo_optimization_status`)
3. Check attributes for:
    - Last update time
    - Update success status
    - Error messages
    - Data source states

### Monitor with automations

Create automations to alert on update issues:

```yaml
# Alert on persistent update failures
automation:
  - alias: HAEO update failure alert
    trigger:
      - platform: state
        entity_id: sensor.haeo_optimization_status
        to: error
        for:
          minutes: 15
    action:
      - service: notify.mobile_app
        data:
          title: HAEO optimization failing
          message: >
            HAEO has failed to optimize for 15 minutes.
            Check configuration and logs.
```

## Integration with automations

### Using updated data

HAEO sensors update automatically, so automations just work:

```yaml
# Automation triggers on updated recommendations
automation:
  - alias: Follow HAEO battery recommendations
    trigger:
      - platform: state
        entity_id: sensor.haeo_battery_recommended_power
    condition:
      # Only act on meaningful changes
      - condition: template
        value_template: >
          {{
            (trigger.to_state.state | float(0) - trigger.from_state.state | float(0))
          | abs > 100
          }}
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_target_power
        data:
          value: "{{ states('sensor.haeo_battery_recommended_power') }}"
```

**Best practices:**

- Add change thresholds to prevent minor fluctuations
- Include safety checks and limits
- Handle unavailable sensor states gracefully
- Log actions for debugging

### Coordination with other integrations

When using HAEO with other control systems:

**Priority:**

1. Safety systems (BMS, inverter protection) - always highest priority
2. Manual overrides - user control when needed
3. HAEO recommendations - normal automated operation
4. Fallback behavior - when HAEO unavailable

**Implementation:**

```yaml
automation:
  - alias: Battery control with safety and overrides
    trigger:
      - platform: state
        entity_id: sensor.haeo_battery_recommended_power
    condition:
      # Check safety systems
      - condition: state
        entity_id: binary_sensor.battery_error
        state: off
      # Check manual override not active
      - condition: state
        entity_id: input_boolean.manual_battery_control
        state: off
      # Check HAEO data available
      - condition: template
        value_template: >
          {{
            states('sensor.haeo_battery_recommended_power') not in ['unavailable',
          'unknown']
          }}
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_target_power
        data:
          value: "{{ states('sensor.haeo_battery_recommended_power') }}"
```

## Frequently asked questions

### Can I change the update interval?

Yes. Open the HAEO integration options and adjust **Update interval (minutes)** to suit your system.
Lower values run the optimizer more frequently, while higher values reduce background load.

Remember that very short intervals can increase solver CPU usage, especially on larger networks.

### Why do sensors sometimes show "unavailable"?

Sensors become unavailable when:

- Optimization fails to find a solution
- Required data sources are offline
- Configuration errors prevent optimization
- Integration is initializing

Check the `sensor.haeo_optimization_status` entity for details.

### How can I speed up updates?

Combine these strategies for quicker responses:

- Shorten the **Update interval** to run the optimizer more often when no sensor changes occur.
- Reduce the **Debounce window** so sensor changes trigger reruns sooner.
- Reduce optimization horizon for faster solving after consulting the [horizon guidance](configuration.md#horizon-hours).
- Use longer time periods (15 minutes vs. 5 minutes) to shrink the optimization problem.
- Simplify network topology when possible.
- Trigger manual updates via service calls when you need immediate feedback.

### Do I need to restart Home Assistant after configuration changes?

No. Configuration changes through the UI take effect immediately:

- Element settings updates trigger optimization refresh
- New connections rebuild network and re-optimize
- Sensor changes detected automatically

Only changes to integration code (development) require restart.

## Next Steps

Focus on these areas to keep data updates reliable and useful.

<div class="grid cards" markdown>

- :material-tune:{ .lg .middle } __Tune configuration settings__

    Adjust horizon, period, and solver options to balance accuracy and speed.

    [:material-arrow-right: Configuration options](configuration.md)

- :material-chart-line:{ .lg .middle } __Monitor optimization performance__

    Track solve duration and update frequency to spot bottlenecks.

    [:material-arrow-right: Performance tips](optimization.md#performance-considerations)

- :material-robot-outline:{ .lg .middle } __Automate responses to new data__

    Trigger actions when HAEO publishes fresh recommendations.

    [:material-arrow-right: Automation patterns](automations.md)

- :material-help-circle-outline:{ .lg .middle } __Resolve persistent issues__

    Work through common problems when data updates fall behind.

    [:material-arrow-right: Troubleshooting tips](troubleshooting.md)

</div>
