"""Test data for model element tests.

This module provides factory functions and utilities for creating test element instances.
"""

from collections.abc import Sequence
from typing import Any, cast

from pulp import LpVariable

from .connection_types import ConnectionTestCase
from .element_types import ElementTestCase


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
from . import battery, connection, node  # noqa: E402


def _aggregate_element_cases() -> list[ElementTestCase]:
    """Aggregate valid element test cases."""
    return [
        *battery.VALID_CASES,
        *node.VALID_CASES,
    ]


def _aggregate_connection_cases() -> list[ConnectionTestCase]:
    """Aggregate valid connection test cases."""
    return [
        *connection.VALID_CASES,
    ]


def _aggregate_invalid_element_cases() -> list[ElementTestCase]:
    """Aggregate invalid element test cases."""
    return [
        *battery.INVALID_CASES,
        *node.INVALID_CASES,
    ]


def _aggregate_invalid_connection_cases() -> list[ConnectionTestCase]:
    """Aggregate invalid connection test cases."""
    return [
        *connection.INVALID_CASES,
    ]


# Aggregate cases
VALID_ELEMENT_CASES = _aggregate_element_cases()
VALID_CONNECTION_CASES = _aggregate_connection_cases()
INVALID_ELEMENT_CASES = _aggregate_invalid_element_cases()
INVALID_CONNECTION_CASES = _aggregate_invalid_connection_cases()

__all__ = [
    "INVALID_CONNECTION_CASES",
    "INVALID_ELEMENT_CASES",
    "VALID_CONNECTION_CASES",
    "VALID_ELEMENT_CASES",
    "battery",
    "connection",
    "fix_lp_variable",
    "grid",
    "load",
    "lp_sequence",
    "node",
    "photovoltaics",
]
