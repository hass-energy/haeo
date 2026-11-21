"""Benchmark tasks and the Home Assistant world they run in.

A task runs in the world of the scenario it names: that scenario's entity
states, environment, and hub config. It picks which of the scenario's
elements already exist, states a goal in the user's terms, and says what
subentry data the goal should produce.
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
    """One benchmark task, as stored in ``tasks/<id>.json``."""

    id: str
    scenario: str
    """The directory under ``tests/scenarios`` whose world the task runs in."""
    goal: str
    participants: list[str]
    expect: Expectation


def is_task(value: JsonValueType) -> TypeGuard[Task]:
    """Return whether a parsed task file has the shape of a task."""
    if not isinstance(value, dict):
        return False
    expect = value.get("expect")
    return (
        isinstance(value.get("id"), str)
        and isinstance(value.get("scenario"), str)
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


def load_tasks() -> list[Task]:
    """Load every task, sorted by id."""
    return [load_task(path.stem) for path in sorted(TASKS_DIR.glob("*.json"))]


def _scenario(task: Task) -> Path:
    return SCENARIOS_DIR / task["scenario"]


def world_environment(task: Task) -> dict[str, JsonValueType]:
    """Return the environment of the task's scenario."""
    return _object(_read_json(_scenario(task) / "environment.json"), f"{task['scenario']} environment")


def world_states(task: Task) -> list[dict[str, JsonValueType]]:
    """Return the entity states of the task's scenario."""
    path = _scenario(task) / "inputs.json"
    loaded = _read_json(path)
    if not isinstance(loaded, list):
        msg = f"{path} must hold a list of states"
        raise TypeError(msg)
    return [_object(raw, f"a state in {path}") for raw in loaded]


def hub_config(task: Task) -> dict[str, JsonValueType]:
    """Return the scenario's hub config keeping only the task's existing elements."""
    config = _object(_read_json(_scenario(task) / "config.json"), f"{task['scenario']} config")
    participants = _object(config["participants"], f"{task['scenario']} participants")
    unknown = set(task["participants"]) - set(participants)
    if unknown:
        msg = f"Task {task['id']} names elements {task['scenario']} does not have: {sorted(unknown)}"
        raise ValueError(msg)
    config["participants"] = {name: copy.deepcopy(participants[name]) for name in task["participants"]}
    return config
