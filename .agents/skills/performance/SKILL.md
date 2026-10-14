---
name: performance
description: Measuring and improving HAEO's speed — optimization cycle time, input loading on the event loop, LP rebuild and solve time, output sensor building, pytest-benchmark model benchmarks, and profiling with cProfile. Use when asked to make something faster, when a change could affect solve or load time, when Home Assistant reports a slow or blocking update, or before claiming a performance improvement.
---

# Performance work

## Stages of an optimization cycle

Measure each stage before choosing what to change; which one dominates depends on the configuration and the path being exercised.

- **Input loading** runs on the Home Assistant event loop whenever a source entity changes.
    Forecast integrations write many entities in one pass, so per-change work multiplies by the number of sources in a field.
- **Model rebuild and solve** run in the executor.
    The network persists between cycles: each horizon roll changes the period widths, which rebuilds most constraints, and HiGHS then warm starts.
- **Output extraction and sensor building** run on the event loop after every solve.
- **Cold start** (network build plus the first solve) happens only at setup or reload.

## Rules

- Replace per-period, per-point, and per-row Python loops with numpy operations on whole arrays.
    In the model layer this means `LinearArray`; the `model` skill covers how.
- Work done for every element, output, or sensor must not repeat work that is the same for all of them, such as converting horizon timestamps.
- Coalesce bursts of state changes into one reload, but load immediately when an optimization could otherwise read stale inputs.
- A performance change must not change results.
    Dump every model output before and after across cold solves and horizon rolls and compare them.
    Costs and primal outputs must match; shadow prices may differ only where the LP is degenerate, and the cause must be explained.

## Measuring

- Model benchmarks are disabled by default.
    Run `uv run pytest tests/scenarios/test_benchmark.py -m benchmark --benchmark-enable -o timeout=300` and compare medians against the base branch.
- A benchmark round must change something real.
    Re-solving unchanged inputs measures a warm no-op, which is why `test_time_shift` alternates between two horizons and updates the periods.
- The helpers in `tests/scenarios/test_benchmark.py` build a network from a scenario without Home Assistant, which suits ad hoc timing and `cProfile` scripts.
- Split solve time from Python time by timing `Highs.run` inside `optimize()`; the remainder is model rebuild.

## Profiling pitfalls

- Scenario tests run under freezegun, which also freezes `time.perf_counter`.
    Time with `freezegun.api.real_perf_counter`, and expect datetime-heavy code to look several times slower than it is in production.
- On Python 3.12 and later, `cProfile` records every thread, so executor work appears in an event loop profile.
    Its timings include waiting for the GIL.
- Profile the path a user actually hits, such as a burst of source entity changes or a horizon roll, not only a forced re-run with unchanged inputs.
