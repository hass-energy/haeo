"""Fixtures for centralized scenario tests."""

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def scenario_path(request: pytest.FixtureRequest) -> Path:
    """Get the path to the current scenario directory from parameterized test."""
    return request.param  # type: ignore[no-any-return]


@pytest.fixture
def scenario_data(scenario_path: Path) -> dict[str, Any]:
    """Load scenario data from diagnostic format file.

    Loads from scenario.json which contains the complete diagnostic format
    with config, environment, inputs, and outputs sections.
    """
    scenario_file = scenario_path / "scenario.json"
    if not scenario_file.exists():
        msg = f"Scenario file not found: {scenario_file}"
        raise FileNotFoundError(msg)

    with scenario_file.open() as f:
        data = json.load(f)

    if not isinstance(data, dict):
        msg = f"Scenario file {scenario_file} must contain an object"
        raise TypeError(msg)

    # Validate required keys
    if not all(key in data for key in ("config", "inputs", "environment")):
        msg = f"Scenario file {scenario_file} must contain config, inputs, and environment keys"
        raise ValueError(msg)

    return data


@pytest.fixture
def scenario_config(scenario_data: dict[str, Any]) -> dict[str, Any]:
    """Extract config from scenario data."""
    config: dict[str, Any] = scenario_data["config"]
    return config


@pytest.fixture
def scenario_states(scenario_data: dict[str, Any]) -> Sequence[dict[str, Any]]:
    """Extract input states from scenario data."""
    states: Sequence[dict[str, Any]] = scenario_data["inputs"]
    return states


@pytest.fixture
def scenario_outputs(scenario_data: dict[str, Any]) -> Sequence[dict[str, Any]]:
    """Extract output states from scenario data for snapshot comparison."""
    outputs: Sequence[dict[str, Any]] = scenario_data.get("outputs", [])
    return outputs
