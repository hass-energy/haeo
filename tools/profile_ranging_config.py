"""Measure HiGHS getRanging() cost vs solver configuration and solve state.

Builds scenario1 (typical) and scenario6 (largest) networks, times solve and
ranging separately, and prints median timings (ms) per configuration.

Run with:
    uv run python tools/profile_ranging_config.py 2>/dev/null
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import time
from typing import Any

import numpy as np

from custom_components.haeo.core.model import network as network_mod
from custom_components.haeo.core.model.network import CalibratedOptions, Network, OnOffChoose
from custom_components.haeo.core.model.reactive.decorators import populate_ranging
from tests.scenarios.test_benchmark import _build_network, _load_scenario, _ScenarioStateMachine

_REPEAT = 40
_SCENARIOS = ("scenario1", "scenario6")
_REPO = Path(__file__).resolve().parent.parent


def _median_ms(fn: Callable[[], object], repeat: int = _REPEAT) -> float:
    samples: list[float] = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1e3)
    return float(np.median(samples))


def _noop_ranging(_solver: object) -> None:
    return None


def _load_network(scenario_name: str, *, presolve: OnOffChoose, simplex_strategy: int) -> Network:
    scenario_path = _REPO / "tests" / "scenarios" / scenario_name
    config, inputs, freeze_timestamp = _load_scenario(scenario_path)
    frozen_dt = datetime.fromisoformat(freeze_timestamp)
    sm = _ScenarioStateMachine(inputs)
    options = CalibratedOptions(presolve=presolve, simplex_strategy=simplex_strategy)
    network, _ = _build_network(config, sm, frozen_dt, options=options)
    return network


def _prime_calibrated(network: Network) -> None:
    """Run enough optimizes to reach production warm blended path."""
    network.optimize()
    network.optimize()


def _solve_without_ranging(network: Network) -> None:
    network_mod.populate_ranging = _noop_ranging
    try:
        network.optimize()
    finally:
        network_mod.populate_ranging = populate_ranging


def _ranging_valid(solver: Any) -> bool:
    _status, rng = solver.getRanging()
    return bool(rng.valid)


def _finite_ranging_checksum(solver: Any) -> float | None:
    """Checksum of finite row bound ranging values for cross-config comparison."""
    _status, rng = solver.getRanging()
    if not rng.valid:
        return None
    up = np.asarray(rng.row_bound_up.value_, dtype=float)
    dn = np.asarray(rng.row_bound_dn.value_, dtype=float)
    finite = np.isfinite(up) & np.isfinite(dn)
    if not np.any(finite):
        return None
    return float(np.sum(up[finite]) + np.sum(dn[finite]))


def _print_table(title: str, rows: list[tuple[str, float, float, float]]) -> None:
    print(f"\n{title}")
    header = f"{'config':<28} {'solve_ms':>10} {'getRanging_ms':>14} {'getSolution_ms':>14}"
    print(header)
    print("-" * len(header))
    for config, solve_ms, ranging_ms, solution_ms in rows:
        print(f"{config:<28} {solve_ms:>10.2f} {ranging_ms:>14.2f} {solution_ms:>14.4f}")


def _measure_warm_standard(
    scenario_name: str,
    *,
    presolve: OnOffChoose,
    simplex_strategy: int,
    label: str,
) -> tuple[str, float, float, float, bool, float | None]:
    network = _load_network(scenario_name, presolve=presolve, simplex_strategy=simplex_strategy)
    _prime_calibrated(network)
    solver = network._solver  # noqa: SLF001

    solve_ms = _median_ms(lambda: _solve_without_ranging(network))
    ranging_ms = _median_ms(solver.getRanging)
    solution_ms = _median_ms(solver.getSolution)
    valid = _ranging_valid(solver)
    checksum = _finite_ranging_checksum(solver)
    return label, solve_ms, ranging_ms, solution_ms, valid, checksum


def _measure_presolve_and_strategy(scenario_name: str) -> list[tuple[str, float, float, float]]:
    rows: list[tuple[str, float, float, float]] = []
    configs: list[tuple[str, OnOffChoose, int]] = [
        ("presolve=choose strat=4 (prod)", "choose", 4),
        ("presolve=off strat=4", "off", 4),
        ("presolve=on strat=4", "on", 4),
        ("presolve=choose strat=1 (dual)", "choose", 1),
        ("presolve=choose strat=4 (primal)", "choose", 4),
    ]
    seen: set[tuple[OnOffChoose, int]] = set()
    for label, presolve, strategy in configs:
        key = (presolve, strategy)
        if key in seen:
            continue
        seen.add(key)
        row = _measure_warm_standard(scenario_name, presolve=presolve, simplex_strategy=strategy, label=label)
        rows.append(row[:4])
    return rows


def _measure_warm_vs_cold(scenario_name: str) -> None:
    """Compare getRanging after first solve (cold) vs after warm re-solve."""
    print(f"\n{scenario_name} — warm vs cold getRanging (presolve=choose, strat=4)")
    header = f"{'state':<12} {'solve_ms':>10} {'getRanging_ms':>14} {'valid':>6}"
    print(header)
    print("-" * len(header))

    # Cold: fresh network, first solve only.
    network_cold = _load_network(scenario_name, presolve="choose", simplex_strategy=4)
    cold_solve_ms = _median_ms(lambda: _solve_without_ranging(network_cold))
    cold_rng_ms = _median_ms(network_cold._solver.getRanging)  # noqa: SLF001
    cold_valid = _ranging_valid(network_cold._solver)  # noqa: SLF001
    print(f"{'cold (1st)':<12} {cold_solve_ms:>10.2f} {cold_rng_ms:>14.2f} {cold_valid!s:>6}")

    # Warm: primed network, re-solve then ranging.
    network_warm = _load_network(scenario_name, presolve="choose", simplex_strategy=4)
    _prime_calibrated(network_warm)
    warm_solve_ms = _median_ms(lambda: _solve_without_ranging(network_warm))
    warm_rng_ms = _median_ms(network_warm._solver.getRanging)  # noqa: SLF001
    warm_valid = _ranging_valid(network_warm._solver)  # noqa: SLF001
    print(f"{'warm (re)':<12} {warm_solve_ms:>10.2f} {warm_rng_ms:>14.2f} {warm_valid!s:>6}")


def _measure_double_ranging(scenario_name: str) -> None:
    """Two getRanging() calls on the same basis without re-solve."""
    network = _load_network(scenario_name, presolve="choose", simplex_strategy=4)
    _prime_calibrated(network)
    _solve_without_ranging(network)
    solver = network._solver  # noqa: SLF001

    first_ms = _median_ms(solver.getRanging)
    second_ms = _median_ms(solver.getRanging)
    ratio = second_ms / first_ms if first_ms else 0.0
    print(
        f"\n{scenario_name} — double getRanging (same basis): "
        f"1st={first_ms:.2f} ms  2nd={second_ms:.2f} ms  ratio={ratio:.2f}"
    )


def _measure_correctness_notes(scenario_name: str) -> None:
    """Compare ranging validity and fingerprints across presolve settings."""
    print(f"\n{scenario_name} — ranging validity / fingerprint (after warm solve)")
    header = f"{'config':<22} {'valid':>6} {'finite_checksum':>18}"
    print(header)
    print("-" * len(header))
    checksums: dict[str, float | None] = {}
    for presolve in ("off", "on", "choose"):
        label, *_rest, valid, checksum = _measure_warm_standard(
            scenario_name,
            presolve=presolve,  # type: ignore[arg-type]
            simplex_strategy=4,
            label=f"presolve={presolve}",
        )
        checksums[label] = checksum
        cs = f"{checksum:.8g}" if checksum is not None else "n/a"
        print(f"{label:<22} {valid!s:>6} {cs:>18}")

    ref = checksums.get("presolve=choose")
    if ref is not None:
        for label, checksum in checksums.items():
            if label == "presolve=choose" or checksum is None:
                continue
            match = np.isclose(checksum, ref, rtol=1e-9, atol=1e-6)
            print(f"  {label} finite_checksum matches choose: {match}")


def main() -> None:
    """Run the full ranging configuration profiling suite across scenarios."""
    for scenario_name in _SCENARIOS:
        network = _load_network(scenario_name, presolve="choose", simplex_strategy=4)
        _prime_calibrated(network)
        solver = network._solver  # noqa: SLF001
        n_periods = network.n_periods
        print(f"\n{'=' * 72}\n{scenario_name}: periods={n_periods} vars={solver.numVariables} rows={solver.numConstrs}")

        rows = _measure_presolve_and_strategy(scenario_name)
        _print_table(f"{scenario_name} — warm solve (median of {_REPEAT})", rows)

        _measure_warm_vs_cold(scenario_name)
        _measure_double_ranging(scenario_name)
        _measure_correctness_notes(scenario_name)

    print("\nDone.")


if __name__ == "__main__":
    main()
