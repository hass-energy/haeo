"""Test schema generation for HAEO types."""

import pytest

from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.types import ELEMENT_TYPES


@pytest.fixture
def schema_params():
    """Fixture providing schema parameters for tests."""
    return {"participants": ["test_element_1", "test_element_2"]}


@pytest.mark.parametrize(("element_type", "config_class"), [(name, cls) for name, cls in ELEMENT_TYPES.items()])
def test_schema_for_type(element_type, config_class, schema_params):
    """Test schema for type."""

    # Always pass participants - in real code this will be provided
    schema = schema_for_type(config_class, **schema_params)

    assert schema is not None
    # Just check that the schema has some fields
    assert len(schema.schema) > 0
