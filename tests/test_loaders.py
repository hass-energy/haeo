"""Unit tests for the new HAEO data loaders."""

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.const import convert_to_base_unit
from custom_components.haeo.data.loader import ConstantLoader, SensorLoader

# -----------------------------------------------------------------------------
# convert_to_base_unit
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "unit", "cls", "expected"),
    [
        (1, UnitOfPower.WATT, SensorDeviceClass.POWER, 0.001),  # 1 W = 0.001 kW
        (1, UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, 1),  # 1 kW = 1 kW
        (5, "kWh", SensorDeviceClass.ENERGY, 5),  # 5 kWh = 5 kWh
        (75, "%", SensorDeviceClass.BATTERY, 75),  # Percentage unchanged
    ],
)
def test_convert_to_base_unit(value: float, unit: str, cls: SensorDeviceClass | str, expected: float) -> None:
    """Ensure the helper converts as expected to kW/kWh base units."""
    device_class = cls if isinstance(cls, SensorDeviceClass) else None
    assert convert_to_base_unit(value, unit, device_class) == expected


# -----------------------------------------------------------------------------
# SensorLoader
# -----------------------------------------------------------------------------


async def test_sensor_loader_single(hass: HomeAssistant) -> None:
    """Load a single sensor value with unit conversion to kW."""
    sensor_loader = SensorLoader()
    hass.states.async_set(
        "sensor.power", "1000", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT}
    )
    assert sensor_loader.available(hass=hass, value=["sensor.power"], forecast_times=[]) is True
    # 1000 W = 1.0 kW
    assert await sensor_loader.load(hass=hass, value=["sensor.power"], forecast_times=[]) == 1.0


async def test_sensor_loader_multiple(hass: HomeAssistant) -> None:
    """Sum multiple sensors in kW."""
    sensor_loader = SensorLoader()
    hass.states.async_set(
        "sensor.a", "1", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.KILO_WATT}
    )
    hass.states.async_set(
        "sensor.b", "500", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT}
    )
    result = await sensor_loader.load(hass=hass, value=["sensor.a", "sensor.b"], forecast_times=[])
    # 1 kW + 500 W = 1 kW + 0.5 kW = 1.5 kW
    assert pytest.approx(result) == 1.5


@pytest.mark.asyncio
async def test_constant_loader(hass: HomeAssistant) -> None:
    """Test constant loader functions directly."""
    constant_loader = ConstantLoader[int](int)
    assert constant_loader.available(hass=hass, value=100, forecast_times=[]) is True  # Constants are always available
    assert await constant_loader.load(hass=hass, value=100, forecast_times=[]) == 100


async def test_constant_loader_wrong_type_available(hass: HomeAssistant) -> None:
    """Test ConstantLoader.available() raises TypeError for wrong type."""
    constant_loader = ConstantLoader[float](float)
    # Passing a string when expecting float should raise TypeError
    with pytest.raises(TypeError, match="Value must be of type"):
        constant_loader.available(hass=hass, value="not_a_number", forecast_times=[])


async def test_constant_loader_wrong_type_load(hass: HomeAssistant) -> None:
    """Test ConstantLoader.load() raises TypeError for wrong type."""
    constant_loader = ConstantLoader[int](int)
    # Passing a string when expecting int should raise TypeError
    with pytest.raises(TypeError, match="Value must be of type"):
        await constant_loader.load(hass=hass, value="not_an_int", forecast_times=[])


async def test_constant_loader_type_guard(hass: HomeAssistant) -> None:
    """Test ConstantLoader.is_valid_value() TypeGuard."""
    float_loader = ConstantLoader[float](float)
    # Valid float inputs
    assert float_loader.is_valid_value(5.0) is True
    assert float_loader.is_valid_value(5) is True  # int is Real
    # Invalid inputs
    assert float_loader.is_valid_value("5.0") is False
    assert float_loader.is_valid_value(None) is False


async def test_sensor_loader_missing_sensor(hass: HomeAssistant) -> None:
    """Test SensorLoader raises error when sensor not found."""
    sensor_loader = SensorLoader()
    # Check availability first
    assert sensor_loader.available(hass=hass, value=["sensor.missing"], forecast_times=[]) is False

    # Try to load missing sensor - should raise ValueError
    with pytest.raises(ValueError, match=r"Sensor sensor\.missing not found"):
        await sensor_loader.load(hass=hass, value=["sensor.missing"], forecast_times=[])


async def test_sensor_loader_invalid_state(hass: HomeAssistant) -> None:
    """Test SensorLoader handles invalid state values."""
    sensor_loader = SensorLoader()
    hass.states.async_set("sensor.invalid", "not_a_number")

    # Should not be available
    assert sensor_loader.available(hass=hass, value=["sensor.invalid"], forecast_times=[]) is True

    # Try to load - should raise ValueError
    with pytest.raises(ValueError, match="Cannot parse sensor value"):
        await sensor_loader.load(hass=hass, value=["sensor.invalid"], forecast_times=[])


async def test_sensor_loader_unavailable_state(hass: HomeAssistant) -> None:
    """Test SensorLoader handles unavailable sensor states."""
    sensor_loader = SensorLoader()
    hass.states.async_set("sensor.unavailable", "unavailable")

    # Should not be available
    assert sensor_loader.available(hass=hass, value=["sensor.unavailable"], forecast_times=[]) is False


async def test_sensor_loader_unknown_state(hass: HomeAssistant) -> None:
    """Test SensorLoader handles unknown sensor states."""
    sensor_loader = SensorLoader()
    hass.states.async_set("sensor.unknown", "unknown")

    # Should not be available
    assert sensor_loader.available(hass=hass, value=["sensor.unknown"], forecast_times=[]) is False


async def test_sensor_loader_invalid_type(hass: HomeAssistant) -> None:
    """Test SensorLoader TypeGuard validates input types."""
    sensor_loader = SensorLoader()

    # TypeGuard should return False for invalid types
    assert sensor_loader.is_valid_value(123) is False
    assert sensor_loader.is_valid_value({"key": "value"}) is False
    assert sensor_loader.is_valid_value(None) is False

    # TypeGuard should return True for valid types
    assert sensor_loader.is_valid_value("sensor.test") is True
    assert sensor_loader.is_valid_value(["sensor.test1", "sensor.test2"]) is True


async def test_constant_loader_invalid_type() -> None:
    """Test ConstantLoader validates type correctly."""
    # Create loader expecting int
    int_loader = ConstantLoader[int](int)

    # Test with invalid type - should raise TypeError
    with pytest.raises(TypeError, match="Value must be of type"):
        int_loader.available(value="not_a_number")

    # Test with valid type
    assert int_loader.available(value=42) is True
    result = await int_loader.load(value=42)
    assert result == 42


async def test_constant_loader_float_conversion() -> None:
    """Test ConstantLoader handles float conversions."""
    float_loader = ConstantLoader[float](float)

    # Test with integer (should convert to float)
    assert float_loader.available(value=42) is True
    result = await float_loader.load(value=42)
    assert result == 42.0
    assert isinstance(result, float)

    # Test with actual float
    assert float_loader.available(value=3.14) is True
    result = await float_loader.load(value=3.14)
    assert result == 3.14


async def test_constant_loader_type_validation() -> None:
    """Test ConstantLoader is_valid_value method."""
    int_loader = ConstantLoader[int](int)

    # Test valid value
    assert int_loader.is_valid_value(42) is True

    # Test invalid value
    assert int_loader.is_valid_value("not_an_int") is False
    assert int_loader.is_valid_value(3.14) is False
