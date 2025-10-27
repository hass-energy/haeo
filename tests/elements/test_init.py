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
