"""Tests for reactive decorators (constraint, cost, output) and integration tests."""

from collections.abc import Sequence

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression
import numpy as np
import pytest

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.battery import Battery
from custom_components.haeo.core.model.reactive import (
    ReactiveConstraint,
    ReactiveCost,
    TrackedParam,
    applied_constraint,
    constraint,
    cost,
)


def create_test_element[T: Element[str]](cls: type[T]) -> T:
    """Create a test element instance with a fresh solver."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    return cls(name="test", periods=np.array([1.0]), solver=solver, output_names=frozenset())


# ReactiveConstraint tests


def test_cached_constraint_caches_result() -> None:
    """Test that constraint result is cached."""
    call_count = 0

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> list[highs_linear_expression]:
            nonlocal call_count
            call_count += 1
            return []

    elem = create_test_element(TestElement)

    # First call
    result1 = elem.my_constraint()
    assert result1 == []
    assert call_count == 1

    # Get the state
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert not state["invalidated"]

    # Second call should use cache
    result2 = elem.my_constraint()
    assert result2 == []
    assert call_count == 1  # Not incremented


def test_cached_constraint_recomputes_when_invalidated() -> None:
    """Test that constraint recomputes when invalidated."""
    call_count = 0

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

        @constraint
        def my_constraint(self) -> list[highs_linear_expression]:
            nonlocal call_count
            call_count += 1
            _ = self.capacity  # Access to establish dependency
            return []

    elem = create_test_element(TestElement)
    elem.capacity = 5.0

    # First call
    result1 = elem.my_constraint()
    assert result1 == []
    assert call_count == 1

    # Change capacity (invalidates constraint)
    elem.capacity = 10.0

    # Check state was invalidated
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert state["invalidated"]

    # Next call should recompute
    result2 = elem.my_constraint()
    assert result2 == []
    assert call_count == 2


def test_cached_constraint_tracks_multiple_dependencies() -> None:
    """Test that multiple parameter dependencies are tracked."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()
        efficiency = TrackedParam[float]()

        @constraint
        def combined_constraint(self) -> list[highs_linear_expression]:
            # Access both parameters to establish dependencies
            _ = self.capacity
            _ = self.efficiency
            return []

    elem = create_test_element(TestElement)
    elem.capacity = 10.0
    elem.efficiency = 0.9

    elem.combined_constraint()

    # Check state was created and dependencies tracked
    state = getattr(elem, "_reactive_state_combined_constraint", None)
    assert state is not None
    assert (elem, "capacity") in state["deps"]
    assert (elem, "efficiency") in state["deps"]


def test_cached_constraint_class_access_returns_descriptor() -> None:
    """Test accessing ReactiveConstraint on class returns the descriptor."""

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> list[int]:
            return []

    assert isinstance(TestElement.my_constraint, ReactiveConstraint)


# ReactiveCost tests


def test_cached_cost_caches_result() -> None:
    """Test that cost result is cached."""
    call_count = 0

    class TestElement(Element[str]):
        @cost
        def my_cost(self) -> Sequence[highs_linear_expression]:
            nonlocal call_count
            call_count += 1
            return []

    elem = create_test_element(TestElement)

    # First call
    elem.my_cost()
    assert call_count == 1

    # Second call should use cache
    elem.my_cost()
    assert call_count == 1  # Not incremented


def test_cached_cost_recomputes_when_invalidated() -> None:
    """Test that cost recomputes when invalidated."""
    call_count = 0

    class TestElement(Element[str]):
        price = TrackedParam[float]()

        @cost
        def my_cost(self) -> Sequence[highs_linear_expression]:
            nonlocal call_count
            call_count += 1
            _ = self.price  # Access to establish dependency
            return []

    elem = create_test_element(TestElement)
    elem.price = 0.25

    # First call
    elem.my_cost()
    assert call_count == 1

    # Change price (invalidates cost)
    elem.price = 0.50

    # Check state was invalidated
    state = getattr(elem, "_reactive_state_my_cost", None)
    assert state is not None
    assert state["invalidated"]

    # Next call should recompute
    elem.my_cost()
    assert call_count == 2


def test_cached_cost_class_access_returns_descriptor() -> None:
    """Test accessing ReactiveCost on class returns the descriptor."""

    class TestElement(Element[str]):
        @cost
        def my_cost(self) -> Sequence[highs_linear_expression]:
            return []

    assert isinstance(TestElement.my_cost, ReactiveCost)


# Element reactive infrastructure tests


def test_element_reactive_initialization() -> None:
    """Test that Element initializes properly."""
    elem = create_test_element(Element)

    # Element should initialize without errors
    # No reactive state exists until decorators are called
    assert elem.name == "test"
    assert len(elem.periods) == 1


def test_element_reactive_invalidate_dependents_constraints() -> None:
    """Test invalidate_dependents marks correct constraints."""

    class TestElement(Element[str]):
        a = TrackedParam[float]()
        b = TrackedParam[float]()

        @constraint
        def uses_a(self) -> list[int]:
            _ = self.a
            return []

        @constraint
        def uses_b(self) -> list[int]:
            _ = self.b
            return []

        @constraint
        def uses_both(self) -> list[int]:
            _ = self.a
            _ = self.b
            return []

    elem = create_test_element(TestElement)
    elem.a = 1.0
    elem.b = 2.0

    # Call all constraints to establish dependencies
    elem.uses_a()
    elem.uses_b()
    elem.uses_both()

    # Get states
    state_a = getattr(elem, "_reactive_state_uses_a", None)
    state_b = getattr(elem, "_reactive_state_uses_b", None)
    state_both = getattr(elem, "_reactive_state_uses_both", None)
    assert state_a is not None
    assert state_b is not None
    assert state_both is not None

    # Change 'a' - should invalidate uses_a and uses_both but not uses_b
    elem.a = 10.0

    assert state_a["invalidated"]
    assert state_both["invalidated"]
    assert not state_b["invalidated"]


def test_invalidation_reaches_methods_on_other_objects() -> None:
    """A method reading another object's parameter, directly or through its methods, is invalidated with it."""

    class Upstream(Element[str]):
        a = TrackedParam[float]()
        b = TrackedParam[float]()

        @cost
        def scaled(self) -> float:
            return self.b * 2

    class Downstream(Element[str]):
        def __init__(self, upstream: Upstream) -> None:
            super().__init__(name="downstream", periods=np.array([1.0]), solver=Highs(), output_names=frozenset())
            self.upstream = upstream

        @cost
        def reads_param(self) -> float:
            return self.upstream.a

        @cost
        def reads_method(self) -> float:
            return self.upstream.scaled()

    upstream = create_test_element(Upstream)
    upstream.a = 1.0
    upstream.b = 1.0
    downstream = Downstream(upstream)
    assert downstream.reads_param() == 1.0
    assert downstream.reads_method() == 2.0

    upstream.a = 3.0
    upstream.b = 5.0

    assert downstream.reads_param() == 3.0
    assert downstream.reads_method() == 10.0


def test_element_reactive_invalidate_dependents_costs() -> None:
    """Test invalidate_dependents marks correct costs."""

    class TestElement(Element[str]):
        price = TrackedParam[float]()

        @cost
        def price_cost(self) -> Sequence[highs_linear_expression]:
            _ = self.price
            return []

    elem = create_test_element(TestElement)
    elem.price = 0.25

    # Call cost to establish dependency
    elem.price_cost()

    # Get state
    state = getattr(elem, "_reactive_state_price_cost", None)
    assert state is not None
    assert not state["invalidated"]

    # Change price
    elem.price = 0.50

    assert state["invalidated"]


# Constraint collection tests


def test_constraints_adds_new_constraint() -> None:
    """Test that constraints() adds constraints to solver on first call."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    x = solver.addVariable(lb=0.0, ub=10.0)

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> list[highs_linear_expression]:
            # Constraint methods return expressions, decorator applies to solver
            return [x <= 5.0]

    elem = TestElement(name="test", periods=np.array([1.0]), solver=solver, output_names=frozenset())

    elem.constraints()

    # Constraint should be applied (state should exist with constraint)
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert "constraint" in state


def test_constraint_returning_none_raises() -> None:
    """A constraint must return rows, so returning None is a clear error."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> None:
            return None

    elem = TestElement(name="test", periods=np.array([1.0]), solver=solver, output_names=frozenset())

    with pytest.raises(TypeError, match="my_constraint returned None"):
        elem.my_constraint()


def test_constraint_free_row_stays_in_lp_and_binds_later() -> None:
    """A constraint that does not apply keeps a free row, which binds again without adding rows.

    A free row is not listed by constraints() and has no shadow price.
    """
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    x = solver.addVariable(lb=0.0, ub=10.0)

    class TestElement(Element[str]):
        limit = TrackedParam[float | None]()

        @constraint(output=True)
        def my_constraint(self) -> highs_linear_expression:
            row = 1.0 * x
            return row if self.limit is None else row <= self.limit

    elem = TestElement(name="test", periods=np.array([1.0]), solver=solver, output_names=frozenset())
    solver.changeColsCost(1, np.array([0], dtype=np.int32), np.array([-1.0]))

    def maximized_x() -> float:
        elem.constraints()
        solver.run()
        return solver.getSolution().col_value[0]

    elem.limit = None
    assert maximized_x() == 10.0
    assert solver.numConstrs == 1
    assert "my_constraint" not in elem.constraints()
    assert applied_constraint(elem, "my_constraint") is None

    elem.limit = 5.0
    assert maximized_x() == 5.0
    assert "my_constraint" in elem.constraints()

    elem.limit = None
    assert maximized_x() == 10.0
    assert solver.numConstrs == 1
    assert "my_constraint" not in elem.constraints()


def test_constraint_row_count_change_raises_clear_error() -> None:
    """A list constraint must keep its row count so the LP keeps its shape."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    x = solver.addVariables(2, lb=0.0, ub=10.0)

    class TestElement(Element[str]):
        rows = TrackedParam[int]()

        @constraint
        def my_constraint(self) -> list[highs_linear_expression]:
            return [x[i] <= 1.0 for i in range(self.rows)]

    elem = TestElement(name="test", periods=np.array([1.0]), solver=solver, output_names=frozenset())
    elem.rows = 2
    elem.my_constraint()

    elem.rows = 1
    with pytest.raises(ValueError, match="returned 1 rows after 2"):
        elem.my_constraint()


def test_constraint_shape_change_raises_clear_error() -> None:
    """A constraint cannot switch between a single row and a list of rows."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    x = solver.addVariable(lb=0.0, ub=10.0)

    class TestElement(Element[str]):
        as_list = TrackedParam[bool]()

        @constraint
        def my_constraint(self) -> highs_linear_expression | list[highs_linear_expression]:
            row = x <= 1.0
            return [row] if self.as_list else row

    elem = TestElement(name="test", periods=np.array([1.0]), solver=solver, output_names=frozenset())
    elem.as_list = False
    elem.my_constraint()

    elem.as_list = True
    with pytest.raises(ValueError, match="switched between a single row and a list of rows"):
        elem.my_constraint()


def test_failed_row_write_is_retried() -> None:
    """A constraint whose rows fail to reach the solver is computed and written again on the next call."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    x = solver.addVariable(lb=0.0, ub=10.0)
    fail = [True]

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> highs_linear_expression:
            return x <= 5.0

    elem = TestElement(name="test", periods=np.array([1.0]), solver=solver, output_names=frozenset())
    add_constr = solver.addConstr

    def flaky_add(expr: highs_linear_expression) -> highs_cons:
        if fail[0]:
            msg = "solver refused the row"
            raise RuntimeError(msg)
        return add_constr(expr)

    solver.addConstr = flaky_add  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="refused"):
        elem.my_constraint()
    assert solver.numConstrs == 0

    fail[0] = False
    elem.my_constraint()
    assert solver.numConstrs == 1


# Integration tests


def test_reactive_workflow() -> None:
    """Test complete reactive workflow with parameter changes."""

    class Battery(Element[str]):
        capacity = TrackedParam[float]()
        initial_charge = TrackedParam[float]()

        def __init__(
            self,
            capacity: float,
            initial_charge: float,
            **kwargs: object,
        ) -> None:
            super().__init__(**kwargs)  # type: ignore[arg-type]
            self.capacity = capacity
            self.initial_charge = initial_charge
            self._soc_values: list[float] = []

        @constraint
        def test_constraint(self) -> list[highs_linear_expression]:
            # Simulated constraint that depends on capacity
            self._soc_values = [self.capacity * 0.9]
            return []

    solver = Highs()
    solver.setOptionValue("output_flag", False)
    battery = Battery(
        capacity=10.0,
        initial_charge=5.0,
        name="test",
        periods=np.array([1.0]),
        solver=solver,
        output_names=frozenset(),
    )

    # Initial constraint computation
    result1 = battery.test_constraint()
    assert result1 == []
    assert battery._soc_values == [9.0]

    # Cached access
    result2 = battery.test_constraint()
    assert result2 == []
    assert battery._soc_values == [9.0]

    # Change capacity
    battery.capacity = 20.0

    # Recomputed
    result3 = battery.test_constraint()
    assert result3 == []
    assert battery._soc_values == [18.0]


def test_constraint_without_output_flag() -> None:
    """Test that constraints without output=True don't return OutputData from get_output()."""
    h = Highs()
    h.setOptionValue("output_flag", False)

    # Use 2 periods since battery constraints use slices [1:]
    battery = Battery(
        name="test",
        periods=np.array([1.0, 1.0]),
        solver=h,
        capacity=np.array([10.0, 10.0, 10.0]),
        initial_charge=5.0,
    )

    # Trigger constraint creation
    battery.constraints()

    # Get outputs - should not include constraints without output=True
    outputs = battery.outputs()

    # Battery has @constraint decorators without output=False (energy_balance)
    # These should not appear in outputs because output=False
    assert "energy_balance" not in outputs

    # But should include constraints with output=True
    assert "battery_soc_max" in outputs
    assert "battery_soc_min" in outputs
