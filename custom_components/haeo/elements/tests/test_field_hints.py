"""Tests for elements.field_hints: list helpers and OutputType defaults."""

from homeassistant.components.number.const import DEFAULT_MAX_VALUE, DEFAULT_MIN_VALUE

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.elements.grid import GridConfigSchema
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints, extract_field_hints
from custom_components.haeo.core.schema.sections import CONF_PRICE_SOURCE_TARGET, SECTION_PRICING
from custom_components.haeo.elements.field_hints import (
    OUTPUT_TYPE_DEFAULTS,
    PRICE_NATIVE_MAX_VALUE,
    PRICE_NATIVE_MIN_VALUE,
    _build_translation_key,
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
    items: object = ["not_a_dict", {"name": "grid", "price": 0.30}]

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


def test_build_translation_key_without_device_type() -> None:
    """Fields without a device_type produce the simple element_field translation key."""
    assert _build_translation_key("battery", "capacity", None) == "battery_capacity"
    assert _build_translation_key("grid", "price_source_target", None) == "grid_price_source_target"


def test_build_translation_key_with_device_type_disambiguates_partitions() -> None:
    """Battery undercharge/overcharge partition fields produce distinct translation keys.

    Without device_type qualification, both partitions of ``cost`` and ``percentage``
    collapse onto identical ``battery_cost`` / ``battery_percentage`` keys, which
    renders as duplicate "Cost" and "Percentage" entries on the battery device card
    in Home Assistant. See issue #427.
    """
    under_cost = _build_translation_key("battery", "cost", "undercharge_partition")
    over_cost = _build_translation_key("battery", "cost", "overcharge_partition")
    under_pct = _build_translation_key("battery", "percentage", "undercharge_partition")
    over_pct = _build_translation_key("battery", "percentage", "overcharge_partition")

    assert under_cost == "battery_undercharge_partition_cost"
    assert over_cost == "battery_overcharge_partition_cost"
    assert under_pct == "battery_undercharge_partition_percentage"
    assert over_pct == "battery_overcharge_partition_percentage"
    # All four keys must be distinct so HA renders them as separate entity names.
    assert len({under_cost, over_cost, under_pct, over_pct}) == 4


def test_build_translation_key_empty_string_device_type_treated_as_absent() -> None:
    """An empty ``device_type`` is falsy and produces the unqualified key."""
    assert _build_translation_key("battery", "capacity", "") == "battery_capacity"
