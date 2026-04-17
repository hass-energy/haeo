"""Model-layer benchmark using real scenario data.

Measures optimization performance at the network/model layer without
Home Assistant in the loop. Collects per-phase timing for the
lexicographic multi-objective solve.

Run with:
    uv run pytest tests/scenarios/test_benchmark.py -m scenario -s
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from typing import Any

import numpy as np
import pytest

from custom_components.haeo.coordinator.network import update_element
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.data.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds
from custom_components.haeo.core.data.loader.config_loader import load_element_configs
from custom_components.haeo.core.model.network import Network, SolveOptions
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.core.state import EntityState

# ---------------------------------------------------------------------------
# Lightweight StateMachine backed by scenario inputs.json
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _EntityState:
    """Minimal EntityState for the core data-loading pipeline."""

    entity_id: str
    state: str
    attributes: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "state": self.state,
            "attributes": dict(self.attributes),
        }


class _ScenarioStateMachine:
    """StateMachine backed by a list of state dicts from inputs.json."""

    def __init__(self, inputs: list[dict[str, Any]]) -> None:
        self._states: dict[str, _EntityState] = {}
        for entry in inputs:
            entity_id = entry["entity_id"]
            self._states[entity_id] = _EntityState(
                entity_id=entity_id,
                state=entry["state"],
                attributes=entry.get("attributes", {}),
            )

    def get(self, entity_id: str) -> EntityState | None:
        return self._states.get(entity_id)


# ---------------------------------------------------------------------------
# Per-phase timing instrumentation
# ---------------------------------------------------------------------------


@dataclass
class PhaseTimings:
    """Timing breakdown for a single optimize() call."""

    total_ns: int = 0
    constraint_ns: int = 0
    cost_ns: int = 0
    phase1_ns: int = 0
    phase2_ns: int = 0
    phase3_ns: int = 0
    n_variables: int = 0
    n_constraints: int = 0

    @property
    def total_ms(self) -> float:
        """Total time in milliseconds."""
        return self.total_ns / 1_000_000

    @property
    def constraint_ms(self) -> float:
        """Constraint generation time in milliseconds."""
        return self.constraint_ns / 1_000_000

    @property
    def cost_ms(self) -> float:
        """Cost computation time in milliseconds."""
        return self.cost_ns / 1_000_000

    @property
    def phase1_ms(self) -> float:
        """Phase 1 solve time in milliseconds."""
        return self.phase1_ns / 1_000_000

    @property
    def phase2_ms(self) -> float:
        """Phase 2 solve time in milliseconds."""
        return self.phase2_ns / 1_000_000

    @property
    def phase3_ms(self) -> float:
        """Phase 3 solve time in milliseconds."""
        return self.phase3_ns / 1_000_000


def _timed_optimize(network: Network) -> PhaseTimings:
    """Run network.optimize() with per-phase timing instrumentation.

    Wraps the solver's run() method to capture per-phase timing without
    modifying the Network class.
    """
    timings = PhaseTimings()
    h = network._solver
    phase_times: list[int] = []

    original_run = h.run

    def timed_run() -> Any:
        start = time.perf_counter_ns()
        result = original_run()
        phase_times.append(time.perf_counter_ns() - start)
        return result

    h.run = timed_run  # type: ignore[assignment]
    try:
        # Pre-measure constraint and cost overhead (these are also called
        # inside optimize(), but measuring separately shows their contribution)
        tc0 = time.perf_counter_ns()
        for element in network.elements.values():
            element.constraints()
        timings.constraint_ns = time.perf_counter_ns() - tc0

        tco0 = time.perf_counter_ns()
        network.cost()
        timings.cost_ns = time.perf_counter_ns() - tco0

        # Full optimize (includes constraint/cost collection + solver phases)
        t0 = time.perf_counter_ns()
        network.optimize()
        timings.total_ns = time.perf_counter_ns() - t0
    finally:
        h.run = original_run  # type: ignore[assignment]

    if len(phase_times) >= 1:
        timings.phase1_ns = phase_times[0]
    if len(phase_times) >= 2:
        timings.phase2_ns = phase_times[1]
    if len(phase_times) >= 3:
        timings.phase3_ns = phase_times[2]

    timings.n_variables = h.numVariables
    timings.n_constraints = h.getNumRow()

    return timings


# ---------------------------------------------------------------------------
# Network construction from scenario data
# ---------------------------------------------------------------------------


def _load_scenario(
    scenario_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """Load scenario files from disk."""
    with (scenario_path / "config.json").open() as f:
        config = json.load(f)
    with (scenario_path / "environment.json").open() as f:
        environment = json.load(f)
    with (scenario_path / "inputs.json").open() as f:
        inputs = json.load(f)
    return config, inputs, environment["timestamp"]


def _build_network(
    config: dict[str, Any],
    sm: _ScenarioStateMachine,
    frozen_dt: datetime,
    options: SolveOptions | None = None,
) -> Network:
    """Build a Network from scenario data without Home Assistant.

    All timestamps are explicitly passed so no freeze_time is needed.
    """
    participants: dict[str, ElementConfigSchema] = config["participants"]
    periods_seconds = tiers_to_periods_seconds(config, start_time=frozen_dt)
    periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
    forecast_times = generate_forecast_timestamps(periods_seconds, start_time=frozen_dt.timestamp())

    loaded_configs = load_element_configs(participants, sm, forecast_times)

    if options is None:
        network = Network(name="benchmark", periods=periods_hours)
    else:
        network = Network(name="benchmark", periods=periods_hours, options=options)
    for element_config in collect_model_elements(loaded_configs):
        network.add(element_config)

    return network


def _load_configs(
    config: dict[str, Any],
    sm: _ScenarioStateMachine,
    frozen_dt: datetime,
) -> dict[str, ElementConfigData]:
    """Load element configs resolved against scenario state machine."""
    periods_seconds = tiers_to_periods_seconds(config, start_time=frozen_dt)
    forecast_times = generate_forecast_timestamps(periods_seconds, start_time=frozen_dt.timestamp())
    return load_element_configs(config["participants"], sm, forecast_times)


def _load_shifted_configs(
    config: dict[str, Any],
    sm: _ScenarioStateMachine,
    frozen_dt: datetime,
    shift_seconds: int,
) -> dict[str, ElementConfigData]:
    """Load element configs with time shifted forward."""
    shifted_epoch = frozen_dt.timestamp() + shift_seconds
    shifted_dt = datetime.fromtimestamp(shifted_epoch, tz=UTC)
    shifted_periods = tiers_to_periods_seconds(config, start_time=shifted_dt)
    shifted_forecast_times = generate_forecast_timestamps(shifted_periods, start_time=shifted_epoch)
    return load_element_configs(config["participants"], sm, shifted_forecast_times)


# ---------------------------------------------------------------------------
# Benchmark test
# ---------------------------------------------------------------------------


def _discover_scenarios() -> list[Path]:
    scenarios_dir = Path(__file__).parent
    required_files = ("config.json", "environment.json", "inputs.json")
    return sorted(path for path in scenarios_dir.glob("scenario*/") if all((path / f).exists() for f in required_files))


_scenarios = _discover_scenarios()

WARMUP_ITERATIONS = 2
BENCHMARK_ITERATIONS = 10


def _format_timings(label: str, timings_list: list[PhaseTimings]) -> str:
    """Format a list of timings as a summary line with mean values."""
    totals = [t.total_ms for t in timings_list]
    p1s = [t.phase1_ms for t in timings_list]
    p2s = [t.phase2_ms for t in timings_list]
    p3s = [t.phase3_ms for t in timings_list]
    constraints = [t.constraint_ms for t in timings_list]
    costs = [t.cost_ms for t in timings_list]

    def _mean(values: list[float]) -> str:
        if not values or max(values) == 0:
            return "    -  "
        return f"{sum(values) / len(values):7.2f}"

    return (
        f"  {label:<24s}"
        f"  total={_mean(totals)}ms"
        f"  P1={_mean(p1s)}ms"
        f"  P2={_mean(p2s)}ms"
        f"  P3={_mean(p3s)}ms"
        f"  constr={_mean(constraints)}ms"
        f"  cost={_mean(costs)}ms"
    )


@pytest.mark.benchmark
@pytest.mark.timeout(120)
@pytest.mark.parametrize(
    "scenario_path",
    _scenarios,
    ids=[s.name for s in _scenarios],
    indirect=["scenario_path"],
)
def test_benchmark(scenario_path: Path) -> None:
    """Benchmark optimization performance using real scenario data."""
    config, inputs, freeze_timestamp = _load_scenario(scenario_path)
    frozen_dt = datetime.fromisoformat(freeze_timestamp)
    sm = _ScenarioStateMachine(inputs)

    # Build one network to show dimensions
    network = _build_network(config, sm, frozen_dt)
    network.optimize()
    n_elements = len(network.elements)
    n_vars = network._solver.numVariables
    n_rows = network._solver.getNumRow()

    print(f"\n{'=' * 80}")  # noqa: T201
    print(f"  {scenario_path.name}: {n_elements} elements, {n_vars} vars, {n_rows} constraints")  # noqa: T201
    print(f"{'=' * 80}")  # noqa: T201

    # --- 1. Initial optimization (cold start) ---
    initial_timings: list[PhaseTimings] = []
    for i in range(WARMUP_ITERATIONS + BENCHMARK_ITERATIONS):
        net = _build_network(config, sm, frozen_dt)
        t = _timed_optimize(net)
        if i >= WARMUP_ITERATIONS:
            initial_timings.append(t)
    print(_format_timings("initial (cold)", initial_timings))  # noqa: T201

    # --- 2. Reentrant optimization (no changes) ---
    network = _build_network(config, sm, frozen_dt)
    network.optimize()  # prime

    reentrant_timings: list[PhaseTimings] = []
    for i in range(WARMUP_ITERATIONS + BENCHMARK_ITERATIONS):
        t = _timed_optimize(network)
        if i >= WARMUP_ITERATIONS:
            reentrant_timings.append(t)
    print(_format_timings("reentrant (no-op)", reentrant_timings))  # noqa: T201

    # --- 3. Update first participant's tracked params ---
    loaded_configs = _load_configs(config, sm, frozen_dt)
    first_name = next(iter(loaded_configs))
    first_config = loaded_configs[first_name]

    network = _build_network(config, sm, frozen_dt)
    network.optimize()  # prime

    update_timings: list[PhaseTimings] = []
    for i in range(WARMUP_ITERATIONS + BENCHMARK_ITERATIONS):
        update_element(network, first_config)
        t = _timed_optimize(network)
        if i >= WARMUP_ITERATIONS:
            update_timings.append(t)
    print(_format_timings(f"update ({first_name})", update_timings))  # noqa: T201

    # --- 4. Full re-update of all elements ---
    network = _build_network(config, sm, frozen_dt)
    network.optimize()  # prime

    all_update_timings: list[PhaseTimings] = []
    for i in range(WARMUP_ITERATIONS + BENCHMARK_ITERATIONS):
        for elem_config in loaded_configs.values():
            update_element(network, elem_config)
        t = _timed_optimize(network)
        if i >= WARMUP_ITERATIONS:
            all_update_timings.append(t)
    print(_format_timings("update (all elements)", all_update_timings))  # noqa: T201

    # --- 5. Time shift (shifted forecast times, all params updated) ---
    periods_seconds = tiers_to_periods_seconds(config, start_time=frozen_dt)
    shift_seconds = periods_seconds[0]  # one tick
    shifted_configs = _load_shifted_configs(config, sm, frozen_dt, shift_seconds)

    shift_timings: list[PhaseTimings] = []
    for i in range(WARMUP_ITERATIONS + BENCHMARK_ITERATIONS):
        network = _build_network(config, sm, frozen_dt)
        network.optimize()

        for elem_config in shifted_configs.values():
            update_element(network, elem_config)
        t = _timed_optimize(network)
        if i >= WARMUP_ITERATIONS:
            shift_timings.append(t)
    print(_format_timings("time shift (+1 tick)", shift_timings))  # noqa: T201

    print(f"{'=' * 80}\n")  # noqa: T201
