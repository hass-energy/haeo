"""Fixtures for centralized scenario tests."""

import json
from pathlib import Path
from typing import Any, TypedDict, TypeGuard

import pytest


class ScenarioData(TypedDict):
    """TypedDict for scenario data structure."""

    config: dict[str, Any]
    environment: dict[str, Any]
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]


def is_scenario_data(value: Any) -> TypeGuard[ScenarioData]:
    """Type guard to validate scenario data structure."""
    if not isinstance(value, dict):
        return False

    # Check required keys
    if not all(key in value for key in ("config", "environment", "inputs", "outputs")):
        return False

    # Validate types
    if not isinstance(value["config"], dict):
        return False
    if not isinstance(value["environment"], dict):
        return False
    if not isinstance(value["inputs"], list):
        return False
    return isinstance(value["outputs"], list)


@pytest.fixture
def scenario_path(request: pytest.FixtureRequest) -> Path:
    """Get the path to the current scenario directory from parameterized test."""
    return request.param  # type: ignore[no-any-return]


@pytest.fixture
def scenario_data(scenario_path: Path) -> ScenarioData:
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

    if not is_scenario_data(data):
        msg = (
            f"Scenario file {scenario_file} must contain valid scenario data "
            "with config, environment, inputs, and outputs keys"
        )
        raise ValueError(msg)

    return data
