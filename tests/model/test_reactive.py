"""Tests for reactive parameter and constraint caching infrastructure."""

from collections.abc import Sequence
from typing import Any

from highspy import Highs
from highspy.highs import highs_linear_expression

from custom_components.haeo.model.reactive import (
    CachedConstraint,
    CachedCost,
    ReactiveElement,
    TrackedParam,
    cached_constraint,
    cached_cost,
)


class TestTrackedParam:
    """Tests for TrackedParam descriptor."""

    def test_set_and_get_value(self) -> None:
        """Test basic value storage and retrieval."""

        class Element(ReactiveElement):
            capacity = TrackedParam[float]()

        elem = Element()
        elem.capacity = 10.0

        assert elem.capacity == 10.0

    def test_set_initial_value_does_not_invalidate(self) -> None:
        """Test that initial value set does not mark anything as invalidated."""

        class Element(ReactiveElement):
            capacity = TrackedParam[float]()

        elem = Element()
        elem.capacity = 10.0

        # No constraints defined yet, but _invalidated should be empty
        assert len(elem._invalidated) == 0

    def test_change_value_invalidates_dependents(self) -> None:
        """Test that changing a value invalidates dependent constraints."""

        class Element(ReactiveElement):
            capacity = TrackedParam[float]()

            @cached_constraint
            def soc_constraint(self) -> list[Any]:
                _ = self.capacity  # Access to establish dependency
                return []

        elem = Element()
        elem.capacity = 10.0

        # Call constraint to establish dependency
        elem.soc_constraint()
        assert "soc_constraint" in elem._constraint_deps
        assert "capacity" in elem._constraint_deps["soc_constraint"]

        # Change value
        elem.capacity = 20.0

        # Constraint should be invalidated
        assert "soc_constraint" in elem._invalidated

    def test_same_value_does_not_invalidate(self) -> None:
        """Test that setting the same value does not invalidate."""

        class Element(ReactiveElement):
            capacity = TrackedParam[float]()

            @cached_constraint
            def soc_constraint(self) -> list[Any]:
                _ = self.capacity
                return []

        elem = Element()
        elem.capacity = 10.0
        elem.soc_constraint()

        # Set same value
        elem.capacity = 10.0

        # Should not be invalidated
        assert "soc_constraint" not in elem._invalidated

    def test_class_access_returns_descriptor(self) -> None:
        """Test accessing TrackedParam on class returns the descriptor."""

        class Element(ReactiveElement):
            capacity = TrackedParam[float]()

        assert isinstance(Element.capacity, TrackedParam)


class TestCachedConstraint:
    """Tests for cached_constraint decorator."""

    def test_caches_result(self) -> None:
        """Test that constraint result is cached."""
        call_count = 0

        class Element(ReactiveElement):
            @cached_constraint
            def my_constraint(self) -> list[int]:
                nonlocal call_count
                call_count += 1
                return [1, 2, 3]

        elem = Element()

        # First call
        result1 = elem.my_constraint()
        assert result1 == [1, 2, 3]
        assert call_count == 1

        # Second call should use cache
        result2 = elem.my_constraint()
        assert result2 == [1, 2, 3]
        assert call_count == 1  # Not incremented

    def test_recomputes_when_invalidated(self) -> None:
        """Test that constraint recomputes when invalidated."""
        call_count = 0

        class Element(ReactiveElement):
            capacity = TrackedParam[float]()

            @cached_constraint
            def my_constraint(self) -> list[float]:
                nonlocal call_count
                call_count += 1
                return [self.capacity * 2]

        elem = Element()
        elem.capacity = 5.0

        # First call
        result1 = elem.my_constraint()
        assert result1 == [10.0]
        assert call_count == 1

        # Change capacity (invalidates constraint)
        elem.capacity = 10.0
        assert "my_constraint" in elem._invalidated

        # Next call should recompute
        result2 = elem.my_constraint()
        assert result2 == [20.0]
        assert call_count == 2

    def test_tracks_multiple_dependencies(self) -> None:
        """Test that multiple parameter dependencies are tracked."""

        class Element(ReactiveElement):
            capacity = TrackedParam[float]()
            efficiency = TrackedParam[float]()

            @cached_constraint
            def combined_constraint(self) -> list[float]:
                return [self.capacity * self.efficiency]

        elem = Element()
        elem.capacity = 10.0
        elem.efficiency = 0.9

        elem.combined_constraint()

        deps = elem._constraint_deps["combined_constraint"]
        assert "capacity" in deps
        assert "efficiency" in deps

    def test_class_access_returns_descriptor(self) -> None:
        """Test accessing CachedConstraint on class returns the descriptor."""

        class Element(ReactiveElement):
            @cached_constraint
            def my_constraint(self) -> list[int]:
                return []

        assert isinstance(Element.my_constraint, CachedConstraint)


class TestCachedCost:
    """Tests for cached_cost decorator."""

    def test_caches_result(self) -> None:
        """Test that cost result is cached."""
        call_count = 0

        class Element(ReactiveElement):
            @cached_cost
            def my_cost(self) -> Sequence[highs_linear_expression]:
                nonlocal call_count
                call_count += 1
                return []

        elem = Element()

        # First call
        elem.my_cost()
        assert call_count == 1

        # Second call should use cache
        elem.my_cost()
        assert call_count == 1  # Not incremented

    def test_recomputes_when_invalidated(self) -> None:
        """Test that cost recomputes when invalidated."""
        call_count = 0

        class Element(ReactiveElement):
            price = TrackedParam[float]()

            @cached_cost
            def my_cost(self) -> Sequence[highs_linear_expression]:
                nonlocal call_count
                call_count += 1
                _ = self.price  # Access to establish dependency
                return []

        elem = Element()
        elem.price = 0.25

        # First call
        elem.my_cost()
        assert call_count == 1

        # Change price (invalidates cost)
        elem.price = 0.50
        assert "my_cost" in elem._invalidated_costs

        # Next call should recompute
        elem.my_cost()
        assert call_count == 2

    def test_class_access_returns_descriptor(self) -> None:
        """Test accessing CachedCost on class returns the descriptor."""

        class Element(ReactiveElement):
            @cached_cost
            def my_cost(self) -> Sequence[highs_linear_expression]:
                return []

        assert isinstance(Element.my_cost, CachedCost)


class TestReactiveElement:
    """Tests for ReactiveElement base class."""

    def test_initialization(self) -> None:
        """Test that ReactiveElement initializes all tracking structures."""
        elem = ReactiveElement()

        assert elem._invalidated == set()
        assert elem._constraint_cache == {}
        assert elem._constraint_deps == {}
        assert elem._applied_constraints == {}
        assert elem._invalidated_costs == set()
        assert elem._cost_cache == {}
        assert elem._cost_deps == {}

    def test_invalidate_dependents_constraints(self) -> None:
        """Test invalidate_dependents marks correct constraints."""

        class Element(ReactiveElement):
            a = TrackedParam[float]()
            b = TrackedParam[float]()

            @cached_constraint
            def uses_a(self) -> list[int]:
                _ = self.a
                return []

            @cached_constraint
            def uses_b(self) -> list[int]:
                _ = self.b
                return []

            @cached_constraint
            def uses_both(self) -> list[int]:
                _ = self.a
                _ = self.b
                return []

        elem = Element()
        elem.a = 1.0
        elem.b = 2.0

        # Call all constraints to establish dependencies
        elem.uses_a()
        elem.uses_b()
        elem.uses_both()

        # Change 'a' - should invalidate uses_a and uses_both but not uses_b
        elem.a = 10.0

        assert "uses_a" in elem._invalidated
        assert "uses_both" in elem._invalidated
        assert "uses_b" not in elem._invalidated

    def test_invalidate_dependents_costs(self) -> None:
        """Test invalidate_dependents marks correct costs."""

        class Element(ReactiveElement):
            price = TrackedParam[float]()

            @cached_cost
            def price_cost(self) -> Sequence[highs_linear_expression]:
                _ = self.price
                return []

        elem = Element()
        elem.price = 0.25

        # Call cost to establish dependency
        elem.price_cost()

        # Change price
        elem.price = 0.50

        assert "price_cost" in elem._invalidated_costs


class TestApplyConstraints:
    """Tests for constraint application to solver."""

    def test_apply_constraints_adds_new_constraint(self) -> None:
        """Test that apply_constraints adds constraints to solver on first call."""
        solver = Highs()
        x = solver.addVariable(lb=0.0, ub=10.0)

        class Element(ReactiveElement):
            @cached_constraint
            def my_constraint(self) -> list[highs_linear_expression]:
                # Return a valid constraint expression with bounds
                return [x <= 5.0]

        elem = Element()

        elem.apply_constraints(solver)

        # Constraint should be tracked in _applied_constraints
        assert "my_constraint" in elem._applied_constraints

    def test_apply_constraints_skips_none_result(self) -> None:
        """Test that apply_constraints handles None result gracefully."""

        class Element(ReactiveElement):
            @cached_constraint
            def my_constraint(self) -> None:
                return None

        elem = Element()
        solver = Highs()

        elem.apply_constraints(solver)

        # No constraint should be added
        assert "my_constraint" not in elem._applied_constraints


class TestIntegration:
    """Integration tests combining TrackedParam and cached_constraint."""

    def test_reactive_workflow(self) -> None:
        """Test complete reactive workflow with parameter changes."""

        class Battery(ReactiveElement):
            capacity = TrackedParam[float]()
            initial_charge = TrackedParam[float]()

            def __init__(self, capacity: float, initial_charge: float) -> None:
                super().__init__()
                self.capacity = capacity
                self.initial_charge = initial_charge
                self._soc_values: list[float] = []

            @cached_constraint
            def soc_max_constraint(self) -> list[float]:
                # Simulated constraint that depends on capacity
                self._soc_values = [self.capacity * 0.9]
                return self._soc_values

        battery = Battery(capacity=10.0, initial_charge=5.0)

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
