"""Profile the compute cost of ranging now that it is baked into optimize().

Builds each scenario network, primes it, then times:
  - optimize() WITH ranging (current behavior: solve + populate_ranging)
  - optimize() WITHOUT ranging (populate_ranging patched out) => solve-only baseline
  - full element.outputs() extraction (slices cached ranging arrays)

The ranging cost is the difference between the two optimize timings.

Run with:
    uv run python tools/profile_ranging.py
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import time

import numpy as np

from custom_components.haeo.core.model import network as network_mod
from custom_components.haeo.core.model.network import Network
from tests.scenarios.test_benchmark import _build_network, _load_scenario, _ScenarioStateMachine

_REPEAT = 50


def _time(fn: Callable[[], object], repeat: int = _REPEAT) -> float:
    """Return median seconds over `repeat` runs."""
    samples: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return float(np.median(samples))


def _extract_all_outputs(network: Network) -> int:
    return sum(len(element.outputs()) for element in network.elements.values())


def main() -> None:
    """Profile ranging overhead and output extraction across all scenarios."""
    scenarios_dir = Path(__file__).parent.parent / "tests" / "scenarios"
    scenario_paths = sorted(
        p for p in scenarios_dir.glob("scenario*/") if (p / "config.json").exists() and (p / "inputs.json").exists()
    )

    header = (
        f"{'scenario':<20} {'periods':>8} {'vars':>7} {'rows':>7} "
        f"{'opt+rng_ms':>11} {'opt-rng_ms':>11} {'ranging_ms':>11} {'rng_%':>7} {'extract_ms':>11}"
    )
    print(header)
    print("-" * len(header))

    original_populate = network_mod.populate_ranging

    for scenario_path in scenario_paths:
        config, inputs, freeze_timestamp = _load_scenario(scenario_path)
        frozen_dt = datetime.fromisoformat(freeze_timestamp)
        sm = _ScenarioStateMachine(inputs)
        network, _ = _build_network(config, sm, frozen_dt)

        solver = network._solver  # noqa: SLF001
        network.optimize()
        n_vars = solver.numVariables
        n_rows = solver.numConstrs
        n_periods = network.n_periods

        # optimize WITH ranging (current behavior).
        network_mod.populate_ranging = original_populate
        opt_with_ms = _time(network.optimize) * 1e3

        # optimize WITHOUT ranging (solve-only baseline).
        network_mod.populate_ranging = lambda _solver: None
        opt_without_ms = _time(network.optimize) * 1e3
        network_mod.populate_ranging = original_populate

        ranging_ms = opt_with_ms - opt_without_ms
        rng_pct = (ranging_ms / opt_with_ms * 100.0) if opt_with_ms else 0.0

        # Output extraction (slices cached ranging arrays; should be cheap now).
        network.optimize()
        extract_ms = _time(lambda net=network: _extract_all_outputs(net)) * 1e3

        print(
            f"{scenario_path.name:<20} {n_periods:>8} {n_vars:>7} {n_rows:>7} "
            f"{opt_with_ms:>11.2f} {opt_without_ms:>11.2f} {ranging_ms:>11.2f} {rng_pct:>6.1f}% {extract_ms:>11.2f}"
        )

    network_mod.populate_ranging = original_populate


if __name__ == "__main__":
    main()
