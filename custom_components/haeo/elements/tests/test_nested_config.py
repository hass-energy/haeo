"""Tests for nested config helper utilities."""

from typing import Any, cast

from custom_components.haeo.elements import (
    find_nested_config_path,
    get_nested_config_value,
    get_nested_config_value_by_path,
    set_nested_config_value,
    set_nested_config_value_by_path,
)


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
