"""Model-layer benchmarks using real scenario data.

Measures optimization performance at the network/model layer without
Home Assistant in the loop.  Uses pytest-benchmark for statistical
tracking across runs.

Run with:
    uv run pytest tests/scenarios/test_benchmark.py -m benchmark
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, tzinfo
import itertools
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from homeassistant.util.json import JsonValueType
import numpy as np
from numpy.typing import NDArray
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from custom_components.haeo.core.adapters.network_builder import ElementUpdater, build_network, periods_in_hours
from custom_components.haeo.core.data.forecast_times import generate_forecast_timestamps, preset_periods_seconds
from custom_components.haeo.core.data.loader.config_loader import load_element_configs
from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.core.state import EntityState
from custom_components.haeo.elements import is_element_config_schema
from tools.diag.cli import config_horizon_preset, migrate_batteries_for_diag

# ---------------------------------------------------------------------------
# Lightweight StateMachine backed by scenario inputs.json
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _EntityState:
    """Minimal EntityState for the core data-loading pipeline."""

    entity_id: str
    state: str
    attributes: Mapping[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "state": self.state,
            "attributes": dict(self.attributes),
        }


class _ScenarioStateMachine:
    """StateMachine backed by a list of state dicts from inputs.json."""

    def __init__(self, inputs: list[dict[str, JsonValueType]], time_zone: tzinfo) -> None:
        self.time_zone = time_zone
        self._states: dict[str, _EntityState] = {}
        for entry in inputs:
            entity_id = entry["entity_id"]
            state = entry["state"]
            if not isinstance(entity_id, str) or not isinstance(state, str):
                msg = f"Scenario input entry has non-string entity_id/state: {entry!r}"
                raise TypeError(msg)
            attributes = entry.get("attributes", {})
            self._states[entity_id] = _EntityState(
                entity_id=entity_id,
                state=state,
                attributes=attributes if isinstance(attributes, dict) else {},
            )

    def get(self, entity_id: str) -> EntityState | None:
        return self._states.get(entity_id)


# ---------------------------------------------------------------------------
# Network construction from scenario data
# ---------------------------------------------------------------------------


def _load_scenario(
    scenario_path: Path,
) -> tuple[dict[str, JsonValueType], list[dict[str, JsonValueType]], str, ZoneInfo]:
    """Load scenario files from disk."""
    with (scenario_path / "config.json").open() as f:
        config = json.load(f)
    with (scenario_path / "environment.json").open() as f:
        environment = json.load(f)
    with (scenario_path / "inputs.json").open() as f:
        inputs = json.load(f)
    return config, inputs, environment["optimization_start_time"], ZoneInfo(environment["timezone"])


def _participants_from_config(config: Mapping[str, JsonValueType]) -> dict[str, ElementConfigSchema]:
    """Migrate a scenario config's batteries as v1.4 does and narrow its participants to ElementConfigSchema entries."""
    participants_raw = config["participants"]
    if not isinstance(participants_raw, dict):
        msg = "Scenario config participants must be an object"
        raise TypeError(msg)
    raw_configs: dict[str, dict[str, object]] = {}
    for name, participant_config in participants_raw.items():
        if not isinstance(participant_config, dict):
            msg = f"Scenario participant {name!r} must be an object"
            raise TypeError(msg)
        raw_configs[name] = dict(participant_config)
    participants: dict[str, ElementConfigSchema] = {}
    for name, participant_config in migrate_batteries_for_diag(raw_configs).items():
        if not is_element_config_schema(participant_config):
            msg = f"Scenario participant {name!r} is not a valid element config"
            raise TypeError(msg)
        participants[name] = participant_config
    return participants


def _build_network(
    config: dict[str, JsonValueType],
    sm: _ScenarioStateMachine,
    frozen_dt: datetime,
) -> tuple[Network, dict[str, ElementUpdater]]:
    """Build a Network from scenario data without Home Assistant."""
    participants = _participants_from_config(config)
    periods_seconds = preset_periods_seconds(config_horizon_preset(config), start_time=frozen_dt)
    forecast_times = generate_forecast_timestamps(periods_seconds, start_time=frozen_dt.timestamp())
    loaded_configs = load_element_configs(participants, sm, forecast_times)
    return build_network("benchmark", loaded_configs, periods_seconds)


def _load_configs(
    config: dict[str, JsonValueType],
    sm: _ScenarioStateMachine,
    frozen_dt: datetime,
) -> dict[str, ElementConfigData]:
    """Load element configs resolved against scenario state machine."""
    periods_seconds = preset_periods_seconds(config_horizon_preset(config), start_time=frozen_dt)
    forecast_times = generate_forecast_timestamps(periods_seconds, start_time=frozen_dt.timestamp())
    return load_element_configs(_participants_from_config(config), sm, forecast_times)


def _load_shifted_horizon(
    config: dict[str, JsonValueType],
    sm: _ScenarioStateMachine,
    frozen_dt: datetime,
    shift_seconds: int,
) -> tuple[NDArray[np.float64], dict[str, ElementConfigData]]:
    """Return the period widths (hours) and element configs for a horizon shifted forward."""
    shifted_epoch = frozen_dt.timestamp() + shift_seconds
    shifted_dt = datetime.fromtimestamp(shifted_epoch, tz=UTC)
    shifted_periods = preset_periods_seconds(config_horizon_preset(config), start_time=shifted_dt)
    shifted_forecast_times = generate_forecast_timestamps(shifted_periods, start_time=shifted_epoch)
    configs = load_element_configs(_participants_from_config(config), sm, shifted_forecast_times)
    return periods_in_hours(shifted_periods), configs


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------


def _discover_scenarios() -> list[Path]:
    scenarios_dir = Path(__file__).parent
    required_files = ("config.json", "environment.json", "inputs.json")
    return sorted(path for path in scenarios_dir.glob("scenario*/") if all((path / f).exists() for f in required_files))


_scenarios = _discover_scenarios()


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


_benchmark_params = [
    pytest.mark.benchmark,
    pytest.mark.timeout(120),
    pytest.mark.parametrize(
        "scenario_path",
        _scenarios,
        ids=[s.name for s in _scenarios],
        indirect=["scenario_path"],
    ),
]


def _apply_marks[F: Callable[..., None]](fn: F) -> F:
    for mark in reversed(_benchmark_params):
        fn = mark(fn)
    return fn


@_apply_marks
def test_cold_start(scenario_path: Path, benchmark: BenchmarkFixture) -> None:
    """Build network from scratch and optimize."""
    config, inputs, freeze_timestamp, time_zone = _load_scenario(scenario_path)
    frozen_dt = datetime.fromisoformat(freeze_timestamp)
    sm = _ScenarioStateMachine(inputs, time_zone)

    def run() -> float:
        net, _ = _build_network(config, sm, frozen_dt)
        return net.optimize()

    result = benchmark(run)
    assert np.isfinite(result)


@_apply_marks
def test_update_all(scenario_path: Path, benchmark: BenchmarkFixture) -> None:
    """Update all element parameters and re-optimize."""
    config, inputs, freeze_timestamp, time_zone = _load_scenario(scenario_path)
    frozen_dt = datetime.fromisoformat(freeze_timestamp)
    sm = _ScenarioStateMachine(inputs, time_zone)

    loaded_configs = _load_configs(config, sm, frozen_dt)
    network, updaters = _build_network(config, sm, frozen_dt)
    network.optimize()  # prime

    def run() -> float:
        for elem_name, elem_config in loaded_configs.items():
            updater = updaters.get(elem_name)
            if updater is not None:
                updater(elem_config)
        return network.optimize()

    result = benchmark(run)
    assert np.isfinite(result)


@_apply_marks
def test_time_shift(scenario_path: Path, benchmark: BenchmarkFixture) -> None:
    """Roll the horizon forward one tick and re-optimize, as each optimization cycle does.

    Rounds alternate between the original and the shifted horizon, so every round
    changes the period widths and forecasts rather than re-solving unchanged inputs.
    """
    config, inputs, freeze_timestamp, time_zone = _load_scenario(scenario_path)
    frozen_dt = datetime.fromisoformat(freeze_timestamp)
    sm = _ScenarioStateMachine(inputs, time_zone)

    periods_seconds = preset_periods_seconds(config_horizon_preset(config), start_time=frozen_dt)
    horizons = [
        _load_shifted_horizon(config, sm, frozen_dt, 0),
        _load_shifted_horizon(config, sm, frozen_dt, periods_seconds[0]),
    ]

    network, updaters = _build_network(config, sm, frozen_dt)
    network.optimize()  # prime
    rounds = itertools.count(1)

    def run() -> float:
        periods_hours, configs = horizons[next(rounds) % 2]
        network.update_periods(periods_hours)
        for elem_name, elem_config in configs.items():
            updater = updaters.get(elem_name)
            if updater is not None:
                updater(elem_config)
        return network.optimize()

    result = benchmark(run)
    assert np.isfinite(result)


@_apply_marks
def test_warm_reentrant(scenario_path: Path, benchmark: BenchmarkFixture) -> None:
    """Re-optimize with no parameter changes (warm start)."""
    config, inputs, freeze_timestamp, time_zone = _load_scenario(scenario_path)
    frozen_dt = datetime.fromisoformat(freeze_timestamp)
    sm = _ScenarioStateMachine(inputs, time_zone)

    network, _ = _build_network(config, sm, frozen_dt)
    network.optimize()  # prime

    result = benchmark(network.optimize)
    assert np.isfinite(result)
