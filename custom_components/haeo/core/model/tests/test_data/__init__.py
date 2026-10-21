"""Test data for model element tests.

This module provides factory functions and utilities for creating test element instances.
"""

import numpy as np
from custom_components.haeo.core.model.linear import LinearArray
from custom_components.haeo.core.model.solver import Solver

from .connection_types import ConnectionTestCase
from .element_types import ElementTestCase
from .segment_types import ConnectionScenario, SegmentScenario


def fixed_variables(h: Solver, length: int) -> LinearArray:
    """Return variables fixed to 1, 2, ... and solve so they hold those values."""
    values = np.arange(1.0, length + 1.0, dtype=np.float64)
    variables = h.add_variables(length, lower=values, upper=values, name="variables")
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
from . import battery, connection, connection_segments, deferrable_load, node, segments  # noqa: E402 (must import after utility functions are defined)


VALID_ELEMENT_CASES: list[ElementTestCase] = [*battery.VALID_CASES, *deferrable_load.VALID_CASES, *node.VALID_CASES]
VALID_CONNECTION_CASES: list[ConnectionTestCase] = [*connection.VALID_CASES]
SEGMENT_SCENARIOS: list[SegmentScenario] = [*segments.SEGMENT_SCENARIOS]
CONNECTION_SEGMENT_SCENARIOS: list[ConnectionScenario] = [*connection_segments.CONNECTION_SCENARIOS]

__all__ = [
    "CONNECTION_SEGMENT_SCENARIOS",
    "SEGMENT_SCENARIOS",
    "VALID_CONNECTION_CASES",
    "VALID_ELEMENT_CASES",
    "battery",
    "connection",
    "connection_segments",
    "deferrable_load",
    "fixed_variables",
    "minimize",
    "node",
    "segments",
    "solution_value",
]
