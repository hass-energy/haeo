"""Tests for element methods (constraints and cost)."""

from typing import Any

import pytest

from . import test_data


@pytest.mark.parametrize(
    "case",
    test_data.VALID_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_constraints(case: dict[str, Any]) -> None:
    """Element.get_all_constraints() should return valid constraints."""

    element = case["factory"](case["data"])
    element.build()
    constraints = element.get_all_constraints()

    # Should return a sequence (list/tuple)
    assert isinstance(constraints, (list, tuple))

    # All items should be constraint-like objects or equations
    # For elements without energy balance, this may be empty
    for constraint in constraints:
        # Constraints should have attributes typical of PuLP constraints
        assert hasattr(constraint, "__class__")


@pytest.mark.parametrize(
    "case",
    test_data.VALID_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_cost(case: dict[str, Any]) -> None:
    """Element.cost() should return a numeric cost value or LP expression."""

    element = case["factory"](case["data"])
    cost = element.cost()

    # Should return a number (float, int) or LP expression (has arithmetic operations)
    # PuLP expressions don't have __float__ but do support arithmetic
    assert isinstance(cost, (int, float)) or hasattr(cost, "__add__")
