"""Unit tests for SensorLoader."""

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.const import convert_to_base_unit
from custom_components.haeo.data.loader import SensorLoader


@pytest.mark.parametrize(
    ("value", "unit", "cls", "expected"),
    [
        (1, UnitOfPower.WATT, SensorDeviceClass.POWER, 0.001),
        (1, UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, 1),
        (5, "kWh", SensorDeviceClass.ENERGY, 5),
        (75, "%", SensorDeviceClass.BATTERY, 75),
    ],
)
def test_convert_to_base_unit(value: float, unit: str, cls: SensorDeviceClass | str, expected: float) -> None:
    """Ensure the helper converts as expected to kW/kWh base units."""
    device_class = cls if isinstance(cls, SensorDeviceClass) else None
    assert convert_to_base_unit(value, unit, device_class) == expected


async def test_sensor_loader_single(hass: HomeAssistant) -> None:
    """Load a single sensor value with unit conversion to kW."""
    sensor_loader = SensorLoader()
    hass.states.async_set(
        "sensor.power", "1000", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT}
    )
    assert sensor_loader.available(hass=hass, value=["sensor.power"], forecast_times=[]) is True
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
    assert pytest.approx(result) == 1.5


async def test_sensor_loader_missing_sensor(hass: HomeAssistant) -> None:
    """Test SensorLoader raises error when sensor not found."""
    sensor_loader = SensorLoader()
    assert sensor_loader.available(hass=hass, value=["sensor.missing"], forecast_times=[]) is False

    with pytest.raises(ValueError, match=r"Sensor sensor\.missing not found"):
        await sensor_loader.load(hass=hass, value=["sensor.missing"], forecast_times=[])


async def test_sensor_loader_invalid_state(hass: HomeAssistant) -> None:
    """Test SensorLoader handles invalid state values."""
    sensor_loader = SensorLoader()
    hass.states.async_set("sensor.invalid", "not_a_number")

    assert sensor_loader.available(hass=hass, value=["sensor.invalid"], forecast_times=[]) is True

    with pytest.raises(ValueError, match="Cannot parse sensor value"):
        await sensor_loader.load(hass=hass, value=["sensor.invalid"], forecast_times=[])


async def test_sensor_loader_unavailable_state(hass: HomeAssistant) -> None:
    """Test SensorLoader handles unavailable sensor states."""
    sensor_loader = SensorLoader()
    hass.states.async_set("sensor.unavailable", "unavailable")

    assert sensor_loader.available(hass=hass, value=["sensor.unavailable"], forecast_times=[]) is False


async def test_sensor_loader_unknown_state(hass: HomeAssistant) -> None:
    """Test SensorLoader handles unknown sensor states."""
    sensor_loader = SensorLoader()
    hass.states.async_set("sensor.unknown", "unknown")

    assert sensor_loader.available(hass=hass, value=["sensor.unknown"], forecast_times=[]) is False


async def test_sensor_loader_invalid_type(hass: HomeAssistant) -> None:
    """Test SensorLoader TypeGuard validates input types."""
    sensor_loader = SensorLoader()

    assert sensor_loader.is_valid_value(123) is False
    assert sensor_loader.is_valid_value({"key": "value"}) is False
    assert sensor_loader.is_valid_value(None) is False

    assert sensor_loader.is_valid_value("sensor.test") is True
    assert sensor_loader.is_valid_value(["sensor.test1", "sensor.test2"]) is True
