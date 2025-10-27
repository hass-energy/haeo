"""Unit tests for ConstantLoader."""

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import ConstantLoader


async def test_constant_loader(hass: HomeAssistant) -> None:
    """Test constant loader functions directly."""
    constant_loader = ConstantLoader[int](int)
    assert constant_loader.available(hass=hass, value=100, forecast_times=[]) is True
    assert await constant_loader.load(hass=hass, value=100, forecast_times=[]) == 100


async def test_constant_loader_wrong_type_available(hass: HomeAssistant) -> None:
    """Test ConstantLoader.available() raises TypeError for wrong type."""
    constant_loader = ConstantLoader[float](float)
    with pytest.raises(TypeError, match="Value must be of type"):
        constant_loader.available(hass=hass, value="not_a_number", forecast_times=[])


async def test_constant_loader_wrong_type_load(hass: HomeAssistant) -> None:
    """Test ConstantLoader.load() raises TypeError for wrong type."""
    constant_loader = ConstantLoader[int](int)
    with pytest.raises(TypeError, match="Value must be of type"):
        await constant_loader.load(hass=hass, value="not_an_int", forecast_times=[])


async def test_constant_loader_type_guard(hass: HomeAssistant) -> None:
    """Test ConstantLoader.is_valid_value() TypeGuard."""
    float_loader = ConstantLoader[float](float)
    assert float_loader.is_valid_value(5.0) is True
    assert float_loader.is_valid_value(5) is True
    assert float_loader.is_valid_value("5.0") is False
    assert float_loader.is_valid_value(None) is False


async def test_constant_loader_invalid_type() -> None:
    """Test ConstantLoader validates type correctly."""
    int_loader = ConstantLoader[int](int)

    with pytest.raises(TypeError, match="Value must be of type"):
        int_loader.available(value="not_a_number")

    assert int_loader.available(value=42) is True
    result = await int_loader.load(value=42)
    assert result == 42


async def test_constant_loader_float_conversion() -> None:
    """Test ConstantLoader handles float conversions."""
    float_loader = ConstantLoader[float](float)

    assert float_loader.available(value=42) is True
    result = await float_loader.load(value=42)
    assert result == 42.0
    assert isinstance(result, float)

    assert float_loader.available(value=3.14) is True
    result = await float_loader.load(value=3.14)
    assert result == 3.14


async def test_constant_loader_type_validation() -> None:
    """Test ConstantLoader is_valid_value method."""
    int_loader = ConstantLoader[int](int)

    assert int_loader.is_valid_value(42) is True
    assert int_loader.is_valid_value("not_an_int") is False
    assert int_loader.is_valid_value(3.14) is False
