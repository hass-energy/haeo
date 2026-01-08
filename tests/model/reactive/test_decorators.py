"""Tests for reactive decorators (constraint, cost, output) and integration tests."""

from collections.abc import Sequence

from highspy import Highs
from highspy.highs import highs_linear_expression

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import CachedConstraint, CachedCost, TrackedParam, constraint, cost


def create_test_element[T: Element[str]](cls: type[T]) -> T:
    """Create a test element instance with a fresh solver."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    return cls(name="test", periods=(1.0,), solver=solver)


# CachedConstraint tests


def test_cached_constraint_caches_result() -> None:
    """Test that constraint result is cached."""
    call_count = 0

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> None:
            # Return None to skip solver application
            nonlocal call_count
            call_count += 1

    elem = create_test_element(TestElement)

    # First call
    result1 = elem.my_constraint()
    assert result1 is None
    assert call_count == 1

    # Get the state
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert not state["invalidated"]

    # Second call should use cache
    result2 = elem.my_constraint()
    assert result2 is None
    assert call_count == 1  # Not incremented


def test_cached_constraint_recomputes_when_invalidated() -> None:
    """Test that constraint recomputes when invalidated."""
    call_count = 0

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

        @constraint
        def my_constraint(self) -> None:
            # Return None to skip solver application
            nonlocal call_count
            call_count += 1
            _ = self.capacity  # Access to establish dependency

    elem = create_test_element(TestElement)
    elem.capacity = 5.0

    # First call
    result1 = elem.my_constraint()
    assert result1 is None
    assert call_count == 1

    # Change capacity (invalidates constraint)
    elem.capacity = 10.0

    # Check state was invalidated
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert state["invalidated"]

    # Next call should recompute
    result2 = elem.my_constraint()
    assert result2 is None
    assert call_count == 2


def test_cached_constraint_tracks_multiple_dependencies() -> None:
    """Test that multiple parameter dependencies are tracked."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()
        efficiency = TrackedParam[float]()

        @constraint
        def combined_constraint(self) -> None:
            # Access both parameters to establish dependencies
            _ = self.capacity
            _ = self.efficiency

    elem = create_test_element(TestElement)
    elem.capacity = 10.0
    elem.efficiency = 0.9

    elem.combined_constraint()

    # Check state was created and dependencies tracked
    state = getattr(elem, "_reactive_state_combined_constraint", None)
    assert state is not None
    assert "capacity" in state["deps"]
    assert "efficiency" in state["deps"]


def test_cached_constraint_class_access_returns_descriptor() -> None:
    """Test accessing CachedConstraint on class returns the descriptor."""

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> list[int]:
            return []

    assert isinstance(TestElement.my_constraint, CachedConstraint)


# CachedCost tests


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
    """Test accessing CachedCost on class returns the descriptor."""

    class TestElement(Element[str]):
        @cost
        def my_cost(self) -> Sequence[highs_linear_expression]:
            return []

    assert isinstance(TestElement.my_cost, CachedCost)


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

    elem = TestElement(name="test", periods=(1.0,), solver=solver)

    elem.constraints()

    # Constraint should be applied (state should exist with constraint)
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert "constraint" in state


def test_constraints_skips_none_result() -> None:
    """Test that constraints() handles None result gracefully."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> None:
            return None

    elem = TestElement(name="test", periods=(1.0,), solver=solver)

    elem.constraints()

    # State should exist but no constraint should be added
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert "constraint" not in state


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
        def test_constraint(self) -> None:
            # Simulated constraint that depends on capacity
            # Return None to skip solver application
            self._soc_values = [self.capacity * 0.9]

    solver = Highs()
    solver.setOptionValue("output_flag", False)
    battery = Battery(
        capacity=10.0,
        initial_charge=5.0,
        name="test",
        periods=(1.0,),
        solver=solver,
    )

    # Initial constraint computation
    result1 = battery.test_constraint()
    assert result1 is None
    assert battery._soc_values == [9.0]

    # Cached access
    result2 = battery.test_constraint()
    assert result2 is None
    assert battery._soc_values == [9.0]

    # Change capacity
    battery.capacity = 20.0

    # Recomputed
    result3 = battery.test_constraint()
    assert result3 is None
    assert battery._soc_values == [18.0]

