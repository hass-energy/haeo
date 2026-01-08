"""Tests for reactive type helpers (UNSET sentinel and is_set function)."""

from highspy import Highs

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import UNSET, TrackedParam, is_set


def create_test_element[T: Element[str]](cls: type[T]) -> T:
    """Create a test element instance with a fresh solver."""
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    return cls(name="test", periods=(1.0,), solver=solver)


def test_unset_sentinel_returns_unset() -> None:
    """Test that accessing an unset TrackedParam returns UNSET sentinel."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    # Never set, should return UNSET
    assert elem.capacity is UNSET
    assert not is_set(elem.capacity)


def test_is_set_returns_true_after_setting() -> None:
    """Test that is_set returns True after setting a value."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)
    assert not is_set(elem.capacity)

    elem.capacity = 10.0
    assert is_set(elem.capacity)


def test_getitem_returns_unset_for_unset_param() -> None:
    """Test that __getitem__ returns UNSET for unset TrackedParams."""

    class TestElement(Element[str]):
        capacity = TrackedParam[float]()

    elem = create_test_element(TestElement)

    # Accessing via __getitem__ should also return UNSET
    assert elem["capacity"] is UNSET
    assert not is_set(elem["capacity"])

