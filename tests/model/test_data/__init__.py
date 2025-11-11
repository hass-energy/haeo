"""Test data for model element tests.

This module provides factory functions and utilities for creating test element instances.
"""

from collections.abc import Sequence
from typing import Any, cast

from pulp import LpVariable

type TestCase = dict[str, Any]


def fix_lp_variable(variable: LpVariable, value: float) -> None:
    """Assign a fixed value to an LP variable using typed casts for mypy."""

    lp_variable = cast("Any", variable)
    lp_variable.setInitialValue(value)
    lp_variable.fixValue()


def lp_sequence(name: str, length: int) -> Sequence[LpVariable]:
    """Return a sequence of PuLP variables for tests with fixed values."""

    variables: list[LpVariable] = []
    for index in range(length):
        variable = LpVariable(f"{name}_{index}")
        fix_lp_variable(variable, float(index + 1))
        variables.append(variable)

    return tuple(variables)


# Import modules after defining utilities to avoid circular imports
from . import battery, connection, element, grid, photovoltaics  # noqa: E402


def _aggregate_cases() -> tuple[list[TestCase], list[TestCase]]:
    """Aggregate test cases from all element modules."""
    valid_cases: list[TestCase] = [
        *element.VALID_CASES,
        *battery.VALID_CASES,
        *connection.VALID_CASES,
        *grid.VALID_CASES,
        *photovoltaics.VALID_CASES,
    ]

    invalid_cases: list[TestCase] = [
        *element.INVALID_CASES,
        *battery.INVALID_CASES,
        *connection.INVALID_CASES,
        *grid.INVALID_CASES,
        *photovoltaics.INVALID_CASES,
    ]

    return valid_cases, invalid_cases


# Aggregate all valid and invalid cases from element modules
VALID_CASES, INVALID_CASES = _aggregate_cases()

__all__ = [
    "INVALID_CASES",
    "VALID_CASES",
    "battery",
    "connection",
    "element",
    "fix_lp_variable",
    "grid",
    "lp_sequence",
    "photovoltaics",
]
