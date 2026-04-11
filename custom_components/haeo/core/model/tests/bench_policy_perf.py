"""Performance benchmark: scenario1-equivalent network with and without policies.

Measures optimization time for:
1. Original code path (main branch baseline via single-tag default)
2. New code with no policies (should be equivalent to baseline)
3. New code with policies configured (additional VLAN overhead)

Run with: uv run python custom_components/haeo/core/model/tests/bench_policy_perf.py
"""

import time
from typing import Any

import numpy as np

from custom_components.haeo.core.adapters.tariff_compilation import compile_policies
from custom_components.haeo.core.model.network import Network


def build_scenario1_periods() -> np.ndarray:
    """Build the 110-period time array matching scenario1 tiers."""
    periods_minutes = (
        [1] * 5  # Tier 1: 5 x 1 min
        + [5] * 11  # Tier 2: 11 x 5 min
        + [30] * 46  # Tier 3: 46 x 30 min
        + [60] * 48  # Tier 4: 48 x 60 min
    )
    return np.array(periods_minutes, dtype=float) / 60.0  # Convert to hours


def build_scenario1_elements(n: int) -> list[dict[str, Any]]:
    """Build model elements matching scenario1 topology.

    Grid <-> Switchboard <-> Battery
    Solar -> Switchboard
    Switchboard -> Load
    Inverter is between Solar/Battery and Switchboard in the real config,
    but for model-layer benchmarking we simplify to direct connections.
    """
    # Realistic time-varying data
    np.random.seed(42)
    grid_import = np.clip(0.20 + 0.15 * np.sin(np.linspace(0, 4 * np.pi, n)), 0.05, 0.50)
    grid_export = np.clip(grid_import * 0.3, 0.01, 0.15)
    solar_gen = np.clip(5.0 * np.sin(np.linspace(0, 2 * np.pi, n)), 0, 5.0)
    load_power = np.full(n, 1.5) + 0.5 * np.sin(np.linspace(0, 4 * np.pi, n))

    return [
        {"element_type": "node", "name": "grid", "is_source": True, "is_sink": True},
        {"element_type": "node", "name": "solar", "is_source": True, "is_sink": False},
        {"element_type": "node", "name": "sw", "is_source": False, "is_sink": False},
        {"element_type": "node", "name": "load", "is_source": False, "is_sink": True},
        {"element_type": "battery", "name": "battery", "capacity": 32.0, "initial_charge": 16.0},
        # Grid <-> Switchboard
        {
            "element_type": "connection", "name": "grid_conn", "source": "grid", "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.full(n, 55.0),
                    "max_power_target_source": np.full(n, 30.0),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": grid_import,
                    "price_target_source": -grid_export,
                },
            },
        },
        # Solar -> Switchboard
        {
            "element_type": "connection", "name": "solar_conn", "source": "solar", "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": solar_gen,
                    "max_power_target_source": np.zeros(n),
                },
            },
        },
        # Battery <-> Switchboard
        {
            "element_type": "connection", "name": "battery_conn", "source": "battery", "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.full(n, 25.0),
                    "max_power_target_source": np.full(n, 25.0),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.full(n, 0.02),  # Wear cost
                    "price_target_source": np.full(n, 0.001),
                },
            },
        },
        # Switchboard -> Load
        {
            "element_type": "connection", "name": "load_conn", "source": "sw", "target": "load",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": load_power,
                    "max_power_target_source": np.zeros(n),
                    "fixed": True,
                },
            },
        },
    ]


def benchmark_no_policies(elements: list[dict[str, Any]], periods: np.ndarray, n_runs: int = 10) -> list[float]:
    """Benchmark: no policies configured (tag 0 only, equivalent to old behavior)."""
    times = []
    for _ in range(n_runs):
        network = Network(name="bench", periods=periods)
        for elem in sorted(elements, key=lambda e: e.get("element_type") == "connection"):
            network.add(elem)

        start = time.perf_counter()
        network.optimize()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def benchmark_with_policies(
    elements: list[dict[str, Any]],
    periods: np.ndarray,
    policies: list[dict[str, Any]],
    n_runs: int = 10,
) -> list[float]:
    """Benchmark: with policies configured (multiple VLANs)."""
    times = []
    for _ in range(n_runs):
        compiled = compile_policies([dict(e) for e in elements], policies)
        network = Network(name="bench", periods=periods)
        for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
            network.add(elem)

        start = time.perf_counter()
        network.optimize()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def main() -> None:
    """Run benchmarks."""
    periods = build_scenario1_periods()
    n = len(periods)
    elements = build_scenario1_elements(n)

    n_runs = 20
    print(f"Scenario1-equivalent: {n} periods, {len(elements)} elements, {n_runs} runs each")
    print()

    # 1. No policies (baseline)
    times_no_policy = benchmark_no_policies(elements, periods, n_runs)
    median_no = sorted(times_no_policy)[n_runs // 2]
    mean_no = sum(times_no_policy) / n_runs
    print(f"No policies (baseline):     median={median_no*1000:.1f}ms  mean={mean_no*1000:.1f}ms  min={min(times_no_policy)*1000:.1f}ms  max={max(times_no_policy)*1000:.1f}ms")

    # 2. With simple policies (2 VLANs)
    simple_policies = [
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05},
    ]
    times_simple = benchmark_with_policies(elements, periods, simple_policies, n_runs)
    median_simple = sorted(times_simple)[n_runs // 2]
    mean_simple = sum(times_simple) / n_runs
    print(f"Simple policy (2 VLANs):    median={median_simple*1000:.1f}ms  mean={mean_simple*1000:.1f}ms  min={min(times_simple)*1000:.1f}ms  max={max(times_simple)*1000:.1f}ms")

    # 3. With full policies (4 VLANs - grid, solar, battery each have different treatment)
    full_policies = [
        {"sources": ["solar"], "destinations": ["grid"], "price_source_target": 0.02},
        {"sources": ["battery"], "destinations": ["grid"], "price_source_target": 0.10},
        {"sources": ["battery"], "destinations": ["load"], "price_source_target": 0.01},
        {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.00},
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.00},
        {"sources": ["solar"], "destinations": ["battery"], "price_source_target": 0.00},
        {"sources": ["grid"], "destinations": ["battery"], "price_source_target": 0.00},
    ]
    times_full = benchmark_with_policies(elements, periods, full_policies, n_runs)
    median_full = sorted(times_full)[n_runs // 2]
    mean_full = sum(times_full) / n_runs
    print(f"Full policies (4 VLANs):    median={median_full*1000:.1f}ms  mean={mean_full*1000:.1f}ms  min={min(times_full)*1000:.1f}ms  max={max(times_full)*1000:.1f}ms")

    # 4. With merged policies (all same price = 2 VLANs after merging)
    merged_policies = [
        {"sources": ["*"], "destinations": ["load"], "price_source_target": 0.05},
    ]
    times_merged = benchmark_with_policies(elements, periods, merged_policies, n_runs)
    median_merged = sorted(times_merged)[n_runs // 2]
    mean_merged = sum(times_merged) / n_runs
    print(f"Wildcard policy (2 VLANs):  median={median_merged*1000:.1f}ms  mean={mean_merged*1000:.1f}ms  min={min(times_merged)*1000:.1f}ms  max={max(times_merged)*1000:.1f}ms")

    print()
    print(f"Overhead vs baseline:")
    print(f"  Simple (2 VLANs):   {median_simple/median_no:.2f}x")
    print(f"  Full (4 VLANs):     {median_full/median_no:.2f}x")
    print(f"  Wildcard (2 VLANs): {median_merged/median_no:.2f}x")

    # Count variables
    for label, elems in [("No policies", elements), ("Full policies", compile_policies([dict(e) for e in elements], full_policies))]:
        network = Network(name="count", periods=periods)
        for elem in sorted(elems, key=lambda e: e.get("element_type") == "connection"):
            network.add(elem)
        network.optimize()
        h = network._solver
        print(f"\n{label}: {h.getNumCol()} variables, {h.getNumRow()} constraints")


if __name__ == "__main__":
    main()
