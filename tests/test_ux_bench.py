"""Tests for the config flow usability benchmark's tasks, matching, and scoring."""

from __future__ import annotations

from pathlib import Path
import subprocess

from homeassistant.util.json import JsonValueType
import pytest

from custom_components.haeo.core.schema.elements import ElementType
from tools.ux_bench.matching import mismatches
from tools.ux_bench.run import RunResult, rescore, run_one, summarize
from tools.ux_bench.scoring import Subentries, Subentry, evaluate
from tools.ux_bench.tasks import TASKS_DIR, Task, hub_config, load_tasks, world_states

ALL_TASKS = load_tasks(include_holdout=True)


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ({"a": 1}, {"a": 1, "b": 2}),
        ({"a": {"b": 1.0}}, {"a": {"b": 1.0000000001}}),
        ({"v": {"$set": ["x", "y"]}}, {"v": ["y", "x"]}),
        ({"v": {"$contains": [{"k": 1}]}}, {"v": [{"k": 2}, {"k": 1, "j": 3}]}),
        ({"gone": {"$absent": True}}, {"other": 1}),
        (["a", "b"], ["a", "b"]),
        (
            {"v": {"$contains": [{"s": "B"}, {"s": "B", "p": 1}]}},
            {"v": [{"s": "B", "p": 1}, {"s": "B", "p": 2}]},
        ),
    ],
    ids=["extra-keys", "close-float", "set-any-order", "contains", "absent", "list", "contains-loose-first"],
)
def test_matching_accepts(expected: JsonValueType, actual: JsonValueType) -> None:
    """Data that holds everything the expectation names matches."""
    assert mismatches(expected, actual) == []


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ({"a": 1}, {"b": 1}),
        ({"a": 1}, {"a": 2}),
        ({"a": True}, {"a": 1}),
        ({"a": 1}, {"a": True}),
        ({"v": {"$set": ["x", "y"]}}, {"v": ["x"]}),
        ({"v": {"$set": ["x"]}}, {"v": ["x", "y"]}),
        ({"v": {"$contains": [{"k": 1}]}}, {"v": [{"k": 2}]}),
        ({"gone": {"$absent": True}}, {"gone": []}),
        (["a", "b"], ["b", "a"]),
    ],
)
def test_matching_rejects(expected: JsonValueType, actual: JsonValueType) -> None:
    """Data that differs from the expectation anywhere it names fails."""
    assert mismatches(expected, actual)


@pytest.mark.parametrize("task", ALL_TASKS, ids=lambda task: task["id"])
def test_task_is_consistent(task: Task) -> None:
    """Each task names its file, an element type, and elements scenario 6 has."""
    assert (TASKS_DIR / f"{task['id']}.json").exists()
    assert task["expect"]["element_type"] in set(ElementType)
    participants = hub_config(task)["participants"]
    assert isinstance(participants, dict)
    if task["expect"]["kind"] == "edit":
        assert task["expect"].get("title") in participants


def test_world_has_every_entity_the_tasks_expect() -> None:
    """Every entity a task expects the agent to pick exists in the world."""
    entity_ids = {str(state["entity_id"]) for state in world_states()}

    def expected_entities(value: JsonValueType) -> set[str]:
        if isinstance(value, dict):
            return set().union(*(expected_entities(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(expected_entities(item) for item in value))
        return {value} if isinstance(value, str) and value.startswith("sensor.") else set()

    for task in ALL_TASKS:
        assert expected_entities(task["expect"]["data"]) <= entity_ids, task["id"]


@pytest.mark.parametrize(
    ("task_id", "scenario_element"),
    [("add_battery", "Battery"), ("add_grid_amber", "Grid"), ("add_load_forecast", "Load")],
)
def test_expectations_match_the_users_own_config(task_id: str, scenario_element: str) -> None:
    """Tasks modeled on scenario 6's elements expect what its user configured."""
    task = next(task for task in ALL_TASKS if task["id"] == task_id)
    config = hub_config({**task, "participants": [scenario_element]})["participants"]
    assert isinstance(config, dict)
    assert mismatches(task["expect"]["data"], config[scenario_element]) == []


def _sub(element_type: str, title: str, data: dict[str, JsonValueType]) -> Subentry:
    return {"type": element_type, "title": title, "data": data}


def _rule(price: float, source: list[JsonValueType], target: list[JsonValueType] | None = None) -> JsonValueType:
    rule: dict[str, JsonValueType] = {"price": price, "source": source}
    if target is not None:
        rule["target"] = target
    return rule


ADD_TASK: Task = {
    "id": "t",
    "holdout": False,
    "goal": "",
    "participants": [],
    "expect": {"kind": "add", "element_type": "load", "title": "Pump", "data": {"forecast": 1.0}},
}
EDIT_TASK: Task = {
    "id": "t",
    "holdout": False,
    "goal": "",
    "participants": [],
    "expect": {"kind": "edit", "element_type": "battery", "title": "Battery", "data": {"min": 20}},
}
BEFORE: Subentries = {"grid": _sub("grid", "Grid", {"x": 1}), "bat": _sub("battery", "Battery", {"min": 5})}
PUMP = _sub("load", "Pump", {"forecast": 1.0})


def test_evaluate_add_passes() -> None:
    """One new subentry of the right type with the expected data passes."""
    assert evaluate(ADD_TASK, BEFORE, {**BEFORE, "new": PUMP})["success"] is True


@pytest.mark.parametrize(
    "after",
    [
        BEFORE,
        {**BEFORE, "new": _sub("load", "Pump", {"forecast": 2.0})},
        {**BEFORE, "new": _sub("load", "Other", {"forecast": 1.0})},
        {**BEFORE, "new": _sub("solar", "Pump", {"forecast": 1.0})},
        {**BEFORE, "new": PUMP, "extra": _sub("load", "Pump 2", {"forecast": 1.0})},
        {**BEFORE, "grid": _sub("grid", "Grid", {"x": 2}), "new": PUMP},
    ],
    ids=["nothing", "wrong-data", "wrong-title", "wrong-type", "two-added", "collateral-edit"],
)
def test_evaluate_add_fails(after: Subentries) -> None:
    """A missing, wrong, duplicated, or collateral change fails."""
    assert evaluate(ADD_TASK, BEFORE, after)["success"] is False


def test_evaluate_edit() -> None:
    """Editing the named subentry passes; also changing another fails."""
    edited = {**BEFORE, "bat": _sub("battery", "Battery", {"min": 20})}
    assert evaluate(EDIT_TASK, BEFORE, edited)["success"] is True
    assert evaluate(EDIT_TASK, BEFORE, {**edited, "grid": _sub("grid", "Grid", {"x": 2})})["success"] is False
    assert evaluate(EDIT_TASK, BEFORE, BEFORE)["success"] is False


@pytest.mark.parametrize(
    ("rules", "success"),
    [
        ([_rule(0.01, ["Pump"])], True),
        ([_rule(0.01, [], ["Pump"])], True),
        ([_rule(0.01, ["Grid"])], False),
    ],
    ids=["from-element", "to-element", "other-element"],
)
def test_evaluate_allows_only_the_elements_own_policy_rules(rules: list[JsonValueType], *, success: bool) -> None:
    """A policy subentry the flow creates may only hold rules naming the new element."""
    after = {**BEFORE, "new": PUMP, "policy": _sub("policy", "Policies", {"rules": rules})}
    assert evaluate(ADD_TASK, BEFORE, after)["success"] is success


def test_evaluate_edit_accepts_rules_renamed_with_the_element() -> None:
    """Renaming the element rewrites its policy rules under the new name."""
    before = {**BEFORE, "policy": _sub("policy", "Policies", {"rules": [_rule(0.01, ["Battery"])]})}
    after = {
        **before,
        "bat": _sub("battery", "Home Battery", {"min": 20}),
        "policy": _sub("policy", "Policies", {"rules": [_rule(0.01, ["Home Battery"])]}),
    }
    task: Task = {**EDIT_TASK, "expect": {"kind": "edit", "element_type": "battery", "title": "Battery", "data": {}}}
    assert evaluate(task, before, after)["success"] is True


@pytest.mark.parametrize(
    "policy",
    [
        _sub("policy", "Renamed", {"rules": [_rule(0.01, ["Pump"])]}),
        _sub("policy", "Policies", {"rules": [_rule(0.01, ["Pump"])], "note": "changed"}),
    ],
    ids=["renamed", "other-data"],
)
def test_evaluate_rejects_other_changes_to_a_policy_beside_its_rules(policy: Subentry) -> None:
    """Only rules naming the element may change on an existing policy; its title and other data may not."""
    before = {**BEFORE, "policy": _sub("policy", "Policies", {"rules": []})}
    assert evaluate(ADD_TASK, before, {**before, "new": PUMP, "policy": policy})["success"] is False


def test_run_starts_from_an_empty_directory_and_saves_a_startup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run never sees an earlier run's files, and a session that fails to start is saved for rescoring."""
    run_dir = tmp_path / ADD_TASK["id"] / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "session.json").write_text('{"port": 1}', encoding="utf-8")
    (run_dir / "result.json").write_text('{"success": true}', encoding="utf-8")

    class _ExitedSession:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def poll(self) -> int:
            return 1

    monkeypatch.setattr(subprocess, "Popen", _ExitedSession)
    result = run_one(ADD_TASK, 1, tmp_path, model="haiku", budget=1.0, timeout=1.0)

    assert result["success"] is False
    assert result.get("problems") == ["The session did not start; see session.log"]
    assert not (run_dir / "result.json").exists()
    assert [saved.get("problems") for saved in rescore(tmp_path)] == [result.get("problems")]


def test_summarize_counts_runs() -> None:
    """The summary counts passes and takes medians per task."""
    results: list[RunResult] = [
        {"task": "a", "repeat": 1, "success": True, "actions": 4, "errors_shown": 0, "seconds": 10.0, "cost_usd": 0.1},
        {"task": "a", "repeat": 2, "success": False, "actions": 8, "errors_shown": 1, "seconds": 20.0, "cost_usd": 0.2},
    ]
    summary = summarize(results)
    assert summary["passed"] == 1
    assert summary["tasks"]["a"]["actions"] == 6
    assert summary["tasks"]["a"]["actions_when_passed"] == 4
