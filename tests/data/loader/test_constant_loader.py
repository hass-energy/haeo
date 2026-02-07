"""Unit tests for ConstantLoader."""

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import ConstantLoader


async def test_constant_loader(hass: HomeAssistant) -> None:
    """Test constant loader functions directly."""
    constant_loader = ConstantLoader[int](int)
    assert constant_loader.available(hass=hass, value=100, forecast_times=[]) is True
    assert await constant_loader.load(hass=hass, value=100, forecast_times=[]) == 100


@pytest.mark.parametrize(
    ("loader_type", "method", "value"),
    [
        pytest.param(float, "available", "not_a_number", id="available_wrong_type"),
        pytest.param(int, "load", "not_an_int", id="load_wrong_type"),
    ],
)
async def test_constant_loader_rejects_wrong_type(
    loader_type: type[int] | type[float],
    method: str,
    value: object,
) -> None:
    """ConstantLoader raises TypeError for wrong types across available/load."""
    constant_loader = ConstantLoader(loader_type)
    with pytest.raises(TypeError, match="Value must be of type"):
        if method == "available":
            constant_loader.available(value=value)
        else:
            await constant_loader.load(value=value)


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


@pytest.mark.parametrize(
    ("loader_type", "value", "expected"),
    [
        pytest.param(float, 5.0, True, id="float_value"),
        pytest.param(float, 5, True, id="float_from_int"),
        pytest.param(float, "5.0", False, id="float_string"),
        pytest.param(float, None, False, id="float_none"),
        pytest.param(int, 42, True, id="int_value"),
        pytest.param(int, "not_an_int", False, id="int_string"),
        pytest.param(int, 3.14, False, id="int_float"),
    ],
)
def test_constant_loader_is_valid_value(
    loader_type: type[int] | type[float],
    value: object,
    expected: bool,
) -> None:
    """ConstantLoader.is_valid_value handles scalar variants consistently."""
    loader = ConstantLoader(loader_type)
    assert loader.is_valid_value(value) is expected
