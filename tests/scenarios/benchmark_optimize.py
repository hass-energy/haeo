"""Benchmark cold and warm optimization timing using scenario data.

Usage:
    uv run python tests/scenarios/benchmark_optimize.py

Compares three solve strategies across all scenarios:
- 1-solve: primary objective only (what main branch does)
- 2-solve: primary + secondary (lexicographic, no dual correction)
- 3-solve: primary + secondary + re-primary (correct shadow prices)

Each is measured for:
- Cold solve: first optimization (builds all constraints + variables)
- Warm solve: subsequent optimization (reuses existing model structure)
"""

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.data.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds
from custom_components.haeo.core.data.loader.config_loader import load_element_configs
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.network import (
    _build_cost_vectors,
    _clear_linear_objectives,
    _ensure_optimal,
    _set_cost_vector,
)


# ---------------------------------------------------------------------------
# Minimal StateMachine / EntityState implementations for offline use
# ---------------------------------------------------------------------------


@dataclass
class SimpleEntityState:
    """Lightweight EntityState for benchmark use."""

    entity_id: str
    state: str
    attributes: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "state": self.state,
            "attributes": dict(self.attributes),
        }


class SimpleStateMachine:
    """In-memory state machine that fulfills the StateMachine Protocol."""

    def __init__(self) -> None:
        self._states: dict[str, SimpleEntityState] = {}

    def set(self, entity_id: str, state: str, attributes: dict[str, Any]) -> None:
        self._states[entity_id] = SimpleEntityState(entity_id, state, attributes)

    def get(self, entity_id: str) -> SimpleEntityState | None:
        return self._states.get(entity_id)


# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------


def load_scenario(scenario_path: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Load config, environment, and inputs from a scenario directory."""
    with (scenario_path / "config.json").open() as f:
        config = json.load(f)
    with (scenario_path / "environment.json").open() as f:
        environment = json.load(f)
    with (scenario_path / "inputs.json").open() as f:
        inputs = json.load(f)
    return config, environment, inputs


def build_network_from_scenario(scenario_path: Path) -> Network:
    """Build a Network from scenario data, bypassing Home Assistant."""
    config, environment, inputs = load_scenario(scenario_path)

    # Build state machine from inputs
    sm = SimpleStateMachine()
    for state_data in inputs:
        sm.set(
            state_data["entity_id"],
            state_data["state"],
            state_data.get("attributes", {}),
        )

    # Compute forecast timestamps from tier config + scenario timestamp
    timestamp = datetime.fromisoformat(environment["timestamp"])
    periods_seconds = tiers_to_periods_seconds(config, start_time=timestamp)
    forecast_times = generate_forecast_timestamps(
        periods_seconds,
        start_time=timestamp.timestamp(),
    )

    # Resolve schema values → loaded ElementConfigData
    participants = load_element_configs(config["participants"], sm, forecast_times)

    # Build network
    periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
    net = Network(name=scenario_path.name, periods=periods_hours)

    sorted_elements = collect_model_elements(participants)
    for el in sorted_elements:
        net.add(el)

    return net


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _optimize_n_solves(net: Network, max_solves: int) -> float:
    """Run optimize with a capped number of solves using batch API (for benchmarking)."""
    net.validate()
    h = net._solver  # noqa: SLF001

    for element_name, element in net.elements.items():
        try:
            element.constraints()
        except Exception as e:
            msg = f"Failed to apply constraints for element '{element_name}'"
            raise ValueError(msg) from e

    objectives = net.cost()
    _clear_linear_objectives(h)

    if objectives is None:
        h.run()
        return _ensure_optimal(h)

    n_vars = h.numVariables
    all_col_indices = np.arange(n_vars, dtype=np.int32)
    cost_vectors = _build_cost_vectors(objectives, n_vars)

    from highspy import ObjSense

    h.changeObjectiveSense(ObjSense.kMinimize)

    primary = objectives[0]
    secondary = objectives[1] if len(objectives) > 1 else None

    if primary is None:
        h.run()
        _ensure_optimal(h)
        return 0.0

    # Relax lex constraint for primary solve
    net._relax_lex_constraint()  # noqa: SLF001
    _set_cost_vector(h, all_col_indices, cost_vectors[0])
    h.run()
    primary_value = _ensure_optimal(h)

    if max_solves >= 2 and secondary is not None:
        net._constrain_objective(primary, primary_value)  # noqa: SLF001
        _set_cost_vector(h, all_col_indices, cost_vectors[1])
        h.run()
        _ensure_optimal(h)

    return primary_value


MODES = [("1-solve", 1), ("2-solve", 2), ("3-solve", 0)]  # 0 = use full optimize()


def benchmark_scenario(scenario_path: Path, warm_iterations: int = 5) -> dict[str, Any]:
    """Benchmark cold and warm optimizations for a single scenario."""
    results: dict[str, Any] = {
        "scenario": scenario_path.name,
    }

    for mode, max_solves in MODES:
        net = build_network_from_scenario(scenario_path)

        if max_solves > 0:
            optimize_fn = lambda n=net, m=max_solves: _optimize_n_solves(n, m)
        else:
            optimize_fn = net.optimize

        # Cold solve
        start = time.perf_counter()
        cold_cost = optimize_fn()
        cold_time = time.perf_counter() - start

        # Warm solves
        warm_times: list[float] = []
        for _ in range(warm_iterations):
            start = time.perf_counter()
            optimize_fn()
            warm_times.append(time.perf_counter() - start)

        results[f"{mode}_cold_ms"] = cold_time * 1000
        results[f"{mode}_cold_cost"] = cold_cost
        results[f"{mode}_warm_avg_ms"] = sum(warm_times) / len(warm_times) * 1000
        results[f"{mode}_warm_min_ms"] = min(warm_times) * 1000
        results[f"{mode}_warm_max_ms"] = max(warm_times) * 1000
        results["n_periods"] = net.n_periods
        results["n_elements"] = len(net.elements)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    scenarios_dir = Path(__file__).parent
    scenario_paths = sorted(scenarios_dir.glob("scenario*/"))
    scenario_paths = [
        p for p in scenario_paths if (p / "config.json").exists() and (p / "inputs.json").exists()
    ]

    if not scenario_paths:
        print("No scenarios found.")
        return

    print(f"Benchmarking {len(scenario_paths)} scenarios: 1-solve vs 2-solve vs 3-solve")
    print("=" * 110)

    all_modes = [m for m, _ in MODES]

    results: list[dict[str, Any]] = []
    for scenario_path in scenario_paths:
        print(f"\n{scenario_path.name}:")
        try:
            result = benchmark_scenario(scenario_path, warm_iterations=10)
            results.append(result)
            print(f"  {result['n_periods']} periods, {result['n_elements']} elements")
            for mode in all_modes:
                print(
                    f"  {mode}:  Cold {result[f'{mode}_cold_ms']:7.1f} ms  |  "
                    f"Warm avg {result[f'{mode}_warm_avg_ms']:7.1f} ms  "
                    f"[{result[f'{mode}_warm_min_ms']:.1f} - {result[f'{mode}_warm_max_ms']:.1f}]"
                )
        except Exception as e:
            print(f"  ERROR: {e}")

    # Summary table
    print("\n" + "=" * 110)
    print("\nCold solve times:")
    header = f"{'Scenario':<12} {'Periods':>7}"
    for mode in all_modes:
        header += f" {mode:>10}"
    header += "   Δ(1→2)    Δ(1→3)"
    print(header)
    print("-" * 110)
    for r in results:
        line = f"{r['scenario']:<12} {r['n_periods']:>7}"
        for mode in all_modes:
            line += f" {r[f'{mode}_cold_ms']:>9.1f}ms"
        d12 = r["2-solve_cold_ms"] - r["1-solve_cold_ms"]
        d13 = r["3-solve_cold_ms"] - r["1-solve_cold_ms"]
        line += f"  {d12:>+7.1f}ms  {d13:>+7.1f}ms"
        print(line)

    print("\nWarm solve times (avg):")
    header = f"{'Scenario':<12} {'Periods':>7}"
    for mode in all_modes:
        header += f" {mode:>10}"
    header += "   Δ(1→2)    Δ(1→3)"
    print(header)
    print("-" * 110)
    for r in results:
        line = f"{r['scenario']:<12} {r['n_periods']:>7}"
        for mode in all_modes:
            line += f" {r[f'{mode}_warm_avg_ms']:>9.1f}ms"
        d12 = r["2-solve_warm_avg_ms"] - r["1-solve_warm_avg_ms"]
        d13 = r["3-solve_warm_avg_ms"] - r["1-solve_warm_avg_ms"]
        line += f"  {d12:>+7.1f}ms  {d13:>+7.1f}ms"
        print(line)


if __name__ == "__main__":
    main()
