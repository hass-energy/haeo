"""Tests that input entities and input stores agree on an element's inputs."""

import pytest

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.data.loader.config_loader import element_inputs
from custom_components.haeo.core.schema.constant_value import as_constant_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_RULES
from custom_components.haeo.elements import (
    config_field_path,
    get_input_fields,
    get_list_input_fields,
    iter_input_field_paths,
)


@pytest.mark.parametrize("element_type", list(ElementType))
def test_entity_inputs_match_store_inputs(element_type: ElementType) -> None:
    """Every input path, and the config path it reads, is the same for entities and stores."""
    config: dict[str, object] = {
        CONF_ELEMENT_TYPE: element_type,
        CONF_RULES: [
            {"name": "Export", CONF_ENABLED: True, "price": as_constant_value(0.05)},
            {"name": "Import", CONF_ENABLED: False, "price": as_constant_value(0.30)},
        ],
    }
    field_infos = {**get_input_fields(config), **get_list_input_fields(config)}
    entity_paths = {(path, config_field_path(path, field_info)) for path, field_info in iter_input_field_paths(field_infos)}

    assert {(element_input.path, element_input.config_path) for element_input in element_inputs(config)} == (entity_paths)
