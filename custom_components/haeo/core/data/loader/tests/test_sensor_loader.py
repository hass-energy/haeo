"""Unit tests for sensor payload helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.extractors import ExtractedData
from custom_components.haeo.core.data.loader.sensor_loader import load_sensor, load_sensors
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.model.const import OutputType


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

    assert payloads == {"sensor.a": 1.0, "sensor.b": 0.5}


@pytest.mark.parametrize("failing_id", ["sensor.unavailable", "sensor.missing"])
async def test_load_sensors_is_unavailable_when_any_sensor_is(failing_id: str) -> None:
    """One unavailable or missing sensor makes the whole set unavailable instead of being left out."""

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

    assert load_sensors(sm, ["sensor.a", failing_id]) is None


def test_load_sensors_reports_an_unusable_unit_after_an_unavailable_sensor() -> None:
    """A sensor in an unusable unit is reported even when an earlier sensor is unavailable."""

    sm = FakeStateMachine(
        {
            "sensor.unavailable": FakeEntityState(entity_id="sensor.unavailable", state="unavailable", attributes={}),
            "sensor.temperature": FakeEntityState(
                entity_id="sensor.temperature",
                state="20",
                attributes={"device_class": "temperature", "unit_of_measurement": "°C"},
            ),
        }
    )

    with pytest.raises(InputError):
        load_sensors(sm, ["sensor.unavailable", "sensor.temperature"], output_type=OutputType.POWER)


def test_load_sensors_is_unavailable_without_entity_ids() -> None:
    """No entity IDs means no data, not an empty set of payloads."""

    assert load_sensors(FakeStateMachine({}), []) is None
