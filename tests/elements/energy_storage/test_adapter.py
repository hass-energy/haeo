"""Tests for energy_storage adapter load() and available() functions."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import energy_storage


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


FORECAST_TIMES: Sequence[float] = [0.0, 1800.0]


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Energy storage available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    config: energy_storage.EnergyStorageConfigSchema = {
        "element_type": "energy_storage",
        "name": "test_storage",
        "capacity": ["sensor.capacity"],
        "initial_charge": ["sensor.initial"],
    }

    result = energy_storage.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_sensor_missing(hass: HomeAssistant) -> None:
    """Energy storage available() should return False when a required sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    # Not setting initial_charge sensor

    config: energy_storage.EnergyStorageConfigSchema = {
        "element_type": "energy_storage",
        "name": "test_storage",
        "capacity": ["sensor.capacity"],
        "initial_charge": ["sensor.missing"],
    }

    result = energy_storage.adapter.available(config, hass=hass)
    assert result is False


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Energy storage load() should return ConfigData with loaded values."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    config: energy_storage.EnergyStorageConfigSchema = {
        "element_type": "energy_storage",
        "name": "test_storage",
        "capacity": ["sensor.capacity"],
        "initial_charge": ["sensor.initial"],
    }

    result = await energy_storage.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "energy_storage"
    assert result["name"] == "test_storage"
    assert len(result["capacity"]) == 1
    assert result["capacity"][0] == 10.0
    assert len(result["initial_charge"]) == 1
    assert result["initial_charge"][0] == 50.0
