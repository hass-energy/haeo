"""Tests for ScalarLoader handling current sensor values."""

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader.scalar_loader import ScalarLoader
from custom_components.haeo.schema import as_entity_value


async def test_scalar_loader_available_missing_sensor(hass: HomeAssistant) -> None:
    """Scalar loader is unavailable when sensors are missing."""
    loader = ScalarLoader()
    assert loader.available(hass=hass, value=as_entity_value(["sensor.missing"])) is False


async def test_scalar_loader_load_requires_entity_ids(hass: HomeAssistant) -> None:
    """Scalar loader raises when no sensors are provided."""
    loader = ScalarLoader()
    with pytest.raises(ValueError, match="At least one sensor entity is required"):
        await loader.load(hass=hass, value=as_entity_value([]))


async def test_scalar_loader_loads_and_converts_units(hass: HomeAssistant) -> None:
    """Scalar loader converts units and sums multiple sensors."""
    loader = ScalarLoader()

    hass.states.async_set(
        "sensor.power_one",
        "500",
        {
            "device_class": SensorDeviceClass.POWER,
            "unit_of_measurement": UnitOfPower.WATT,
        },
    )
    hass.states.async_set(
        "sensor.power_two",
        "1.5",
        {
            "device_class": SensorDeviceClass.POWER,
            "unit_of_measurement": UnitOfPower.KILO_WATT,
        },
    )

    assert loader.available(hass=hass, value=as_entity_value(["sensor.power_one", "sensor.power_two"])) is True

    result = await loader.load(hass=hass, value=as_entity_value(["sensor.power_one", "sensor.power_two"]))

    assert result == pytest.approx(2.0)
