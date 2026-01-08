"""Tests for TrackedParam behavior with unset values."""

from highspy import Highs
import numpy as np
import pytest

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import TrackedParam
from custom_components.haeo.model.reactive.tracked_param import _values_equal


def create_test_element[T: Element[str]](cls: type[T]) -> T:
    """Create a test element instance with a fresh solver."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    return cls(name="test", periods=(1.0,), solver=solver, output_names=frozenset())


def test_unset_raises_attribute_error() -> None:
    """Test that accessing an unset TrackedParam raises AttributeError."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    # Never set, should raise AttributeError
    with pytest.raises(AttributeError):
        _ = elem.capacity

    # is_set should return False
    assert not TestElement.capacity.is_set(elem)


def test_is_set_returns_true_after_setting() -> None:
    """Test that is_set returns True after setting a value."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)
    assert not TestElement.capacity.is_set(elem)

    elem.capacity = 10.0
    assert TestElement.capacity.is_set(elem)
    assert elem.capacity == 10.0


def test_getitem_raises_for_unset_param() -> None:
    """Test that __getitem__ raises AttributeError for unset TrackedParams."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    # Accessing via __getitem__ should also raise AttributeError
    with pytest.raises(AttributeError):
        _ = elem["capacity"]
    assert not TestElement.capacity.is_set(elem)


def test_values_equal_handles_comparison_errors() -> None:
    """Test _values_equal handles TypeError and ValueError in comparisons."""
    # Test numpy array comparison that raises TypeError
    # (e.g., arrays with incompatible shapes for certain operations)
    class BadArray:
        """Mock array that raises TypeError on comparison."""

        def __eq__(self, other: object) -> bool:
            msg = "Incompatible types"
            raise TypeError(msg)

        def __hash__(self) -> int:
            return id(self)

    assert not _values_equal(BadArray(), BadArray())

    # Test standard equality that raises ValueError
    class BadValue:
        """Mock value that raises ValueError on comparison."""

        def __eq__(self, other: object) -> bool:
            msg = "Invalid comparison"
            raise ValueError(msg)

        def __hash__(self) -> int:
            return id(self)

    assert not _values_equal(BadValue(), BadValue())

    # Test numpy array comparison that raises ValueError
    # Arrays with object dtype that can't be compared
    a = np.array([BadValue()], dtype=object)
    b = np.array([BadValue()], dtype=object)
    assert not _values_equal(a, b)
