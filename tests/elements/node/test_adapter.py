"""Tests for node adapter load() and available() functions."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import node

FORECAST_TIMES: Sequence[float] = [0.0, 1800.0]


async def test_available_returns_true(hass: HomeAssistant) -> None:
    """Node available() should return True since nodes have no sensor dependencies."""
    config: node.NodeConfigSchema = {
        "element_type": "node",
        "name": "test_node",
        "is_source": False,
        "is_sink": False,
    }

    result = node.available(config, hass=hass)
    assert result is True


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Node load() should return ConfigData with name and type."""
    config: node.NodeConfigSchema = {
        "element_type": "node",
        "name": "test_node",
        "is_source": False,
        "is_sink": False,
    }

    result = await node.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "node"
    assert result["name"] == "test_node"
