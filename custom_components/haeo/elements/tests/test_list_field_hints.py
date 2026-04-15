"""Tests for list input field generation from ListFieldHints."""

from typing import Any

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints
from custom_components.haeo.elements.field_hints import build_list_input_fields


def test_build_list_input_fields_generates_per_item_sections() -> None:
    """Each list item with hinted fields gets its own section keyed by index."""
    hints = ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE, time_series=True)})
    items = [{"name": "solar", "price": 0.05}, {"name": "grid", "price": 0.30}]

    result = build_list_input_fields("policy", "rules", hints, items)

    assert "rules.0" in result
    assert "rules.1" in result
    assert "price" in result["rules.0"]
    assert result["rules.0"]["price"].output_type == OutputType.PRICE
    assert result["rules.0"]["price"].time_series is True


def test_build_list_input_fields_skips_items_without_hinted_fields() -> None:
    """Items that don't contain any hinted fields are omitted from output."""
    hints = ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE)})
    items = [{"name": "solar"}, {"name": "grid", "price": 0.30}]

    result = build_list_input_fields("policy", "rules", hints, items)

    assert "rules.0" not in result
    assert "rules.1" in result


def test_build_list_input_fields_empty_list() -> None:
    """Empty item list produces empty result."""
    hints = ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE)})

    result = build_list_input_fields("policy", "rules", hints, [])

    assert result == {}


def test_build_list_input_fields_skips_non_mapping_items() -> None:
    """Non-mapping items in the list are skipped."""
    hints = ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE)})
    items: Any = ["not_a_dict", {"name": "grid", "price": 0.30}]

    result = build_list_input_fields("policy", "rules", hints, items)

    assert "rules.0" not in result
    assert "rules.1" in result


def test_build_list_input_fields_status_output_type() -> None:
    """STATUS output type produces SwitchEntityDescription."""
    hints = ListFieldHints(fields={"enabled": FieldHint(output_type=OutputType.STATUS)})
    items = [{"enabled": True}]

    result = build_list_input_fields("policy", "rules", hints, items)

    assert "rules.0" in result
    info = result["rules.0"]["enabled"]
    assert info.output_type == OutputType.STATUS
    assert type(info.entity_description).__name__ == "SwitchEntityDescription"
