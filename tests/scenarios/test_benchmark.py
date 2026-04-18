"""Model-layer benchmarks using real scenario data.

Measures optimization performance at the network/model layer without
Home Assistant in the loop.  Uses pytest-benchmark for statistical
tracking across runs.

Run with:
    uv run pytest tests/scenarios/test_benchmark.py -m benchmark
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

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
    """Build a Network from scenario data without Home Assistant."""
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
# Scenario discovery
# ---------------------------------------------------------------------------


def _discover_scenarios() -> list[Path]:
    scenarios_dir = Path(__file__).parent
    required_files = ("config.json", "environment.json", "inputs.json")
    return sorted(
        path for path in scenarios_dir.glob("scenario*/") if all((path / f).exists() for f in required_files)
    )


_scenarios = _discover_scenarios()


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


_MODES: list[SolveOptions] = [
    SolveOptions(mode="calibrated"),
    SolveOptions(mode="lex"),
]


@pytest.mark.benchmark
@pytest.mark.timeout(120)
@pytest.mark.parametrize(
    "scenario_path",
    _scenarios,
    ids=[s.name for s in _scenarios],
    indirect=["scenario_path"],
)
@pytest.mark.parametrize("options", _MODES, ids=[m.mode for m in _MODES])
class TestBenchmark:
    """Optimization benchmarks for each scenario and solve mode."""

    def test_cold_start(self, scenario_path: Path, options: SolveOptions, benchmark: BenchmarkFixture) -> None:
        """Build network from scratch and optimize."""
        config, inputs, freeze_timestamp = _load_scenario(scenario_path)
        frozen_dt = datetime.fromisoformat(freeze_timestamp)
        sm = _ScenarioStateMachine(inputs)

        def run() -> float:
            net = _build_network(config, sm, frozen_dt, options=options)
            return net.optimize()

        result = benchmark(run)
        assert np.isfinite(result)

    def test_update_all(self, scenario_path: Path, options: SolveOptions, benchmark: BenchmarkFixture) -> None:
        """Update all element parameters and re-optimize."""
        config, inputs, freeze_timestamp = _load_scenario(scenario_path)
        frozen_dt = datetime.fromisoformat(freeze_timestamp)
        sm = _ScenarioStateMachine(inputs)

        loaded_configs = _load_configs(config, sm, frozen_dt)
        network = _build_network(config, sm, frozen_dt, options=options)
        network.optimize()  # prime

        def run() -> float:
            for elem_config in loaded_configs.values():
                update_element(network, elem_config)
            return network.optimize()

        result = benchmark(run)
        assert np.isfinite(result)

    def test_time_shift(self, scenario_path: Path, options: SolveOptions, benchmark: BenchmarkFixture) -> None:
        """Shift forecast times forward one tick and re-optimize."""
        config, inputs, freeze_timestamp = _load_scenario(scenario_path)
        frozen_dt = datetime.fromisoformat(freeze_timestamp)
        sm = _ScenarioStateMachine(inputs)

        periods_seconds = tiers_to_periods_seconds(config, start_time=frozen_dt)
        shift_seconds = periods_seconds[0]
        shifted_configs = _load_shifted_configs(config, sm, frozen_dt, shift_seconds)

        network = _build_network(config, sm, frozen_dt, options=options)
        network.optimize()  # prime

        def run() -> float:
            for elem_config in shifted_configs.values():
                update_element(network, elem_config)
            return network.optimize()

        result = benchmark(run)
        assert np.isfinite(result)

    def test_warm_reentrant(self, scenario_path: Path, options: SolveOptions, benchmark: BenchmarkFixture) -> None:
        """Re-optimize with no parameter changes (warm start)."""
        config, inputs, freeze_timestamp = _load_scenario(scenario_path)
        frozen_dt = datetime.fromisoformat(freeze_timestamp)
        sm = _ScenarioStateMachine(inputs)

        network = _build_network(config, sm, frozen_dt, options=options)
        network.optimize()  # prime

        result = benchmark(network.optimize)
        assert np.isfinite(result)
