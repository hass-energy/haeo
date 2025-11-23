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

    Tries to load from scenario.json (new format) first, then falls back to
    loading from separate config.json and states.json files (old format).
    """
    # Try new single-file format first
    scenario_file = scenario_path / "scenario.json"
    if scenario_file.exists():
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

    # Fall back to old format with separate files
    config_path = scenario_path / "config.json"
    states_path = scenario_path / "states.json"

    with config_path.open() as f:
        config = json.load(f)
    with states_path.open() as f:
        states = json.load(f)

    # Convert old format to new format
    return {
        "config": config,
        "environment": {"timestamp": None},  # Will be extracted from states
        "inputs": states,
        "outputs": [],
    }


@pytest.fixture
def scenario_config(scenario_data: dict[str, Any]) -> dict[str, Any]:
    """Extract config from scenario data."""
    return scenario_data["config"]


@pytest.fixture
def scenario_states(scenario_data: dict[str, Any]) -> Sequence[dict[str, Any]]:
    """Extract input states from scenario data."""
    return scenario_data["inputs"]


@pytest.fixture
def scenario_outputs(scenario_data: dict[str, Any]) -> Sequence[dict[str, Any]]:
    """Extract output states from scenario data for snapshot comparison."""
    return scenario_data.get("outputs", [])
