"""Tests for reactive parameter and constraint caching infrastructure."""

from collections.abc import Sequence
from typing import Any

from highspy import Highs
from highspy.highs import highs_linear_expression
import pytest

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import (
    UNSET,
    CachedConstraint,
    CachedCost,
    CachedKind,
    TrackedParam,
    constraint,
    cost,
    is_set,
)


def create_test_element[T: Element[Any]](cls: type[T]) -> T:
    """Create a test element instance with a fresh solver."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    return cls(name="test", periods=(1.0,), solver=solver)


# TrackedParam tests


def test_tracked_param_set_and_get_value() -> None:
    """Test basic value storage and retrieval."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)
    elem.capacity = 10.0

    assert elem.capacity == 10.0


def test_tracked_param_set_initial_value_does_not_invalidate() -> None:
    """Test that initial value set does not mark anything as invalidated."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)
    elem.capacity = 10.0

    # No constraints defined yet, no reactive state should exist
    # This just verifies initial set doesn't cause issues
    assert elem.capacity == 10.0


def test_tracked_param_change_value_invalidates_dependents() -> None:
    """Test that changing a value invalidates dependent constraints."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

        @constraint
        def soc_constraint(self) -> list[Any]:
            _ = self.capacity  # Access to establish dependency
            return []

    elem = create_test_element(TestElement)
    elem.capacity = 10.0

    # Call constraint to establish dependency
    elem.soc_constraint()
    
    # Check state was created and dependency tracked
    state = getattr(elem, "_reactive_state_soc_constraint", None)
    assert state is not None
    assert "capacity" in state["deps"]

    # Change value
    elem.capacity = 20.0

    # Constraint should be invalidated
    assert state["invalidated"]


def test_tracked_param_same_value_does_not_invalidate() -> None:
    """Test that setting the same value does not invalidate."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

        @constraint
        def soc_constraint(self) -> list[Any]:
            _ = self.capacity
            return []

    elem = create_test_element(TestElement)
    elem.capacity = 10.0
    elem.soc_constraint()

    # Get the state
    state = getattr(elem, "_reactive_state_soc_constraint", None)
    assert state is not None
    assert not state["invalidated"]

    # Set same value
    elem.capacity = 10.0

    # Should not be invalidated
    assert not state["invalidated"]


def test_tracked_param_class_access_returns_descriptor() -> None:
    """Test accessing TrackedParam on class returns the descriptor."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    assert isinstance(TestElement.capacity, TrackedParam)


def test_tracked_param_unset_value_returns_unset_sentinel() -> None:
    """Test that accessing an unset TrackedParam returns UNSET sentinel."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    # Never set, should return UNSET
    assert elem.capacity is UNSET
    assert not is_set(elem.capacity)


def test_tracked_param_is_set_returns_true_after_setting() -> None:
    """Test that is_set returns True after setting a value."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)
    assert not is_set(elem.capacity)

    elem.capacity = 10.0
    assert is_set(elem.capacity)


def test_tracked_param_getitem_returns_unset_for_unset_param() -> None:
    """Test that __getitem__ returns UNSET for unset TrackedParams."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    # Accessing via __getitem__ should also return UNSET
    assert elem["capacity"] is UNSET
    assert not is_set(elem["capacity"])


# Dict-style access tests


def test_dict_access_getitem_returns_tracked_param_value() -> None:
    """Test that __getitem__ returns the current value of a TrackedParam."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)
    elem.capacity = 42.0

    assert elem["capacity"] == 42.0


def test_dict_access_setitem_sets_tracked_param_value() -> None:
    """Test that __setitem__ sets the value of a TrackedParam."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)
    elem["capacity"] = 99.0

    assert elem.capacity == 99.0


def test_dict_access_setitem_triggers_invalidation() -> None:
    """Test that __setitem__ triggers constraint invalidation like normal set."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

        @constraint
        def my_constraint(self) -> list[int]:
            _ = self.capacity
            return []

    elem = create_test_element(TestElement)
    elem["capacity"] = 10.0
    elem.my_constraint()  # Establish dependency

    # Get the state
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert not state["invalidated"]

    # Set via __setitem__
    elem["capacity"] = 20.0

    # Constraint should be invalidated
    assert state["invalidated"]


def test_dict_access_getitem_unknown_key_raises_keyerror() -> None:
    """Test that __getitem__ raises KeyError for unknown keys."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    with pytest.raises(KeyError, match="unknown_param"):
        _ = elem["unknown_param"]


def test_dict_access_setitem_unknown_key_raises_keyerror() -> None:
    """Test that __setitem__ raises KeyError for unknown keys."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    with pytest.raises(KeyError, match="unknown_param"):
        elem["unknown_param"] = 123


def test_dict_access_getitem_regular_attribute_raises_keyerror() -> None:
    """Test that __getitem__ raises KeyError for non-TrackedParam attributes."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    # 'name' is a regular attribute, not a TrackedParam
    with pytest.raises(KeyError, match="name"):
        _ = elem["name"]


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
            return None

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
            return None

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
            return None

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


# Apply constraints tests


def test_apply_constraints_adds_new_constraint() -> None:
    """Test that apply_constraints adds constraints to solver on first call."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    x = solver.addVariable(lb=0.0, ub=10.0)

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> list[highs_linear_expression]:
            # Constraint methods return expressions, decorator applies to solver
            return [x <= 5.0]

    elem = TestElement(name="test", periods=(1.0,), solver=solver)

    elem.apply_constraints()

    # Constraint should be applied (state should exist with constraint)
    state = getattr(elem, "_reactive_state_my_constraint", None)
    assert state is not None
    assert "constraint" in state


def test_apply_constraints_skips_none_result() -> None:
    """Test that apply_constraints handles None result gracefully."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> None:
            return None

    elem = TestElement(name="test", periods=(1.0,), solver=solver)

    elem.apply_constraints()

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
        def soc_max_constraint(self) -> None:
            # Simulated constraint that depends on capacity
            # Return None to skip solver application
            self._soc_values = [self.capacity * 0.9]
            return None

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
    result1 = battery.soc_max_constraint()
    assert result1 is None
    assert battery._soc_values == [9.0]

    # Cached access
    result2 = battery.soc_max_constraint()
    assert result2 is None
    assert battery._soc_values == [9.0]

    # Change capacity
    battery.capacity = 20.0

    # Recomputed
    result3 = battery.soc_max_constraint()
    assert result3 is None
    assert battery._soc_values == [18.0]
