"""Coverage for annotated optional fields in schema utilities."""

from typing import Annotated, TypedDict

from custom_components.haeo.schema import _get_annotated_fields
from custom_components.haeo.schema.fields import Constant, PositiveKW


class _DummyConfig(TypedDict, total=False):
    """Config with optional annotated field."""

    element_type: str
    optional_field: Annotated[int | None, PositiveKW(), Constant(int)]


def test_get_annotated_fields_marks_optional() -> None:
    """Optional Annotated fields should be detected and unwrapped."""

    annotated = _get_annotated_fields(_DummyConfig)

    assert "optional_field" in annotated
    validator, is_optional = annotated["optional_field"]
    assert isinstance(validator, PositiveKW)
    assert is_optional is True


class _DummyConfigUnion(TypedDict):
    """Config using Union to represent optional annotated field."""

    element_type: str
    optional_field: Annotated[int, PositiveKW(), Constant(int)] | None


def test_get_annotated_fields_marks_optional_union() -> None:
    """Optional Union fields should also be marked optional."""

    annotated = _get_annotated_fields(_DummyConfigUnion)

    validator, is_optional = annotated["optional_field"]
    assert isinstance(validator, PositiveKW)
    assert is_optional is True
