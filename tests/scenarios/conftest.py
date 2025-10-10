"""Fixture for scenario tests."""

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def scenario_path(request: pytest.FixtureRequest) -> Path:
    """Get the path to the current scenario directory.

    This fixture determines the scenario directory based on the test file location.
    For tests in tests/scenarios/test_scenario1.py, it returns tests/scenarios/scenario1/
    """
    # Get the test file path from pytest request
    return Path(request.fspath.dirname)


@pytest.fixture
def scenario_config(scenario_path: Path) -> dict[str, Any]:
    """Load scenario configuration for the current test scenario."""
    config_path = scenario_path / "config.json"
    with config_path.open() as f:
        return json.load(f)


@pytest.fixture
def scenario_states(scenario_path: Path) -> Sequence[dict[str, Any]]:
    """Load scenario states data for the current test scenario."""
    states_path = scenario_path / "states.json"
    with states_path.open() as f:
        return json.load(f)
