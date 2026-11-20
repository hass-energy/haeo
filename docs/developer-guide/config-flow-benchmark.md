# Config flow usability benchmark

The usability benchmark measures how easily a first-time user completes real setup tasks in HAEO's element config flows.
Use it to compare a config flow change against the current flows before and after the change.

Each task starts a live Home Assistant with real scenario inputs and a configured hub.
A sandboxed Claude session then plays a user who knows their own home but has never used HAEO.
It works from a plain-English goal and sees the browser only through an accessibility tree.
The task passes when the subentries it leaves behind match what the goal asks for.

## Running it

```bash
# Every task three times, eight runs at a time
uv run python -m tools.ux_bench.run --holdout --repeats 3 --parallel 8

# One task once
uv run python -m tools.ux_bench.run --task add_battery --repeats 1

# Score saved runs again after changing a task's expectation or the scoring
uv run python -m tools.ux_bench.run --rescore --out .ux-bench/<run>
```

Results go to `.ux-bench/<timestamp>/` unless `--out` says otherwise.
`summary.md` holds the pass rate and median effort per task.
`report.md` holds each run's problems and the agent's own list of the points where it hesitated or made a mistake.
That list is the most useful output: it names the labels, defaults, and missing explanations that slow users down.

The agent needs the `claude` command logged in.
If Playwright's pinned Chromium is not installed, set `UX_BENCH_CHROMIUM` to the path of a Chromium executable.

| Flag         | Default    | Description                                       |
| ------------ | ---------- | ------------------------------------------------- |
| `--task`     | every task | Task id to run; repeat the flag for several tasks |
| `--holdout`  | off        | Include the holdout tasks                         |
| `--repeats`  | `3`        | Runs per task                                     |
| `--parallel` | `8`        | Runs at a time                                    |
| `--model`    | `sonnet`   | Model the agent runs on                           |
| `--budget`   | `3.0`      | Spend limit per run, in US dollars                |
| `--timeout`  | `900`      | Time limit per run, in seconds                    |
| `--out`      | timestamp  | Output directory                                  |
| `--rescore`  | off        | Score the runs already in `--out` again           |

## Reading the results

A run passes only when the subentry data matches the task and nothing else changed.
Compare pass rates first, then the actions taken by passing runs, then the agent's reports.
A single run is noisy, so compare medians over at least three repeats.

Holdout tasks are kept out of the default run.
Use them to check that an improvement carries over to tasks a change was not tuned against.

## Tasks

Tasks live in `tools/ux_bench/tasks/`, one JSON file per task.
Every task runs in the same world: the inputs and environment of scenario 6, plus the Solcast sensors of scenario 4.

```json
{
  "id": "add_grid_amber",
  "holdout": false,
  "goal": "Add your grid connection to HAEO. ...",
  "participants": [
    "Inverter",
    "Switchboard",
    "Battery",
    "Solar",
    "Load"
  ],
  "expect": {
    "kind": "add",
    "element_type": "grid",
    "data": {
      "pricing": {
        "price_source_target": {
          "type": "entity",
          "value": {
            "$set": [
              "sensor.amber_express_home_general_price"
            ]
          }
        }
      }
    }
  }
}
```

- `goal` is what the user is told.
    Write it in the user's terms, naming their equipment and intent rather than HAEO's field names.
- `participants` names the scenario 6 elements that already exist when the task starts.
- `expect.kind` is `add` for one new subentry of `element_type`, or `edit` for a change to the existing subentry named by `title`.
- `expect.data` lists only the values the goal decides.
    Keys it leaves out are not checked.
    `{"$set": [...]}` matches a list in any order, `{"$contains": [...]}` matches a list holding each item, and `{"$absent": true}` matches a missing key.

Element flows write their surfaced price fields as rules in the hub's policy subentry.
A change to that subentry counts as part of the task when every rule it adds or removes names the element the task is about.

## How it works

`tools/ux_bench/session.py` runs one task.
It starts Home Assistant through the same `live_home_assistant` helper as the guide tests, seeds the hub, opens HAEO's integration page in Chromium, and serves browse commands on a loopback port.
After the run it saves the hub's subentries before and after to `subentries.json` and scores them with `tools/ux_bench/scoring.py`.

`tools/ux_bench/run.py` starts each session and the agent beside it.
The agent runs in an empty directory with two tools: Bash limited to `./browse`, and Read limited to that directory, where its screenshots land.
It cannot see HAEO's source or documentation.

Home Assistant runs under a frozen clock, so the session uses only timeouts that Playwright enforces in its driver.
Python-side waits such as `wait_for_event` never time out while the clock is frozen.

## Related documentation

<div class="grid cards" markdown>

- :material-form-select:{ .lg .middle } **Config flow**

    ---

    How the element config flows are built.

    [:material-arrow-right: Config flow guide](config-flow.md)

- :material-test-tube:{ .lg .middle } **Testing**

    ---

    Scenario and guide tests.

    [:material-arrow-right: Testing guide](testing.md)

- :material-home-lightning-bolt:{ .lg .middle } **Local simulation**

    ---

    A browsable Home Assistant with scenario data.

    [:material-arrow-right: Local simulation](local-sim.md)

</div>
