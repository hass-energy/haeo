"""Tests for elements module __init__.py functions."""

from typing import Any

import pytest

from custom_components.haeo.elements import is_element_config_schema


@pytest.mark.parametrize(
    "input_data",
    [
        [1, 2, 3],
        "not a config",
        None,
    ],
)
def test_is_not_element_config_schema(input_data: Any) -> None:
    """Test is_element_config_schema with non-Mapping input."""
    assert is_element_config_schema(input_data) is False


@pytest.mark.parametrize(
    "input_data",
    [
        {"element_type": "unknown_type", "name": "test"},  # Unknown element type
        {"name": "test"},  # Missing element_type
        {"element_type": "battery"},  # Missing name
    ],
)
def test_is_element_config_schema_invalid_structure(input_data: dict[str, Any]) -> None:
    """Test is_element_config_schema with invalid element structure."""
    assert is_element_config_schema(input_data) is False


def test_is_element_config_schema_valid() -> None:
    """Test is_element_config_schema with valid element config."""
    valid_config = {
        "element_type": "node",
        "name": "test_node",
    }
    assert is_element_config_schema(valid_config) is True
