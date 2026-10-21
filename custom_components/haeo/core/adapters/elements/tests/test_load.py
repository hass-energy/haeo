"""Tests for load element adapter inputs."""

from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements import load as load_element
from custom_components.haeo.elements import get_input_fields


def test_inputs_returns_input_fields() -> None:
    """The load's input fields include its forecast and curtailment."""
    input_fields = get_input_fields(ElementType.LOAD)

    assert load_element.SECTION_FORECAST in input_fields
    assert "forecast" in input_fields[load_element.SECTION_FORECAST]

    assert load_element.SECTION_CURTAILMENT in input_fields
    assert "curtailment" in input_fields[load_element.SECTION_CURTAILMENT]
