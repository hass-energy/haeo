"""Fixtures for centralized scenario tests."""

import json
from pathlib import Path
from typing import Any, TypedDict, TypeGuard

import pytest

from .syrupy_json_extension import ScenarioJSONExtension


@pytest.fixture(autouse=True, scope="session")
def migrate_unified_scenarios() -> None:
    """Migrate any unified scenario.json files to split format.

    This runs once per test session and splits scenario.json into:
    - config.json
    - environment.json
    - inputs.json
    - outputs.json

    After splitting, the original scenario.json is deleted.
    """
    scenarios_dir = Path(__file__).parent
    scenario_folders = sorted(scenarios_dir.glob("scenario*/"))

    for scenario_path in scenario_folders:
        scenario_file = scenario_path / "scenario.json"

        if scenario_file.exists():
            # Load the unified file
            with scenario_file.open() as f:
                data = json.load(f)

            # Validate structure
            required_keys = {"config", "environment", "inputs", "outputs"}
            if not all(key in data for key in required_keys):
                msg = f"Scenario file {scenario_file} missing required keys: {required_keys - data.keys()}"
                raise ValueError(msg)

            # Write split files with consistent formatting
            for key in required_keys:
                split_file = scenario_path / f"{key}.json"
                with split_file.open("w") as f:
                    json.dump(data[key], f, indent=2)
                    f.write("\n")  # POSIX trailing newline

            # Delete the unified file after successful split
            scenario_file.unlink()

            print(f"Migrated {scenario_file.name} to split format in {scenario_path.name}")  # noqa: T201


class ScenarioData(TypedDict):
    """TypedDict for scenario data structure."""

    config: dict[str, Any]
    environment: dict[str, Any]
    inputs: list[dict[str, Any]]
    outputs: dict[str, dict[str, Any]]  # Dict with entity_id keys


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
    return isinstance(value["outputs"], dict)


@pytest.fixture
def scenario_path(request: pytest.FixtureRequest) -> Path:
    """Get the path to the current scenario directory from parameterized test."""
    return request.param  # type: ignore[no-any-return]


@pytest.fixture
def scenario_data(scenario_path: Path) -> ScenarioData:
    """Load scenario data from split JSON files.

    Loads from config.json, environment.json, inputs.json, and outputs.json
    which are created by the migrate_unified_scenarios fixture.
    """
    # Load all split files
    config_file = scenario_path / "config.json"
    environment_file = scenario_path / "environment.json"
    inputs_file = scenario_path / "inputs.json"
    outputs_file = scenario_path / "outputs.json"

    # Check all required files exist
    for file in [config_file, environment_file, inputs_file, outputs_file]:
        if not file.exists():
            msg = f"Required scenario file not found: {file}"
            raise FileNotFoundError(msg)

    # Load all files
    with config_file.open() as f:
        config = json.load(f)
    with environment_file.open() as f:
        environment = json.load(f)
    with inputs_file.open() as f:
        inputs = json.load(f)
    with outputs_file.open() as f:
        outputs = json.load(f)

    # Reconstruct ScenarioData
    data: ScenarioData = {
        "config": config,
        "environment": environment,
        "inputs": inputs,
        "outputs": outputs,
    }

    if not is_scenario_data(data):
        msg = f"Loaded data from {scenario_path} is not valid ScenarioData"
        raise ValueError(msg)

    return data


@pytest.fixture
def snapshot(snapshot):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN201
    """Override the default snapshot fixture with custom ScenarioJSONExtension."""
    return snapshot.use_extension(ScenarioJSONExtension)
