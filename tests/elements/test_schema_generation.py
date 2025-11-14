"""Test schema generation for HAEO types."""

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.schema.params import SchemaParams


@pytest.fixture
def schema_params() -> SchemaParams:
    """Fixture providing schema parameters for tests."""
    return {
        "entity_metadata": [],
        "participants": ["test_element_1", "test_element_2"],
        "current_element_name": None,
    }


@pytest.mark.parametrize(
    ("element_type", "config_class"), [(name, schema_cls) for name, (schema_cls, *_) in ELEMENT_TYPES.items()]
)
def test_schema_for_type(element_type: str, config_class: type, schema_params: SchemaParams) -> None:
    """Test schema for type."""

    # Always pass participants - in real code this will be provided
    schema = schema_for_type(config_class, **schema_params)

    assert schema is not None
    # Just check that the schema has some fields
    assert len(schema.schema) > 0
