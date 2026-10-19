"""Tests for load element adapter availability and inputs."""

from custom_components.haeo.core.schema import as_connection_target, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements import load as load_element
from custom_components.haeo.elements import get_input_fields


def test_inputs_returns_input_fields() -> None:
    """inputs() should return input field definitions for load."""
    config: load_element.LoadConfigSchema = {
        "element_type": ElementType.LOAD,
        "name": "test_load",
        "connection": as_connection_target("main_bus"),
        load_element.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.power"])},
        load_element.SECTION_CURTAILMENT: {},
    }

    input_fields = get_input_fields(config)

    assert load_element.SECTION_FORECAST in input_fields
    assert "forecast" in input_fields[load_element.SECTION_FORECAST]

    assert load_element.SECTION_CURTAILMENT in input_fields
    assert "curtailment" in input_fields[load_element.SECTION_CURTAILMENT]
