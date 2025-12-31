# How data updates work

This guide explains how HAEO keeps its recommendations current.
Use it to understand where the data comes from, what prompts an optimization, and how to give the system a gentle nudge when needed.

## How HAEO receives data

HAEO uses an intermediate input entity layer to receive data from external sensors.
Each configuration field that accepts sensor data creates a corresponding input entity (Number or Switch) in Home Assistant.
These input entities load values from external sensors you select, transform them as needed, and make them available with a `forecast` attribute containing time-series data.

Input entities operate in one of two modes:

- **Editable**: Constant value you configure directly (e.g., battery capacity)
- **Driven**: Value loaded from an external sensor or forecast (e.g., electricity prices)

You can find input entities in Home Assistant's entity list with the `config` entity category.
They appear with names like `number.{element}_{field}` (for example, `number.battery_capacity`).

## What triggers an optimization

HAEO runs a new optimization when either of the following happens:

- An input entity's state changes (new data arrives from a tracked sensor).
- The optimization horizon advances past a period boundary.

The system is event-driven with guaranteed updates at horizon boundaries (for example, every 1 minute for the finest tier).
When sensor data changes between boundaries, the corresponding input entity updates, which triggers a new optimization.

To avoid running multiple optimizations in quick succession, HAEO uses internal debouncing.
Related updates that arrive close together are grouped, and optimization runs after activity settles.

## Manual refresh options

Sometimes you want the latest recommendation right away.
You can trigger a manual refresh from the entity details page or by calling the standard Home Assistant update service for any HAEO sensor.
Manual refreshes skip the waiting period and start a new optimisation as soon as they are invoked.

## Troubleshooting stale data

If the values stop moving, first check your input entities:

1. Navigate to Developer Tools → States
2. Search for `number.` or `switch.` prefixed with your element names to find input entities
3. Verify each input entity shows a valid state and has a `forecast` attribute with time-series data

If input entities show valid data but sensors still seem stale:

- Confirm the upstream source sensors are still reporting
- Check that HAEO is loaded without issues in the Integrations screen
- A quick manual refresh tests whether the optimizer can run with available data

Persistent problems usually point to missing inputs or external services that need attention.

Monitor your system occasionally to ensure updates finish comfortably within the time windows that matter for your automations.
Long optimization runs usually mean the problem has become quite large, so start by simplifying inputs before you tweak the look-ahead horizon.
Review the [interval tier guidance](configuration.md#interval-tiers) before changing that value.

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

Use developer tools to inspect the system state:

1. Navigate to Developer Tools → States
2. Find input entities (Number and Switch entities for your configured elements) and check their states and `forecast` attributes
3. Find output sensors and check their states and attributes
4. Check the optimization status sensor for error messages

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

Check the system logs for optimization error messages.

### How can I speed up updates?

HAEO is event-driven, so optimizations run immediately when input data changes.
To improve responsiveness:

- Ensure your source sensors update frequently (check their polling intervals)
- Adjust interval tiers for faster solving (reduce tier counts or increase durations) after consulting the [interval tier guidance](configuration.md#interval-tiers)
- Simplify network topology when possible
- Trigger manual updates via service calls when you need immediate feedback

### How do I inspect input entity data?

Input entities are visible in Home Assistant's entity list with the `config` entity category.
Each input entity has a `forecast` attribute containing the time-series data used for optimization.

To inspect input data:

1. Navigate to Developer Tools → States
2. Search for your element names (e.g., `number.battery_` or `switch.solar_`)
3. Expand the `forecast` attribute to see the time-series data

See the [Input Entities guide](../developer-guide/inputs.md) for more details on how input entities work.

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
