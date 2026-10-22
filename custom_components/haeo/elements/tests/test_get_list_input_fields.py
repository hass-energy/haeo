"""Tests for get_list_input_fields."""

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.constant_value import as_constant_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_RULES
from custom_components.haeo.elements import get_list_input_fields


def test_get_list_input_fields_empty_for_unknown_element_type() -> None:
    """Invalid element_type yields no dynamic list fields."""
    assert get_list_input_fields({CONF_ELEMENT_TYPE: "not_an_element"}) == {}


def test_get_list_input_fields_skips_non_sequence_list_items() -> None:
    """List hint keys that are not list/tuple are ignored."""
    cfg = {
        CONF_ELEMENT_TYPE: ElementType.POLICY,
        "name": "Policies",
        CONF_RULES: "not-a-list",
    }
    assert get_list_input_fields(cfg) == {}


def test_get_list_input_fields_builds_policy_rule_fields() -> None:
    """Policy rules list produces per-item field definitions."""
    cfg = {
        CONF_ELEMENT_TYPE: ElementType.POLICY,
        "name": "Policies",
        CONF_RULES: [
            {"name": "Export", CONF_ENABLED: True, "price": as_constant_value(0.05)},
        ],
    }
    groups = get_list_input_fields(cfg)
    assert f"{CONF_RULES}.0" in groups
    assert CONF_ENABLED in groups[f"{CONF_RULES}.0"]
    assert "price" in groups[f"{CONF_RULES}.0"]
