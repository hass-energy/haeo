"""Tests for node adapter model elements."""

from custom_components.haeo.core.adapters.elements.node import adapter as node_adapter
from custom_components.haeo.core.schema.elements import ElementType, node


def test_model_elements_applies_default_flags() -> None:
    """model_elements() should apply default is_source/is_sink flags."""
    config_data: node.NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "test_node",
        node.SECTION_ROLE: {},
    }

    elements = node_adapter.model_elements(config_data)

    assert len(elements) == 1
    node_element = elements[0]
    assert node_element["name"] == "test_node"
    assert node_element.get("is_source") is False
    assert node_element.get("is_sink") is False
