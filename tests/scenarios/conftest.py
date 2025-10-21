"""Fixture for scenario tests."""

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any, TypeGuard, cast

import pytest


def _is_dict(value: Any) -> TypeGuard[dict[str, Any]]:
    return isinstance(value, dict)


def _is_state_sequence(value: Any) -> TypeGuard[Sequence[dict[str, Any]]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return False
    return all(isinstance(item, dict) for item in value)


@pytest.fixture
def scenario_path(request: pytest.FixtureRequest) -> Path:
    """Get the path to the current scenario directory.

    This fixture determines the scenario directory based on the test file location.
    For tests in tests/scenarios/test_scenario1.py, it returns tests/scenarios/scenario1/
    """
    node_path = getattr(request.node, "path", None)
    if node_path is None:
        msg = "Fixture request is missing node path information"
        raise RuntimeError(msg)
    return cast("Path", node_path).parent


@pytest.fixture
def scenario_config(scenario_path: Path) -> dict[str, Any]:
    """Load scenario configuration for the current test scenario."""
    config_path = scenario_path / "config.json"
    with config_path.open() as f:
        data = json.load(f)
    if not _is_dict(data):
        msg = f"Scenario config {config_path} must contain an object"
        raise TypeError(msg)
    return data


@pytest.fixture
def scenario_states(scenario_path: Path) -> Sequence[dict[str, Any]]:
    """Load scenario states data for the current test scenario."""
    states_path = scenario_path / "states.json"
    with states_path.open() as f:
        data = json.load(f)
    if not _is_state_sequence(data):
        msg = f"Scenario states {states_path} must contain an array of objects"
        raise TypeError(msg)
    return data
