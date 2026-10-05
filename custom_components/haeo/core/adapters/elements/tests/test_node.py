"""Tests for node adapter availability and model elements."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.adapters.elements.node import adapter as node_adapter
from custom_components.haeo.core.schema.elements import ElementType, node
from custom_components.haeo.elements.availability import schema_config_available


async def test_available_returns_true(hass: HomeAssistant) -> None:
    """Node available() should return True since nodes have no sensor dependencies."""
    config: node.NodeConfigSchema = {
        "element_type": ElementType.NODE,
        "name": "test_node",
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


def test_model_elements_creates_pure_junction() -> None:
    """model_elements() should always create a node that neither sources nor sinks power."""
    config_data: node.NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "test_node",
    }

    elements = node_adapter.model_elements(config_data)

    assert len(elements) == 1
    node_element = elements[0]
    assert node_element["name"] == "test_node"
    assert node_element.get("is_source") is False
    assert node_element.get("is_sink") is False
