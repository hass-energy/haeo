# Historic diagnostics snapshot

This guide demonstrates generating a diagnostics snapshot from a past point in time using the Developer Tools actions UI.
A historic snapshot captures the optimizer's input state at a specific moment,
which is useful for reproducing issues or sharing system context with a developer.

## What is a historic diagnostics snapshot?

HAEO can reconstruct what the optimizer saw at any point in the past by querying the Home Assistant recorder.
The snapshot includes your configuration, all input entity states at the target time, and the optimization results —
everything needed to reproduce an optimization run offline.

This is different from the standard "Download diagnostics" option in Settings,
which only captures the *current* state.
Historic snapshots let you go back to the exact moment something unexpected happened.

## Prerequisites

This guide builds on the [Sigenergy System walkthrough](sigenergy-system.md).
Complete that walkthrough first — the steps here assume your system is already configured.

```guide-setup
run_guide("sigenergy-system")
```

## Generating the snapshot

### Step 1: Open Developer Tools

Open the Developer Tools from the Home Assistant sidebar and select the **Actions** tab.

```guide
page.navigate_to_developer_tools_actions()
```

### Step 2: Select the save diagnostics action

Search for and select the `haeo.save_diagnostics` action.
This is the service that generates diagnostics snapshots with optional time-travel support.

```guide
page.fill_service_action("haeo.save_diagnostics", "Save diagnostics")
```

### Step 3: Select the integration

Choose your HAEO integration from the **Integration** dropdown.

```guide
page.select_config_entry("Sigenergy System")
```

### Step 4: Set the target time and perform the action

Enable the **Time** checkbox and enter the date and time you want to capture.
Then click **Perform action** to generate the snapshot.
Home Assistant will query the recorder for entity states at your target time and write the diagnostics file.

```guide
from datetime import datetime, timedelta
recent = (datetime.now() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
page.fill_datetime_field("Time", recent)
hass.wait_for_recorder()
page.click_perform_action()
```

!!! tip "Choosing a target time"

    Pick a time when you noticed unexpected behavior.
    The snapshot will show exactly what the optimizer saw — prices, forecasts, battery state — at that moment.
    Make sure the time is within your recorder's retention period (default is 10 days).

## Where to find the output

The diagnostics file is saved to:

```
config/haeo/diagnostics/diagnostics_<timestamp>.json
```

The filename uses the target time you specified (not the current time),
making it easy to identify which snapshot corresponds to which event.

!!! info "File location"

    The `config/` directory is your Home Assistant configuration directory.
    For Home Assistant OS, access it via the File editor add-on, SSH, or Samba share.
    For Home Assistant Container, it is the volume you mounted as `/config`.

## Sharing with a developer

When reporting an issue, attach the diagnostics JSON file.
It contains everything needed to reproduce your optimization offline:

- **Configuration**: Your element setup (battery, solar, grid, load, policies)
- **Input states**: All entity values at the target time (prices, forecasts, state of charge)
- **Environment**: System versions, timezone, and timing information

!!! warning "Privacy"

    The diagnostics file contains your energy configuration and entity states.
    Review it before sharing publicly.
    Entity IDs and sensor values are included but no authentication credentials.

## Next steps

<div class="grid cards" markdown>

- :material-bug:{ .lg .middle } **Report an issue**

    ---

    Attach the diagnostics file when opening a GitHub issue for fastest resolution.

    [:material-arrow-right: GitHub Issues](https://github.com/hass-energy/haeo/issues)

- :material-file-download:{ .lg .middle } **Download current diagnostics**

    ---

    You can also download current-state diagnostics from Settings > Integrations > HAEO > three-dot menu > Download diagnostics.

</div>
