"""Unit tests for sensor payload helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader.extractors import ExtractedData
from custom_components.haeo.data.loader.extractors.utils import convert_to_base_unit
from custom_components.haeo.data.loader.sensor_loader import load_sensor, load_sensors, normalize_entity_ids


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


def test_normalize_entity_ids_accepts_str_and_sequence() -> None:
    """Normalization converts both strings and sequences to lists of IDs."""

    assert normalize_entity_ids("sensor.single") == ["sensor.single"]
    assert normalize_entity_ids(["sensor.one", "sensor.two"]) == ["sensor.one", "sensor.two"]

    with pytest.raises(TypeError, match="sensor entity ID"):
        normalize_entity_ids(123)


def test_load_sensor_forecast_returns_series(hass: HomeAssistant) -> None:
    """Forecast sensors return raw timestamp/value pairs."""

    start = datetime(2024, 1, 1, tzinfo=UTC)
    hass.states.async_set(
        "sensor.forecast",
        "0.0",
        {
            "device_class": SensorDeviceClass.POWER,
            "unit_of_measurement": UnitOfPower.KILO_WATT,
        },
    )

    with patch(
        "custom_components.haeo.data.loader.sensor_loader.extract",
        return_value=ExtractedData(
            data=[
                (int((start + timedelta(hours=1)).timestamp()), 1.5),
                (int((start + timedelta(hours=2)).timestamp()), 2.5),
            ],
            unit=UnitOfPower.KILO_WATT,
        ),
    ):
        payload = load_sensor(hass, "sensor.forecast")
        assert payload == [
            (int((start + timedelta(hours=1)).timestamp()), 1.5),
            (int((start + timedelta(hours=2)).timestamp()), 2.5),
        ]


def test_load_sensor_returns_none_when_unavailable(hass: HomeAssistant) -> None:
    """Load sensor returns None when sensor data is unavailable."""

    hass.states.async_set("sensor.unavailable", "unavailable", {})

    payload = load_sensor(hass, "sensor.unavailable")
    assert payload is None


def test_load_sensor_returns_none_when_missing(hass: HomeAssistant) -> None:
    """Load sensor returns None when sensor does not exist."""

    payload = load_sensor(hass, "sensor.missing")
    assert payload is None


async def test_load_sensors_returns_mapping(hass: HomeAssistant) -> None:
    """Load sensors returns the raw payload for each available sensor ID."""

    hass.states.async_set(
        "sensor.a",
        "1",
        {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.KILO_WATT},
    )
    hass.states.async_set(
        "sensor.b",
        "500",
        {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT},
    )

    payloads = load_sensors(hass, ["sensor.a", "sensor.b"])

    assert "sensor.a" in payloads
    assert "sensor.b" in payloads
    # Simple values are returned as floats
    assert isinstance(payloads["sensor.a"], float)
    assert isinstance(payloads["sensor.b"], float)
    assert payloads["sensor.a"] == 1.0
    assert payloads["sensor.b"] == 0.5


async def test_load_sensors_excludes_unavailable(hass: HomeAssistant) -> None:
    """Load sensors excludes sensors that are unavailable or missing."""

    hass.states.async_set(
        "sensor.a",
        "1",
        {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.KILO_WATT},
    )
    hass.states.async_set("sensor.unavailable", "unavailable", {})

    payloads = load_sensors(hass, ["sensor.a", "sensor.unavailable", "sensor.missing"])

    assert "sensor.a" in payloads
    assert "sensor.unavailable" not in payloads
    assert "sensor.missing" not in payloads
    assert len(payloads) == 1
