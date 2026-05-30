# Local Home Assistant simulation

Use `uv run sim` to spin up a real, browsable Home Assistant instance for interactive development and testing.
The simulator loads scenario input data from `tests/scenarios/`, time-shifts forecasts and prices to track the current (or accelerated) clock, optionally configures HAEO from the scenario config, and tears down when you press Ctrl+C.

This replaces the previous `config/packages/` command_line sensor workflow.

## Quick start

```bash
uv run sim scenario1
```

By default it uses the repo `config/` directory on port 8123, applies the scenario timezone, skips onboarding, and opens your browser to an auto-login page (same mechanism as guide tests, via frontend `localStorage` tokens).
From there you can inspect entities, HAEO sensors, and the frontend while the simulator pushes updated input states on an interval.

Use the `127.0.0.1` auto-login URL printed in the terminal — opening `localhost` directly will not match the stored auth client ID.
If auto-login does not take, `testuser` / `testpass` works as a fallback.

## Scenario data

Each scenario directory under `tests/scenarios/` provides:

- `inputs.json` — Home Assistant entity states (including forecast attributes)
- `environment.json` — anchor time (`optimization_start_time`) and timezone
- `config.json` — HAEO hub and element configuration (used when HAEO setup is enabled)

The simulator shifts all ISO 8601 timestamps in the input attributes so the scenario's captured "now" aligns with the simulated clock.
HAEO re-optimizes when input states change, the same way it would with live forecast sensors.

## Options

```bash
# Faster updates (every 30 seconds)
uv run sim scenario1 --interval 30

# Accelerated time: 60× real time (experimental)
uv run sim scenario1 --speed 60 --interval 5

# Load inputs only; configure HAEO manually in the UI
uv run sim scenario1 --no-config

# Ephemeral config directory and random port (for CI or isolated runs)
uv run sim scenario1 --ephemeral

# Custom config directory or port
uv run sim scenario1 --config-dir config --port 8123
```

| Flag           | Default     | Description                                                             |
| -------------- | ----------- | ----------------------------------------------------------------------- |
| `scenario`     | `scenario1` | Scenario name under `tests/scenarios/` or path to a scenario directory  |
| `--interval`   | `60`        | Seconds between input state updates                                     |
| `--speed`      | `1.0`       | Time multiplier; `1.0` uses wall clock, `>1` accelerates simulated time |
| `--no-config`  | off         | Skip automatic HAEO setup from `config.json`                            |
| `--config-dir` | `config/`   | Home Assistant config directory                                         |
| `--port`       | `8123`      | HTTP port                                                               |
| `--no-open`    | off         | Do not open the browser to the auto-login page on startup               |
| `--ephemeral`  | off         | Use a temporary config directory and ephemeral port                     |

## How it works

1. **`tools/live_hass.py`** boots an in-process Home Assistant with HTTP, frontend, auth, and recorder (default: `config/` on port 8123).
2. **`tools/time_shift.py`** applies a uniform timestamp delta to scenario input attributes.
3. **`tools/sim.py`** runs a loop that recomputes the delta each tick, pushes shifted states via `hass.states.async_set()`, and optionally calls `setup_haeo_entry()` from the scenario config.

Accelerated mode (`--speed > 1`) uses freezegun to advance Home Assistant's clock alongside the shifted data.
This mode is experimental; recorder timing and debouncers may behave differently than in production.

## Related workflows

- **Scenario regression tests**: `uv run pytest tests/scenarios/ -m scenario` — snapshot comparison at a single frozen instant
- **Offline diagnostics**: `uv run diag --file tests/scenarios/scenario1/` — model-only optimization without Home Assistant
- **Guide screenshots**: `uv run pytest -m guide` — Playwright walkthroughs using the same live HA runner

For scenario authoring, see `tests/scenarios/README.md`.

## Plain Home Assistant

`uv run sim` is the recommended replacement for `uv run hass -c config` when developing with HAEO.
It uses the same `config/` directory and port 8123 by default, but also loads time-shifted scenario inputs and can configure HAEO automatically.

To run Home Assistant without scenario inputs:

```bash
uv run hass -c config
```
