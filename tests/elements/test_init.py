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


def test_is_element_config_schema_unknown_element_type() -> None:
    """Test is_element_config_schema with unknown element_type."""
    assert is_element_config_schema({"element_type": "unknown_type"}) is False


def test_is_element_config_schema_invalid_schema() -> None:
    """Test is_element_config_schema with valid type but invalid schema."""
    # Battery requires 'name' field, so this should fail validation
    assert is_element_config_schema({"element_type": "battery"}) is False


def test_is_element_config_schema_valid() -> None:
    """Test is_element_config_schema with valid element config."""
    valid_config = {
        "element_type": "node",
        "name": "test_node",
        "is_source": False,
        "is_sink": False,
    }
    assert is_element_config_schema(valid_config) is True
