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

Create automations to alert on persistent optimization failures:

```yaml
automation:
  - alias: HAEO persistent failure alert
    trigger:
      - platform: state
        entity_id: sensor.{network_name}_optimization_status
        to: failed
        for:
          minutes: 15
    action:
      - service: notify.persistent_notification
        data:
          title: HAEO optimization failing
          message: >
            HAEO has failed to optimize for 15 minutes.
            Check configuration and logs.
```

See the [Automations guide](automations.md) for more monitoring examples.

## Using updated sensors in automations

HAEO sensors update automatically when new optimizations complete.
Automations can trigger on state changes to respond to updated recommendations.

**See the [Automations guide](automations.md) for complete examples** of:

- Applying battery charge/discharge recommendations
- Solar curtailment based on optimization
- Notifications on optimization failure
- Safety checks and override patterns

**Key considerations when building automations**:

- Check sensor availability before using values
- Add rate limiting to prevent rapid hardware changes
- Include manual override mechanisms
- Prioritize safety systems above optimization recommendations

## Frequently asked questions

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
