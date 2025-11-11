"""Fixtures for centralized scenario tests."""

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any

import pytest


# Skip all scenario tests unless -m scenario is specified
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Modify collected test items to skip scenario tests unless specified."""
    if not config.getoption("-m"):
        skip_me = pytest.mark.skip(reason="use `-m scenario` to run this test")
        for item in items:
            if "scenario" in item.keywords:
                item.add_marker(skip_me)


@pytest.fixture
def scenario_path(request: pytest.FixtureRequest) -> Path:
    """Get the path to the current scenario directory from parameterized test."""
    return request.param


@pytest.fixture
def scenario_config(scenario_path: Path) -> dict[str, Any]:
    """Load scenario configuration for the current test scenario."""
    config_path = scenario_path / "config.json"
    with config_path.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        msg = f"Scenario config {config_path} must contain an object"
        raise TypeError(msg)
    return data


@pytest.fixture
def scenario_states(scenario_path: Path) -> Sequence[dict[str, Any]]:
    """Load scenario states data for the current test scenario."""
    states_path = scenario_path / "states.json"
    with states_path.open() as f:
        data = json.load(f)
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes, bytearray)):
        msg = f"Scenario states {states_path} must contain an array"
        raise TypeError(msg)
    if not all(isinstance(item, dict) for item in data):
        msg = f"Scenario states {states_path} must contain an array of objects"
        raise TypeError(msg)
    return data
