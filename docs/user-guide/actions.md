# Actions

HAEO adds two actions to Home Assistant.
`haeo.optimize` runs a new plan straight away,
and `haeo.save_diagnostics` saves a diagnostics file for the current moment or a time in the past.

You can run either action from **Developer Tools** → **Actions**,
or call it from an automation or script.

## Run an optimization

`haeo.optimize` runs a new optimization for one HAEO system.
It starts immediately instead of waiting for related updates to settle,
and it runs even when the **Auto optimize** switch on your system's network device is off.

| Field  | Required | Description                         |
| ------ | -------- | ----------------------------------- |
| System | Yes      | The HAEO system to run the plan for |

Use it when:

- **Auto optimize** is off and you want to choose when HAEO plans, such as after an automation changes several inputs at once
- You changed something and want to see the new plan without waiting
- You want to check that HAEO can produce a plan from the data it has now

```yaml
action: haeo.optimize
data:
  config_entry: <your HAEO system>
```

In the automation editor, pick the system from the **System** list rather than typing its ID.

The action returns once the optimization finishes.
Its result shows up the same way as any other plan:
the output sensors update when it succeeds,
and the optimization status sensor and a repair issue explain a failure.
See [Understanding results](optimization.md) and [Troubleshooting](troubleshooting.md).

When the planning horizon has just moved on and HAEO is still loading forecasts for the new periods, the action does nothing.
HAEO plans by itself once those forecasts have loaded, so there is no need to run it again.

## Save diagnostics

`haeo.save_diagnostics` writes a diagnostics file for one HAEO system.
The file holds your HAEO configuration, the input values the optimizer used, and the resulting plan,
in the same format as **Download diagnostics** on the integration page.

| Field  | Required | Description                                                                         |
| ------ | -------- | ----------------------------------------------------------------------------------- |
| System | Yes      | The HAEO system to save diagnostics for                                             |
| Time   | No       | A past date and time to rebuild the inputs from. Leave it out for the current state |

Use it when:

- You want to report a plan that looked wrong some time ago.
    Set **Time** to that moment and HAEO rebuilds what the optimizer saw from Home Assistant's history.
- You want a file of the current state to attach when you ask for help

The file is saved in the `haeo/diagnostics/` folder of your Home Assistant configuration directory.
Its name includes the time it describes.

A **Time** without a time zone is read in Home Assistant's own time zone.
The **Time** field appears only when Home Assistant's recorder is running, because the recorder is where past values come from.
The [historic diagnostics walkthrough](../walkthroughs/historic-diagnostics.md) shows the steps in the Home Assistant interface.

```yaml
action: haeo.save_diagnostics
data:
  config_entry: <your HAEO system>
  time: "2025-01-01 18:30:00"
```

!!! warning "Privacy"

    The diagnostics file contains your energy configuration and the values of the sensors HAEO reads.
    Review it before you share it publicly.

## Errors

Both actions stop with an error message when they cannot run:

| Message                          | What it means                                                                                      | What to do                                                          |
| -------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Config entry … not found         | The chosen system no longer exists                                                                 | Pick the system again; it may have been removed and added again     |
| Config entry … is not a HAEO hub | The chosen entry belongs to another integration                                                    | Pick a HAEO system                                                  |
| Config entry … is not loaded     | The HAEO system is still starting, failed to start, or is disabled                                 | Check the system on the integration page and fix any reported issue |
| No history available at time …   | Only from `haeo.save_diagnostics`: the recorder has no values at that time for the inputs it names | Choose a later time, within how long your recorder keeps history    |

## Next steps

<div class="grid cards" markdown>

- :material-robot-outline:{ .lg .middle } __Automate with HAEO__

    ---

    Use HAEO's plan to control your devices.

    [:material-arrow-right: Automation examples](automations.md)

- :material-refresh:{ .lg .middle } __Understand when HAEO plans__

    ---

    See what starts a new optimization by itself.

    [:material-arrow-right: Data updates](data-updates.md)

- :material-help-circle-outline:{ .lg .middle } __Fix problems__

    ---

    Work through common issues, and attach a diagnostics file when you ask for help.

    [:material-arrow-right: Troubleshooting](troubleshooting.md)

</div>
