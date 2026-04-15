"""Tests for nested config helper utilities."""

from typing import Any, cast

from custom_components.haeo.elements import (
    find_nested_config_path,
    get_nested_config_value,
    get_nested_config_value_by_path,
    iter_input_field_paths,
    set_nested_config_value,
    set_nested_config_value_by_path,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.elements.field_hints import _build_field_info
from custom_components.haeo.core.schema.field_hints import FieldHint


def test_nested_config_helpers_find_values_and_paths() -> None:
    """Nested config helpers find values and paths in nested configs."""
    config: dict[str, Any] = {
        "common": {"name": "test", "connection": "bus"},
        "nested": {"inner": {"value": 5}},
    }

    assert get_nested_config_value(config, "value") == 5
    assert get_nested_config_value(config, "missing") is None

    assert find_nested_config_path(config, "common") == ("common",)
    assert find_nested_config_path(config, "value") == ("nested", "inner", "value")
    assert find_nested_config_path(config, "missing") is None


def test_nested_config_value_by_path_and_setters() -> None:
    """Nested config helpers resolve and set values by name or path."""
    config: dict[str, Any] = {
        "common": {"name": "test"},
        "nested": {"inner": {"value": 5}},
    }

    assert get_nested_config_value_by_path(config, ("nested", "inner", "value")) == 5
    assert get_nested_config_value_by_path(config, ("common", "name", "extra")) is None
    assert get_nested_config_value_by_path(config, ("missing",)) is None

    assert set_nested_config_value(config, "value", 10) is True
    assert config["nested"]["inner"]["value"] == 10
    assert set_nested_config_value(config, "missing", 1) is False

    assert set_nested_config_value_by_path(config, ("nested", "inner", "value"), 20) is True
    assert config["nested"]["inner"]["value"] == 20
    assert set_nested_config_value_by_path(config, ("common", "name", "extra"), 1) is False

    invalid_config = cast(dict[str, Any], "not-a-dict")
    assert set_nested_config_value_by_path(invalid_config, ("field",), 1) is False
    assert set_nested_config_value_by_path(invalid_config, ("field", "inner"), 1) is False


def test_get_nested_config_value_by_path_list_traversal() -> None:
    """Path traversal navigates into list items by integer index."""
    config: dict[str, Any] = {
        "rules": [
            {"name": "solar", "price": 0.05},
            {"name": "grid", "price": 0.30},
        ],
    }

    assert get_nested_config_value_by_path(config, ("rules", "0", "price")) == 0.05
    assert get_nested_config_value_by_path(config, ("rules", "1", "name")) == "grid"

    # Out-of-range index
    assert get_nested_config_value_by_path(config, ("rules", "5", "price")) is None

    # Non-integer index
    assert get_nested_config_value_by_path(config, ("rules", "abc", "price")) is None

    # Path into non-container
    assert get_nested_config_value_by_path(config, ("rules", "0", "price", "extra")) is None

    # Tuple data works the same as list
    config_tuple: dict[str, Any] = {"items": ({"x": 1}, {"x": 2})}
    assert get_nested_config_value_by_path(config_tuple, ("items", "1", "x")) == 2


def test_set_nested_config_value_by_path_list_traversal() -> None:
    """Path setter navigates into list items by integer index."""
    config: dict[str, Any] = {
        "rules": [
            {"name": "solar", "price": 0.05},
            {"name": "grid", "price": 0.30},
        ],
    }

    # Set a value inside a list item
    assert set_nested_config_value_by_path(config, ("rules", "0", "price"), 0.10) is True
    assert config["rules"][0]["price"] == 0.10

    # Set value where final target is a list item
    config2: dict[str, Any] = {"items": [10, 20, 30]}
    assert set_nested_config_value_by_path(config2, ("items", "1"), 99) is True
    assert config2["items"][1] == 99

    # Out-of-range index in intermediate list
    assert set_nested_config_value_by_path(config, ("rules", "5", "price"), 1.0) is False

    # Non-integer index in intermediate list
    assert set_nested_config_value_by_path(config, ("rules", "abc", "price"), 1.0) is False

    # Out-of-range index in final list
    assert set_nested_config_value_by_path(config2, ("items", "10"), 0) is False

    # Non-integer index in final list
    assert set_nested_config_value_by_path(config2, ("items", "abc"), 0) is False

    # Intermediate path hits non-dict, non-list value
    assert set_nested_config_value_by_path(config, ("rules", "0", "name", "extra"), 1) is False

    # Final path hits non-dict, non-list value
    config3: dict[str, Any] = {"x": 42}
    assert set_nested_config_value_by_path(config3, ("x",), 99) is True
    assert config3["x"] == 99


def test_iter_input_field_paths_expands_dotted_keys() -> None:
    """Dotted section keys are expanded into 3-tuple field paths."""
    info = _build_field_info("price", FieldHint(output_type=OutputType.PRICE), "policy_price")

    input_fields = {
        "storage": {"capacity": info},
        "rules.0": {"price": info},
        "rules.1": {"price": info},
    }

    paths = iter_input_field_paths(input_fields)

    section_paths = [p for p, _ in paths if len(p) == 2]
    list_paths = [p for p, _ in paths if len(p) == 3]

    assert section_paths == [("storage", "capacity")]
    assert ("rules", "0", "price") in list_paths
    assert ("rules", "1", "price") in list_paths
