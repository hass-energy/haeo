"""Tests for ListFieldHints extraction from Annotated metadata."""

from typing import Annotated, NotRequired, Required, TypedDict

import pytest

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


_PRICE = FieldHint(output_type=OutputType.PRICE)
_LIMIT = FieldHint(output_type=OutputType.POWER_LIMIT)


@pytest.mark.parametrize(
    ("hints", "item", "fields"),
    [
        pytest.param(
            ListFieldHints(fields={"price": _PRICE, "max_power": _LIMIT}), {}, ["price", "max_power"], id="alike"
        ),
        pytest.param(
            ListFieldHints(
                fields={"price": _PRICE, "max_power": _LIMIT},
                kind_key="segment_type",
                kind_fields={"pricing": ("price",), "power_limit": ("max_power",)},
            ),
            {"segment_type": "power_limit", "price": 1.0},
            ["max_power"],
            id="of_its_kind",
        ),
        pytest.param(
            ListFieldHints(fields={"price": _PRICE}, kind_key="segment_type", kind_fields={"pricing": ("price",)}),
            {"segment_type": "unknown"},
            [],
            id="unknown_kind",
        ),
    ],
)
def test_item_fields_are_every_field_or_those_of_the_item_s_kind(
    hints: ListFieldHints, item: dict[str, object], fields: list[str]
) -> None:
    """Items of a list without kinds have every field, and items of a list with kinds have their kind's fields."""
    assert list(hints.item_fields(item)) == fields
