"""Tests for TrackedParam descriptor and dict-style parameter access."""

from typing import Any

from highspy import Highs
import pytest

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import TrackedParam, constraint


def create_test_element[T: Element[str]](cls: type[T]) -> T:
    """Create a test element instance with a fresh solver."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    return cls(name="test", periods=(1.0,), solver=solver)


# Basic TrackedParam tests


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
