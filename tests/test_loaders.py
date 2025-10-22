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
