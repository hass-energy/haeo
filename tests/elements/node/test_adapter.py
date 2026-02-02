"""Tests for node adapter availability and model elements."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import node


async def test_available_returns_true(hass: HomeAssistant) -> None:
    """Node available() should return True since nodes have no sensor dependencies."""
    config: node.NodeConfigSchema = {
        "element_type": "node",
        "common": {"name": "test_node"},
        "advanced": {"is_source": False, "is_sink": False},
    }

    result = node.adapter.available(config, hass=hass)
    assert result is True


def test_model_elements_applies_default_flags() -> None:
    """model_elements() should apply default is_source/is_sink flags."""
    config_data: node.NodeConfigData = {
        "element_type": "node",
        "common": {"name": "test_node"},
        "advanced": {},
    }

    elements = node.adapter.model_elements(config_data)

    assert len(elements) == 1
    node_element = elements[0]
    assert node_element["name"] == "test_node"
    assert node_element.get("is_source") is False
    assert node_element.get("is_sink") is False
