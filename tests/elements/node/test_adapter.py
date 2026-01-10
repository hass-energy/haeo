"""Tests for node adapter available() function."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import node


async def test_available_returns_true(hass: HomeAssistant) -> None:
    """Node available() should return True since nodes have no sensor dependencies."""
    config: node.NodeConfigSchema = {
        "element_type": "node",
        "name": "test_node",
        "is_source": False,
        "is_sink": False,
    }

    result = node.adapter.available(config, hass=hass)
    assert result is True
