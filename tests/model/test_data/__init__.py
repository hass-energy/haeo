"""Test data for model element tests.

This module provides factory functions and utilities for creating test element instances.
"""

from highspy import Highs
from highspy.highs import highs_var

from .connection_types import ConnectionTestCase
from .element_types import ElementTestCase


def highs_sequence(h: Highs, name: str, length: int) -> tuple[list[highs_var], Highs]:
    """Return a sequence of HiGHS variables for tests with fixed values.

    Args:
        h: The HiGHS solver instance
        name: Base name for variables
        length: Number of variables to create

    Returns:
        Tuple of (list of variables, solved HiGHS instance)

    """
    variables = [h.addVariable(lb=float(i + 1), ub=float(i + 1), name=f"{name}_{i}") for i in range(length)]
    # Solve to get values
    h.run()
    return variables, h


# Import modules after defining utilities to avoid circular imports
from . import battery, connection, node, schedulable_load  # noqa: E402


def _aggregate_element_cases() -> list[ElementTestCase]:
    """Aggregate valid element test cases."""
    return [
        *battery.VALID_CASES,
        *node.VALID_CASES,
        *schedulable_load.VALID_CASES,
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
        *schedulable_load.INVALID_CASES,
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
    "highs_sequence",
    "node",
    "schedulable_load",
]
