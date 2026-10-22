"""Unit tests for sensor payload helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.extractors import ExtractedData
from custom_components.haeo.core.data.loader.sensor_loader import load_readings, load_sensor, load_sensors
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


def test_load_sensor_reads_naive_forecast_times_in_the_state_machine_time_zone() -> None:
    """Forecast times without a time zone are local times in the state machine's time zone."""

    sm = FakeStateMachine(
        {
            "sensor.forecast": FakeEntityState(
                entity_id="sensor.forecast",
                state="1.0",
                attributes={
                    "forecast": [
                        {"time": "2025-07-01T12:00:00", "value": 1.0},
                        {"time": "2025-07-01T12:30:00", "value": 2.0},
                    ],
                    "device_class": "power",
                    "unit_of_measurement": "kW",
                },
            )
        },
        time_zone=ZoneInfo("Australia/Adelaide"),
    )

    payload = load_sensor(sm, "sensor.forecast")

    # Adelaide is UTC+09:30 in July
    assert payload == [
        (datetime(2025, 7, 1, 2, 30, tzinfo=UTC).timestamp(), 1.0),
        (datetime(2025, 7, 1, 3, 0, tzinfo=UTC).timestamp(), 2.0),
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


def test_load_readings_reads_each_state_in_base_units() -> None:
    """Readings are the sensors' states converted to base units, even for a sensor carrying a forecast."""
    forecast = [{"time": "2025-07-01T12:00:00+00:00", "value": 9000.0}]
    sm = FakeStateMachine(
        {
            "sensor.a": FakeEntityState(
                entity_id="sensor.a",
                state="1500",
                attributes={"device_class": "power", "unit_of_measurement": "W", "forecast": forecast},
            ),
            "sensor.b": FakeEntityState(entity_id="sensor.b", state="on", attributes={}),
        }
    )

    assert load_readings(sm, ["sensor.a", "sensor.b"]) == {"sensor.a": 1.5, "sensor.b": 1.0}


@pytest.mark.parametrize(
    "entity_ids",
    [
        pytest.param([], id="no_sensors"),
        pytest.param(["sensor.a", "sensor.missing"], id="missing_sensor"),
        pytest.param(["sensor.a", "sensor.unknown"], id="sensor_without_a_reading"),
        pytest.param(["calendar.trips"], id="calendar"),
        pytest.param(["sensor.nan"], id="nan"),
        pytest.param(["sensor.inf"], id="infinity"),
    ],
)
def test_load_readings_is_unavailable_without_every_reading(entity_ids: list[str]) -> None:
    """One sensor without a reading makes the whole set unavailable."""
    sm = FakeStateMachine(
        {
            "sensor.a": FakeEntityState(entity_id="sensor.a", state="1", attributes={}),
            "sensor.unknown": FakeEntityState(entity_id="sensor.unknown", state="unknown", attributes={}),
            "calendar.trips": FakeEntityState(entity_id="calendar.trips", state="on", attributes={}),
            "sensor.nan": FakeEntityState(entity_id="sensor.nan", state="nan", attributes={}),
            "sensor.inf": FakeEntityState(entity_id="sensor.inf", state="-Infinity", attributes={}),
        }
    )

    assert load_readings(sm, entity_ids) is None


def test_load_readings_rejects_a_unit_the_input_cannot_use() -> None:
    """A reading in a unit that does not convert to the input's unit is rejected."""
    sm = FakeStateMachine(
        {"sensor.t": FakeEntityState(entity_id="sensor.t", state="20", attributes={"unit_of_measurement": "°C"})}
    )

    with pytest.raises(InputError):
        load_readings(sm, ["sensor.t"], output_type=OutputType.POWER)
