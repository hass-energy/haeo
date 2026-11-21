"""Score a run by comparing the hub's subentries before and after against the task.

Element flows such as battery and load write their surfaced price fields as
rules in the hub's single policy subentry. A policy change counts as part of the
element's own change when every rule it adds or removes names that element, by
its old or new title, as a source or target; any other change to a subentry the task did not ask for fails
the run.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from homeassistant.util.json import JsonValueType

from custom_components.haeo.core.schema.elements import ElementType
from tools.ux_bench.matching import mismatches
from tools.ux_bench.tasks import Task


class Subentry(TypedDict):
    """A subentry as the benchmark records it."""

    type: str
    title: str
    data: dict[str, JsonValueType]


type Subentries = dict[str, Subentry]


class Outcome(TypedDict):
    """Whether a run met its task, and why not."""

    success: bool
    problems: list[str]
    result_data: dict[str, JsonValueType] | None


def plain(value: object) -> JsonValueType:
    """Convert mapping proxies and tuples in subentry data to plain JSON values."""
    if isinstance(value, Mapping):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [plain(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _rules(subentry: Subentry | None) -> list[JsonValueType]:
    rules = subentry["data"].get("rules", []) if subentry else []
    return rules if isinstance(rules, list) else []


def _names(rule: JsonValueType, key: str) -> list[JsonValueType]:
    names = rule.get(key, []) if isinstance(rule, dict) else []
    return names if isinstance(names, list) else []


def _without_rules(subentry: Subentry) -> tuple[str, str, dict[str, JsonValueType]]:
    return (
        subentry["type"],
        subentry["title"],
        {key: value for key, value in subentry["data"].items() if key != "rules"},
    )


def _only_surfaced_rules(before: Subentry | None, after: Subentry | None, element_names: set[str]) -> bool:
    """Return whether a policy changed only by rules naming the element, by its old or new title.

    The policy's title and its data besides the rules must stay the same.
    """
    if before is not None and after is not None and _without_rules(before) != _without_rules(after):
        return False
    old, new = _rules(before), _rules(after)
    differing = [rule for rule in new if rule not in old] + [rule for rule in old if rule not in new]
    return all(element_names & set(map(str, _names(rule, "source") + _names(rule, "target"))) for rule in differing)


def evaluate(task: Task, before: Subentries, after: Subentries) -> Outcome:
    """Check the subentries a run left behind against the task's expectation."""
    expect = task["expect"]
    policy_type = str(ElementType.POLICY)
    shared = (
        set()
        if expect["element_type"] == policy_type
        else {subentry_id for subentry_id, sub in {**before, **after}.items() if sub["type"] == policy_type}
    )
    added = [subentry_id for subentry_id in after if subentry_id not in before and subentry_id not in shared]
    removed = [subentry_id for subentry_id in before if subentry_id not in after and subentry_id not in shared]
    changed = [
        subentry_id
        for subentry_id in before
        if subentry_id in after and subentry_id not in shared and before[subentry_id] != after[subentry_id]
    ]
    problems: list[str] = []
    target: str | None = None

    if expect["kind"] == "add":
        matching = [subentry_id for subentry_id in added if after[subentry_id]["type"] == expect["element_type"]]
        if len(added) != 1 or len(matching) != 1:
            found = [f"{after[subentry_id]['type']} {after[subentry_id]['title']!r}" for subentry_id in added]
            problems.append(f"Expected one new {expect['element_type']} subentry, found {found or 'none'}")
        else:
            target = matching[0]
        unintended = changed + removed
    else:
        target = next(
            (
                subentry_id
                for subentry_id, sub in before.items()
                if sub["title"] == expect.get("title") and sub["type"] == expect["element_type"]
            ),
            None,
        )
        if target is None or target not in after:
            problems.append(f"The {expect['element_type']} subentry {expect.get('title')!r} no longer exists")
            target = None
        unintended = [subentry_id for subentry_id in changed if subentry_id != target] + removed + added

    element_names = {sub["title"] for sub in (before.get(target or ""), after.get(target or "")) if sub}
    for subentry_id in shared:
        old, new = before.get(subentry_id), after.get(subentry_id)
        if old != new and not (element_names and _only_surfaced_rules(old, new, element_names)):
            unintended.append(subentry_id)

    if target is not None:
        if expect["kind"] == "add" and "title" in expect and after[target]["title"] != expect["title"]:
            problems.append(f"Expected the title {expect['title']!r}, found {after[target]['title']!r}")
        problems.extend(mismatches(expect["data"], after[target]["data"]))
    for subentry_id in unintended:
        sub = after.get(subentry_id) or before[subentry_id]
        problems.append(f"Unintended change to {sub['type']} {sub['title']!r}")

    return {
        "success": not problems,
        "problems": problems,
        "result_data": after[target]["data"] if target is not None else None,
    }
