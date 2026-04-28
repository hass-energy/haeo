"""Tests for elements.field_hints: list helpers and OutputType defaults."""

from typing import Any

from homeassistant.components.number.const import DEFAULT_MAX_VALUE, DEFAULT_MIN_VALUE

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.elements.grid import GridConfigSchema
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints, extract_field_hints
from custom_components.haeo.core.schema.sections import CONF_PRICE_SOURCE_TARGET, SECTION_PRICING
from custom_components.haeo.elements.field_hints import (
    OUTPUT_TYPE_DEFAULTS,
    PRICE_NATIVE_MAX_VALUE,
    PRICE_NATIVE_MIN_VALUE,
    build_input_fields,
    build_list_input_fields,
)


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


def test_build_list_input_fields_creates_entities_for_all_items() -> None:
    """All items get entities for hinted fields, even when absent from config."""
    hints = ListFieldHints(fields={"price": FieldHint(output_type=OutputType.PRICE)})
    items = [{"name": "solar"}, {"name": "grid", "price": 0.30}]

    result = build_list_input_fields("policy", "rules", hints, items)

    assert "rules.0" in result
    assert "price" in result["rules.0"]
    assert "rules.1" in result
    assert "price" in result["rules.1"]


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


def test_build_list_input_fields_creates_entity_for_absent_fields() -> None:
    """Hinted fields absent from config items still get entities with defaults."""
    hints = ListFieldHints(
        fields={
            "enabled": FieldHint(output_type=OutputType.STATUS, default_value=True),
            "price": FieldHint(output_type=OutputType.PRICE),
        }
    )
    # Item has price but not enabled — both should get entities
    items = [{"price": {"type": "constant", "value": 0.1}}]

    result = build_list_input_fields("policy", "rules", hints, items)

    assert "rules.0" in result
    assert "enabled" in result["rules.0"]
    assert "price" in result["rules.0"]
    assert result["rules.0"]["enabled"].output_type == OutputType.STATUS


def test_price_output_type_defaults_are_explicit_negative_compatible() -> None:
    """PRICE fields must not rely on HA NumberEntityDescription None → min/max defaults.

    Home Assistant maps native_min_value/native_max_value of None to 0.0 and 100.0,
    which incorrectly forbids negative prices and caps above 100.
    """
    meta = OUTPUT_TYPE_DEFAULTS[OutputType.PRICE]
    assert meta.min_value is not None
    assert meta.max_value is not None
    assert meta.min_value == PRICE_NATIVE_MIN_VALUE
    assert meta.max_value == PRICE_NATIVE_MAX_VALUE
    assert meta.min_value < 0
    assert meta.min_value != DEFAULT_MIN_VALUE
    assert meta.max_value != DEFAULT_MAX_VALUE


def test_grid_pricing_fields_use_explicit_price_bounds() -> None:
    """Built grid pricing inputs expose explicit native min/max on the description."""
    hints = extract_field_hints(GridConfigSchema)
    fields = build_input_fields("grid", hints)
    desc = fields[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET].entity_description
    assert desc.native_min_value == PRICE_NATIVE_MIN_VALUE
    assert desc.native_max_value == PRICE_NATIVE_MAX_VALUE
