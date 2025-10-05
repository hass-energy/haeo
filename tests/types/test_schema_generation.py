"""Test schema generation for HAEO types."""

import pytest

from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.types import ELEMENT_TYPES


@pytest.mark.parametrize(("element_type", "config_class"), [(name, cls) for name, cls in ELEMENT_TYPES.items()])
def test_schema_for_type(element_type, config_class):
    """Test schema for type."""

    schema = schema_for_type(config_class)
    assert schema is not None
    # Just check that the schema has some fields
    assert len(schema.schema) > 0
