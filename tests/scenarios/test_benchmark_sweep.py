"""Parametric sweep benchmark over HiGHS solver options.

Sweeps the cartesian product of relevant SolveOptions values against a
single representative scenario, measuring per-workload mean wall time.
The intent is to identify which options materially affect performance.

Run with:
    uv run pytest tests/scenarios/test_benchmark_sweep.py -m scenario -s
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import signal
import time
from typing import Any

import pytest

from custom_components.haeo.coordinator.network import update_element
from custom_components.haeo.core.data.forecast_times import tiers_to_periods_seconds
from custom_components.haeo.core.model.network import SolveOptions
from tests.scenarios.test_benchmark import _build_network, _load_scenario, _load_shifted_configs, _ScenarioStateMachine

SWEEP_SCENARIO = "scenario1"
WARMUP = 1
ITERATIONS = 3


@dataclass(frozen=True)
class SweepCase:
    """A single point in the option sweep grid."""

    label: str
    options: SolveOptions


def _expand_grid(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Return the cartesian product of option values."""
    combos: list[dict[str, Any]] = [{}]
    for key, values in grid.items():
        combos = [{**c, key: v} for c in combos for v in values]
    return combos


def _build_sweep() -> list[SweepCase]:
    """Build a curated sweep of meaningful option combinations.

    Avoids the full cartesian explosion by restricting each algorithm
    family to its own relevant option subset (e.g. simplex_strategy
    is only meaningful when solver=='simplex').
    """
    cases: list[SweepCase] = []

    simplex_grid = {
        "mode": ["lex", "blended", "calibrated"],
        "simplex_strategy": [1, 4],  # dual vs primal
        "presolve": ["choose", "on", "off"],
        "simplex_scale_strategy": [0, 2],
    }
    for combo in _expand_grid(simplex_grid):
        opts = SolveOptions(solver="simplex", **combo)
        label = (
            f"simplex mode={combo['mode']:<10s}"
            f" strat={combo['simplex_strategy']}"
            f" pre={combo['presolve']:<6s}"
            f" scale={combo['simplex_scale_strategy']}"
        )
        cases.append(SweepCase(label=label, options=opts))

    # IPM: crossover must be on for lex mode (phases need a basic solution),
    # but blended mode works with crossover off.
    for combo in _expand_grid({"presolve": ["choose", "off"]}):
        # lex + crossover on
        opts = SolveOptions(solver="ipm", mode="lex", run_crossover="on", **combo)
        label = f"ipm     mode=lex        pre={combo['presolve']:<6s} cross=on     scale=-"
        cases.append(SweepCase(label=label, options=opts))
        # blended + crossover on and off
        for cross in ("on", "off"):
            opts = SolveOptions(solver="ipm", mode="blended", run_crossover=cross, **combo)
            label = f"ipm     mode=blended    pre={combo['presolve']:<6s} cross={cross:<6s} scale=-"
            cases.append(SweepCase(label=label, options=opts))

    return cases


SWEEP_CASES = _build_sweep()


# Per-config wall-clock timeout in seconds.  IPM configs can hang if crossover
# is misconfigured or the solver enters a degenerate path.
CONFIG_TIMEOUT_SECONDS = 30


class _ConfigTimeoutError(Exception):
    """Raised when a single sweep configuration exceeds its time budget."""


def _alarm_handler(_signum: int, _frame: object) -> None:
    raise _ConfigTimeoutError


def _bench(callable_: Callable[[], object], n: int) -> float:
    """Run callable_ n times and return mean wall time in milliseconds."""
    times: list[int] = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        callable_()
        times.append(time.perf_counter_ns() - t0)
    return (sum(times) / len(times)) / 1_000_000


def _measure(
    config: dict[str, Any],
    sm: _ScenarioStateMachine,
    frozen_dt: datetime,
    options: SolveOptions,
) -> dict[str, float | str]:
    """Run all workloads for one options configuration."""
    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(CONFIG_TIMEOUT_SECONDS)
    try:
        # Workload 1: cold start (build + first solve)
        def cold() -> None:
            net = _build_network(config, sm, frozen_dt, options=options)
            net.optimize()

        # Workload 2: warm reentrant (no changes)
        warm_net = _build_network(config, sm, frozen_dt, options=options)
        warm_net.optimize()

        def warm_reentrant() -> None:
            warm_net.optimize()

        # Workload 3: warm solve after time-shifted updates to all elements
        shift_net = _build_network(config, sm, frozen_dt, options=options)
        shift_net.optimize()
        periods_seconds = tiers_to_periods_seconds(config, start_time=frozen_dt)
        shifted = _load_shifted_configs(config, sm, frozen_dt, periods_seconds[0])

        def warm_shift() -> None:
            for elem_config in shifted.values():
                update_element(shift_net, elem_config)
            shift_net.optimize()

        for _ in range(WARMUP):
            cold()
            warm_reentrant()
            warm_shift()

        return {
            "status": "ok",
            "cold_ms": _bench(cold, ITERATIONS),
            "warm_ms": _bench(warm_reentrant, ITERATIONS),
            "shift_ms": _bench(warm_shift, ITERATIONS),
        }
    except _ConfigTimeoutError:
        return {"status": f"TIMEOUT after {CONFIG_TIMEOUT_SECONDS}s"}
    except Exception as exc:
        return {"status": f"FAIL: {type(exc).__name__}: {exc}"[:80]}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


# Module-level result table accumulated across parametrized cases.
_results: list[tuple[str, dict[str, float | str]]] = []


@pytest.fixture(scope="module")
def sweep_data() -> tuple[dict[str, Any], _ScenarioStateMachine, datetime]:
    """Load sweep scenario data once per module."""
    path = Path(__file__).parent / SWEEP_SCENARIO
    if not (path / "config.json").exists():
        pytest.skip(f"Sweep scenario {SWEEP_SCENARIO} not present")
    config, inputs, freeze_timestamp = _load_scenario(path)
    return config, _ScenarioStateMachine(inputs), datetime.fromisoformat(freeze_timestamp)


@pytest.mark.benchmark
@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    "case",
    SWEEP_CASES,
    ids=[c.label.replace(" ", "_") for c in SWEEP_CASES],
)
def test_sweep_case(
    case: SweepCase,
    sweep_data: tuple[dict[str, Any], _ScenarioStateMachine, datetime],
) -> None:
    """Run one option configuration and record its workload timings."""
    config, sm, frozen_dt = sweep_data
    result = _measure(config, sm, frozen_dt, case.options)
    _results.append((case.label, result))


@pytest.mark.benchmark
def test_zsweep_summary() -> None:
    """Print accumulated sweep results as a sortable table.

    Prefixed with 'z' so it runs after all parametrized cases (pytest
    preserves source order for tests in a module, but this gives a
    secondary alphabetical guarantee).
    """
    if not _results:
        pytest.skip("No sweep results collected")

    ok_results = [(lbl, r) for lbl, r in _results if r.get("status") == "ok"]
    ok_results.sort(key=lambda item: float(item[1]["warm_ms"]))  # type: ignore[arg-type]
    failed = [(lbl, r) for lbl, r in _results if r.get("status") != "ok"]

    width = max(len(lbl) for lbl, _ in _results)
    header = f"{'configuration':<{width}}  {'cold':>8}  {'warm':>8}  {'shift':>8}"
    bar = "=" * len(header)
    sep = "-" * len(header)

    print()  # noqa: T201
    print(bar)  # noqa: T201
    print(f"  Parametric sweep: {SWEEP_SCENARIO} ({len(ok_results)} ok / {len(failed)} failed, sorted by warm)")  # noqa: T201
    print(bar)  # noqa: T201
    print(header)  # noqa: T201
    print(sep)  # noqa: T201
    for lbl, r in ok_results:
        print(  # noqa: T201
            f"{lbl:<{width}}"
            f"  {float(r['cold_ms']):>6.2f}ms"
            f"  {float(r['warm_ms']):>6.2f}ms"
            f"  {float(r['shift_ms']):>6.2f}ms"
        )

    if failed:
        print()  # noqa: T201
        print(f"Failed configurations ({len(failed)}):")  # noqa: T201
        for lbl, r in failed:
            print(f"  {lbl}: {r['status']}")  # noqa: T201
    print()  # noqa: T201
