"""Unit tests for the new HAEO data loaders."""

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.const import convert_to_base_unit
from custom_components.haeo.data.loader import constant_loader, sensor_loader

# -----------------------------------------------------------------------------
# convert_to_base_unit
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "unit", "cls", "expected"),
    [
        (1, UnitOfPower.WATT, SensorDeviceClass.POWER, 1),
        (1, UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, 1000),
        (5, "kWh", SensorDeviceClass.ENERGY, 5000),
        (75, "%", SensorDeviceClass.BATTERY, 75),
    ],
)
def test_convert_to_base_unit(value: float, unit: str, cls: SensorDeviceClass | str, expected: float) -> None:
    """Ensure the helper converts as expected."""
    device_class = cls if isinstance(cls, SensorDeviceClass) else None
    assert convert_to_base_unit(value, unit, device_class) == expected


# -----------------------------------------------------------------------------
# SensorLoader
# -----------------------------------------------------------------------------


async def test_sensor_loader_single(hass: HomeAssistant) -> None:
    """Load a single sensor value with unit conversion."""
    hass.states.async_set(
        "sensor.power", "1000", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT}
    )
    assert sensor_loader.available(hass=hass, value=["sensor.power"]) is True
    assert await sensor_loader.load(hass=hass, value=["sensor.power"]) == 1000.0


async def test_sensor_loader_multiple(hass: HomeAssistant) -> None:
    """Sum multiple sensors."""
    hass.states.async_set(
        "sensor.a", "1", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.KILO_WATT}
    )
    hass.states.async_set(
        "sensor.b", "500", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT}
    )
    result = await sensor_loader.load(hass=hass, value=["sensor.a", "sensor.b"])
    # 1 kW + 500 W = 1500 W
    assert pytest.approx(result) == 1500


@pytest.mark.asyncio
async def test_constant_loader() -> None:
    """Test constant loader functions directly."""
    assert constant_loader.available(value=100) is True  # Constants are always available
    assert await constant_loader.load(value=100) == 100
