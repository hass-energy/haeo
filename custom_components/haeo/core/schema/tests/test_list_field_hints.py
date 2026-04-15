"""Tests for ListFieldHints extraction from Annotated metadata."""

from typing import Annotated, NotRequired, Required, TypedDict

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import (
    FieldHint,
    ListFieldHints,
    SectionHints,
    extract_list_field_hints,
)


class _ItemConfig(TypedDict):
    name: str
    price: float


class _SchemaWithList(TypedDict):
    rules: Annotated[
        list[_ItemConfig],
        ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE, time_series=True)}),
    ]


class _SchemaWithRequiredList(TypedDict):
    rules: Required[
        Annotated[
            list[_ItemConfig],
            ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE)}),
        ]
    ]


class _SchemaWithNotRequiredList(TypedDict):
    rules: NotRequired[
        Annotated[
            list[_ItemConfig],
            ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE)}),
        ]
    ]


class _SchemaWithSectionsOnly(TypedDict):
    storage: Annotated[dict[str, float], SectionHints({"capacity": FieldHint(output_type=OutputType.ENERGY)})]


class _SchemaWithNoAnnotations(TypedDict):
    name: str


def test_extract_list_field_hints_plain_annotated() -> None:
    """Extracts ListFieldHints from plain Annotated fields."""
    result = extract_list_field_hints(_SchemaWithList)

    assert "rules" in result
    assert result["rules"].fields["price"].output_type == OutputType.PRICE
    assert result["rules"].fields["price"].time_series is True


def test_extract_list_field_hints_required_wrapper() -> None:
    """Extracts ListFieldHints from Required-wrapped Annotated fields."""
    result = extract_list_field_hints(_SchemaWithRequiredList)
    assert "rules" in result


def test_extract_list_field_hints_not_required_wrapper() -> None:
    """Extracts ListFieldHints from NotRequired-wrapped Annotated fields."""
    result = extract_list_field_hints(_SchemaWithNotRequiredList)
    assert "rules" in result


def test_extract_list_field_hints_ignores_section_hints() -> None:
    """SectionHints annotations are not returned by list extraction."""
    result = extract_list_field_hints(_SchemaWithSectionsOnly)
    assert result == {}


def test_extract_list_field_hints_no_annotations() -> None:
    """Schemas without Annotated fields return empty."""
    result = extract_list_field_hints(_SchemaWithNoAnnotations)
    assert result == {}
