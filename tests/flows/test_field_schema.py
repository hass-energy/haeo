"""Tests for flows/field_schema.py utilities."""

from homeassistant.components.number import NumberEntityDescription
from homeassistant.helpers.selector import BooleanSelector, NumberSelector
import pytest

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    boolean_selector_from_field,
    number_selector_from_field,
)
from custom_components.haeo.model.const import OutputType


# --- Fixtures ---


@pytest.fixture
def number_field() -> InputFieldInfo[NumberEntityDescription]:
    """Create a number input field for testing."""
    return InputFieldInfo(
        field_name="test_field",
        entity_description=NumberEntityDescription(
            key="test_field",
            name="Test Field",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
            native_unit_of_measurement="kW",
        ),
        output_type=OutputType.POWER,
        default=50.0,
    )


# --- Tests for boolean_selector_from_field ---


def test_boolean_selector_from_field_returns_boolean_selector() -> None:
    """Boolean selector is created."""
    selector = boolean_selector_from_field()
    assert isinstance(selector, BooleanSelector)


# --- Tests for number_selector_from_field ---


def test_number_selector_from_field_creates_selector(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Number selector is created with correct config."""
    selector = number_selector_from_field(number_field)
    assert isinstance(selector, NumberSelector)
