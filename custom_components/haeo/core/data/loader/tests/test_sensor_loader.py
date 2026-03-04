"""Unit tests for sensor payload helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.extractors import ExtractedData
from custom_components.haeo.core.data.loader.sensor_loader import load_sensor, load_sensors, normalize_entity_ids


def test_normalize_entity_ids_accepts_str_and_sequence() -> None:
    """Normalization converts both strings and sequences to lists of IDs."""

    assert normalize_entity_ids("sensor.single") == ["sensor.single"]
    assert normalize_entity_ids(["sensor.one", "sensor.two"]) == ["sensor.one", "sensor.two"]

    with pytest.raises(TypeError, match="sensor entity ID"):
        normalize_entity_ids(123)


def test_load_sensor_forecast_returns_series() -> None:
    """Forecast sensors return raw timestamp/value pairs."""

    start = datetime(2024, 1, 1, tzinfo=UTC)
    sm = FakeStateMachine(
        {
            "sensor.forecast": FakeEntityState(
                entity_id="sensor.forecast",
                state="0.0",
                attributes={"device_class": "power", "unit_of_measurement": "kW"},
            )
        }
    )

    with patch(
        "custom_components.haeo.core.data.loader.sensor_loader.extract",
        return_value=ExtractedData(
            data=[
                (int((start + timedelta(hours=1)).timestamp()), 1.5),
                (int((start + timedelta(hours=2)).timestamp()), 2.5),
            ],
            unit="kW",
        ),
    ):
        payload = load_sensor(sm, "sensor.forecast")
        assert payload == [
            (int((start + timedelta(hours=1)).timestamp()), 1.5),
            (int((start + timedelta(hours=2)).timestamp()), 2.5),
        ]


def test_load_sensor_returns_none_when_unavailable() -> None:
    """Load sensor returns None when sensor data is unavailable."""

    sm = FakeStateMachine(
        {
            "sensor.unavailable": FakeEntityState(
                entity_id="sensor.unavailable",
                state="unavailable",
                attributes={},
            )
        }
    )
    payload = load_sensor(sm, "sensor.unavailable")
    assert payload is None


def test_load_sensor_returns_none_when_missing() -> None:
    """Load sensor returns None when sensor does not exist."""

    payload = load_sensor(FakeStateMachine({}), "sensor.missing")
    assert payload is None


async def test_load_sensors_returns_mapping() -> None:
    """Load sensors returns the raw payload for each available sensor ID."""

    sm = FakeStateMachine(
        {
            "sensor.a": FakeEntityState(
                entity_id="sensor.a",
                state="1",
                attributes={"device_class": "power", "unit_of_measurement": "kW"},
            ),
            "sensor.b": FakeEntityState(
                entity_id="sensor.b",
                state="500",
                attributes={"device_class": "power", "unit_of_measurement": "W"},
            ),
        }
    )

    payloads = load_sensors(sm, ["sensor.a", "sensor.b"])

    assert "sensor.a" in payloads
    assert "sensor.b" in payloads
    # Simple values are returned as floats
    assert isinstance(payloads["sensor.a"], float)
    assert isinstance(payloads["sensor.b"], float)
    assert payloads["sensor.a"] == 1.0
    assert payloads["sensor.b"] == 0.5


async def test_load_sensors_excludes_unavailable() -> None:
    """Load sensors excludes sensors that are unavailable or missing."""

    sm = FakeStateMachine(
        {
            "sensor.a": FakeEntityState(
                entity_id="sensor.a",
                state="1",
                attributes={"device_class": "power", "unit_of_measurement": "kW"},
            ),
            "sensor.unavailable": FakeEntityState(
                entity_id="sensor.unavailable",
                state="unavailable",
                attributes={},
            ),
        }
    )

    payloads = load_sensors(sm, ["sensor.a", "sensor.unavailable", "sensor.missing"])

    assert "sensor.a" in payloads
    assert "sensor.unavailable" not in payloads
    assert "sensor.missing" not in payloads
    assert len(payloads) == 1
