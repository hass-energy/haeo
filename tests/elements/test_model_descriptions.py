"""Test model description functions in elements module."""

from typing import Any, cast

import pytest

from custom_components.haeo.elements import ElementConfigSchema, get_model_description
from tests.test_data.elements import ALL_VALID_CONFIGS


@pytest.mark.parametrize(
    ("element_type", "test_case"),
    ALL_VALID_CONFIGS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_valid_element_descriptions(element_type: str, test_case: dict[str, Any]) -> None:
    """Test model description generation for valid element configurations."""
    config = test_case["data"]
    expected = test_case["expected_description"]

    description = get_model_description(cast("ElementConfigSchema", config))

    assert description == expected, f"Failed for {element_type}: {test_case['description']}"


def test_unknown_element_type_raises_error() -> None:
    """Test that unknown element type raises ValueError."""
    config = {
        "element_type": "unknown_type",
        "name": "Test",
    }

    with pytest.raises(ValueError, match="Unknown element type"):
        get_model_description(cast("ElementConfigSchema", config))
