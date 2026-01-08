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

    # No constraints defined yet, but _invalidated should be empty for all kinds
    assert len(elem._invalidated[CachedKind.CONSTRAINT]) == 0
    assert len(elem._invalidated[CachedKind.COST]) == 0


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
    assert "soc_constraint" in elem._deps[CachedKind.CONSTRAINT]
    assert "capacity" in elem._deps[CachedKind.CONSTRAINT]["soc_constraint"]

    # Change value
    elem.capacity = 20.0

    # Constraint should be invalidated
    assert "soc_constraint" in elem._invalidated[CachedKind.CONSTRAINT]


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

    # Set same value
    elem.capacity = 10.0

    # Should not be invalidated
    assert "soc_constraint" not in elem._invalidated[CachedKind.CONSTRAINT]


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

    # Set via __setitem__
    elem["capacity"] = 20.0

    # Constraint should be invalidated
    assert "my_constraint" in elem._invalidated[CachedKind.CONSTRAINT]


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
        def my_constraint(self) -> list[int]:
            nonlocal call_count
            call_count += 1
            return [1, 2, 3]

    elem = create_test_element(TestElement)

    # First call
    result1 = elem.my_constraint()
    assert result1 == [1, 2, 3]
    assert call_count == 1

    # Second call should use cache
    result2 = elem.my_constraint()
    assert result2 == [1, 2, 3]
    assert call_count == 1  # Not incremented


def test_cached_constraint_recomputes_when_invalidated() -> None:
    """Test that constraint recomputes when invalidated."""
    call_count = 0

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

        @constraint
        def my_constraint(self) -> list[float]:
            nonlocal call_count
            call_count += 1
            return [self.capacity * 2]

    elem = create_test_element(TestElement)
    elem.capacity = 5.0

    # First call
    result1 = elem.my_constraint()
    assert result1 == [10.0]
    assert call_count == 1

    # Change capacity (invalidates constraint)
    elem.capacity = 10.0
    assert "my_constraint" in elem._invalidated[CachedKind.CONSTRAINT]

    # Next call should recompute
    result2 = elem.my_constraint()
    assert result2 == [20.0]
    assert call_count == 2


def test_cached_constraint_tracks_multiple_dependencies() -> None:
    """Test that multiple parameter dependencies are tracked."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()
        efficiency = TrackedParam[float]()

        @constraint
        def combined_constraint(self) -> list[float]:
            return [self.capacity * self.efficiency]

    elem = create_test_element(TestElement)
    elem.capacity = 10.0
    elem.efficiency = 0.9

    elem.combined_constraint()

    deps = elem._deps[CachedKind.CONSTRAINT]["combined_constraint"]
    assert "capacity" in deps
    assert "efficiency" in deps


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
    assert "my_cost" in elem._invalidated[CachedKind.COST]

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
    """Test that Element initializes all tracking structures."""
    elem = create_test_element(Element)

    assert elem._invalidated[CachedKind.CONSTRAINT] == set()
    assert elem._invalidated[CachedKind.COST] == set()
    assert elem._cache[CachedKind.CONSTRAINT] == {}
    assert elem._cache[CachedKind.COST] == {}
    assert elem._deps[CachedKind.CONSTRAINT] == {}
    assert elem._deps[CachedKind.COST] == {}
    assert elem._applied_constraints == {}


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

    # Change 'a' - should invalidate uses_a and uses_both but not uses_b
    elem.a = 10.0

    assert "uses_a" in elem._invalidated[CachedKind.CONSTRAINT]
    assert "uses_both" in elem._invalidated[CachedKind.CONSTRAINT]
    assert "uses_b" not in elem._invalidated[CachedKind.CONSTRAINT]


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

    # Change price
    elem.price = 0.50

    assert "price_cost" in elem._invalidated[CachedKind.COST]


# Apply constraints tests


def test_apply_constraints_adds_new_constraint() -> None:
    """Test that apply_constraints adds constraints to solver on first call."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    x = solver.addVariable(lb=0.0, ub=10.0)

    class TestElement(Element[str]):
        @constraint
        def my_constraint(self) -> list[highs_linear_expression]:
            # Constraint methods return expressions, apply_constraints calls addConstrs
            return [x <= 5.0]

    elem = TestElement(name="test", periods=(1.0,), solver=solver)

    elem.apply_constraints()

    # Constraint should be tracked in _applied_constraints
    assert "my_constraint" in elem._applied_constraints


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

    # No constraint should be added
    assert "my_constraint" not in elem._applied_constraints


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
        def soc_max_constraint(self) -> list[float]:
            # Simulated constraint that depends on capacity
            self._soc_values = [self.capacity * 0.9]
            return self._soc_values

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
    assert result1 == [9.0]

    # Cached access
    result2 = battery.soc_max_constraint()
    assert result2 == [9.0]
    assert result1 is result2  # Same object, no recomputation

    # Change capacity
    battery.capacity = 20.0

    # Recomputed
    result3 = battery.soc_max_constraint()
    assert result3 == [18.0]
    assert result3 is not result1  # New object
