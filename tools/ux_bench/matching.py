"""Partial matching of subentry data against a task's expectation.

Expected objects list only the keys a task cares about; other keys in the actual
data are ignored. Three operators cover what plain values cannot:

- ``{"$set": [...]}`` matches a list holding the same items in any order.
- ``{"$contains": [...]}`` matches a list where each expected item matches a
  distinct actual item.
- ``{"$absent": true}`` as a key's value matches when the key is missing.
"""

from __future__ import annotations

import math

from homeassistant.util.json import JsonValueType

_TOLERANCE = 1e-6
_ABSENT: JsonValueType = {"$absent": True}


def mismatches(expected: JsonValueType, actual: JsonValueType, path: str = "$") -> list[str]:
    """Return a description of every place ``actual`` differs from ``expected``."""
    if isinstance(expected, dict):
        if "$set" in expected:
            return _set_mismatches(expected["$set"], actual, path)
        if "$contains" in expected:
            return _contains_mismatches(expected["$contains"], actual, path)
        if not isinstance(actual, dict):
            return [f"{path}: expected an object, found {actual!r}"]
        found: list[str] = []
        for key, value in expected.items():
            if value == _ABSENT:
                if key in actual:
                    found.append(f"{path}.{key}: expected no value, found {actual[key]!r}")
            elif key not in actual:
                found.append(f"{path}.{key}: missing")
            else:
                found.extend(mismatches(value, actual[key], f"{path}.{key}"))
        return found
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [f"{path}: expected {expected!r}, found {actual!r}"]
        found = []
        for index, (want, have) in enumerate(zip(expected, actual, strict=True)):
            found.extend(mismatches(want, have, f"{path}[{index}]"))
        return found
    if isinstance(expected, int | float) and not isinstance(expected, bool):
        if (
            isinstance(actual, int | float)
            and not isinstance(actual, bool)
            and math.isclose(expected, actual, abs_tol=_TOLERANCE)
        ):
            return []
        return [f"{path}: expected {expected!r}, found {actual!r}"]
    if actual == expected and type(actual) is type(expected):
        return []
    return [f"{path}: expected {expected!r}, found {actual!r}"]


def _matching_index(want: JsonValueType, candidates: list[JsonValueType]) -> int | None:
    return next((index for index, have in enumerate(candidates) if not mismatches(want, have)), None)


def _set_mismatches(expected: JsonValueType, actual: JsonValueType, path: str) -> list[str]:
    problem = [f"{path}: expected the items {expected!r} in any order, found {actual!r}"]
    if not isinstance(expected, list) or not isinstance(actual, list) or len(expected) != len(actual):
        return problem
    remaining = list(actual)
    for want in expected:
        index = _matching_index(want, remaining)
        if index is None:
            return problem
        remaining.pop(index)
    return []


def _contains_mismatches(expected: JsonValueType, actual: JsonValueType, path: str) -> list[str]:
    if not isinstance(expected, list) or not isinstance(actual, list):
        return [f"{path}: expected a list containing {expected!r}, found {actual!r}"]
    remaining = list(actual)
    found: list[str] = []
    for want in expected:
        index = _matching_index(want, remaining)
        if index is None:
            found.append(f"{path}: no item matches {want!r} in {actual!r}")
        else:
            remaining.pop(index)
    return found
