"""Benchmark tasks and the Home Assistant world they run in.

Every task runs against the same world: scenario 6's inputs and environment,
plus scenario 4's Solcast sensors. A task picks which of scenario 6's elements
already exist, states a goal in the user's terms, and says what subentry data
the goal should produce.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, TypeGuard

from homeassistant.util.json import JsonValueType

PROJECT_ROOT = Path(__file__).parent.parent.parent
TASKS_DIR = Path(__file__).parent / "tasks"
SCENARIOS_DIR = PROJECT_ROOT / "tests" / "scenarios"
BASE_SCENARIO = SCENARIOS_DIR / "scenario6"
EXTRA_STATES: dict[str, tuple[str, ...]] = {
    "scenario4": (
        "sensor.solcast_pv_forecast_forecast_today",
        "sensor.solcast_pv_forecast_forecast_tomorrow",
        "sensor.solcast_pv_forecast_forecast_day_3",
    ),
}
HUB_TITLE = "Home"


class Expectation(TypedDict):
    """What the goal should leave behind.

    ``add`` expects exactly one new subentry of ``element_type``, titled ``title``
    when given; ``edit`` expects the existing subentry titled ``title`` to change,
    and checks a new name through ``data``. ``data`` is matched
    partially (see ``matching``), and every other subentry must stay as it was.
    """

    kind: Literal["add", "edit"]
    element_type: str
    title: NotRequired[str]
    data: dict[str, JsonValueType]


class Task(TypedDict):
    """One benchmark task, as stored in ``tasks/<id>.json``.

    ``advanced`` runs the task on a hub in advanced mode, which exposes raw
    model elements such as junctions, nodes and connections.
    """

    id: str
    holdout: bool
    goal: str
    participants: list[str]
    expect: Expectation
    advanced: NotRequired[bool]


def is_task(value: JsonValueType) -> TypeGuard[Task]:
    """Return whether a parsed task file has the shape of a task."""
    if not isinstance(value, dict):
        return False
    expect = value.get("expect")
    return (
        isinstance(value.get("id"), str)
        and isinstance(value.get("holdout"), bool)
        and isinstance(value.get("goal"), str)
        and isinstance(value.get("participants"), list)
        and isinstance(expect, dict)
        and expect.get("kind") in ("add", "edit")
        and isinstance(expect.get("element_type"), str)
        and isinstance(expect.get("data"), dict)
    )


def _read_json(path: Path) -> JsonValueType:
    value: JsonValueType = json.loads(path.read_text(encoding="utf-8"))
    return value


def _object(value: JsonValueType, context: str) -> dict[str, JsonValueType]:
    if not isinstance(value, dict):
        msg = f"{context} must be a JSON object"
        raise TypeError(msg)
    return value


def load_task(task_id: str) -> Task:
    """Load one task by id."""
    value = _read_json(TASKS_DIR / f"{task_id}.json")
    if not is_task(value):
        msg = f"tasks/{task_id}.json is not a valid task"
        raise ValueError(msg)
    return value


def load_tasks(*, include_holdout: bool) -> list[Task]:
    """Load every task, sorted by id."""
    tasks = [load_task(path.stem) for path in sorted(TASKS_DIR.glob("*.json"))]
    return [task for task in tasks if include_holdout or not task["holdout"]]


def world_environment() -> dict[str, JsonValueType]:
    """Return the environment every task runs in."""
    return _object(_read_json(BASE_SCENARIO / "environment.json"), "scenario 6 environment")


def world_states() -> list[dict[str, JsonValueType]]:
    """Return the entity states every task starts with."""
    paths: list[tuple[Path, tuple[str, ...] | None]] = [(BASE_SCENARIO / "inputs.json", None)]
    paths.extend(
        (SCENARIOS_DIR / scenario / "inputs.json", entity_ids) for scenario, entity_ids in EXTRA_STATES.items()
    )
    states: list[dict[str, JsonValueType]] = []
    for path, entity_ids in paths:
        loaded = _read_json(path)
        if not isinstance(loaded, list):
            msg = f"{path} must hold a list of states"
            raise TypeError(msg)
        for raw in loaded:
            state = _object(raw, f"a state in {path}")
            if entity_ids is None or state["entity_id"] in entity_ids:
                states.append(state)
    return states


def hub_config(task: Task) -> dict[str, JsonValueType]:
    """Return scenario 6's hub config keeping only the task's existing elements, in the task's mode."""
    config = _object(_read_json(BASE_SCENARIO / "config.json"), "scenario 6 config")
    participants = _object(config["participants"], "scenario 6 participants")
    unknown = set(task["participants"]) - set(participants)
    if unknown:
        msg = f"Task {task['id']} names elements scenario 6 does not have: {sorted(unknown)}"
        raise ValueError(msg)
    config["participants"] = {name: copy.deepcopy(participants[name]) for name in task["participants"]}
    advanced = _object(config.get("advanced", {}), "scenario 6 advanced settings")
    config["advanced"] = {**advanced, "advanced_mode": task.get("advanced", False)}
    return config
