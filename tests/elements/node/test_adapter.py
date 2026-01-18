"""Tests for node adapter build_config_data() and available() functions."""

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


def test_build_config_data_returns_config_data() -> None:
    """build_config_data() should return ConfigData with loaded values."""
    config: node.NodeConfigSchema = {
        "element_type": "node",
        "name": "test_node",
        "is_source": False,
        "is_sink": False,
    }
    loaded_values: node.NodeConfigData = {
        "element_type": "node",
        "name": "test_node",
        "is_source": True,
        "is_sink": False,
    }

    result = node.adapter.build_config_data(loaded_values, config)

    assert result["element_type"] == "node"
    assert result["name"] == "test_node"
    assert result.get("is_source") is True
    assert result.get("is_sink") is False
