"""Test data for model element tests.

This module provides factory functions and utilities for creating test element instances.
"""

import numpy as np
from custom_components.haeo.core.model.linear import LinearArray
from custom_components.haeo.core.model.solver import Solver

from .connection_types import ConnectionTestCase
from .element_types import ElementTestCase
from .segment_types import ConnectionScenario, SegmentErrorScenario, SegmentScenario


def fixed_variables(h: Solver, length: int) -> LinearArray:
    """Return variables fixed to 1, 2, ... and solve so they hold those values."""
    values = np.arange(1.0, length + 1.0, dtype=np.float64)
    variables = h.add_variables(length, lower=values, upper=values)
    h.run()
    return variables


def solution_value(h: Solver, expr: LinearArray) -> float:
    """Return the value of a single-row expression in the current solution."""
    (value,) = expr.value(h.column_values()).tolist()
    return value


def minimize(h: Solver, objective: LinearArray) -> None:
    """Set the objective to minimize the expression's total and solve."""
    n_columns = h.getNumCol()
    h.changeColsCost(n_columns, np.arange(n_columns, dtype=np.int32), objective.column_coefficients(n_columns))
    h.run()


# Import modules after defining utilities to avoid circular imports
from . import battery, connection, connection_segments, node, segments  # noqa: E402 (must import after utility functions are defined)


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


def _aggregate_segment_scenarios() -> list[SegmentScenario]:
    """Aggregate segment scenarios."""
    return [
        *segments.SEGMENT_SCENARIOS,
    ]


def _aggregate_segment_error_scenarios() -> list[SegmentErrorScenario]:
    """Aggregate segment error scenarios."""
    return [
        *segments.SEGMENT_ERROR_SCENARIOS,
    ]


def _aggregate_connection_segment_scenarios() -> list[ConnectionScenario]:
    """Aggregate connection scenarios focused on segments."""
    return [
        *connection_segments.CONNECTION_SCENARIOS,
    ]


# Aggregate cases
VALID_ELEMENT_CASES = _aggregate_element_cases()
VALID_CONNECTION_CASES = _aggregate_connection_cases()
INVALID_ELEMENT_CASES = _aggregate_invalid_element_cases()
INVALID_CONNECTION_CASES = _aggregate_invalid_connection_cases()
SEGMENT_SCENARIOS = _aggregate_segment_scenarios()
CONNECTION_SEGMENT_SCENARIOS = _aggregate_connection_segment_scenarios()
SEGMENT_ERROR_SCENARIOS = _aggregate_segment_error_scenarios()

__all__ = [
    "INVALID_CONNECTION_CASES",
    "INVALID_ELEMENT_CASES",
    "VALID_CONNECTION_CASES",
    "VALID_ELEMENT_CASES",
    "battery",
    "connection_segments",
    "connection",
    "CONNECTION_SEGMENT_SCENARIOS",
    "fixed_variables",
    "minimize",
    "solution_value",
    "node",
    "segments",
    "SEGMENT_SCENARIOS",
    "SEGMENT_ERROR_SCENARIOS",
]
