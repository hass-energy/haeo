"""Tests for the time series loader's availability check."""

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.time_series_loader import TimeSeriesLoader
from custom_components.haeo.core.schema import as_entity_value

_POWER = {"device_class": "power", "unit_of_measurement": "kW"}

_SM = FakeStateMachine(
    {
        "sensor.a": FakeEntityState(entity_id="sensor.a", state="1", attributes=_POWER),
        "sensor.b": FakeEntityState(entity_id="sensor.b", state="2", attributes=_POWER),
        "sensor.unavailable": FakeEntityState(entity_id="sensor.unavailable", state="unavailable", attributes={}),
    }
)


@pytest.mark.parametrize(
    ("entity_ids", "expected"),
    [
        pytest.param(["sensor.a", "sensor.b"], True, id="all_available"),
        pytest.param(["sensor.a", "sensor.unavailable"], False, id="one_unavailable"),
        pytest.param(["sensor.a", "sensor.missing"], False, id="one_missing"),
        pytest.param([], False, id="no_sensors"),
    ],
)
def test_available_requires_every_sensor(entity_ids: list[str], *, expected: bool) -> None:
    """The loader is available only when every referenced sensor supplies data."""
    assert TimeSeriesLoader().available(sm=_SM, value=as_entity_value(entity_ids)) is expected


def test_available_rejects_invalid_value() -> None:
    """A value that is not an entity value is a coding error."""
    with pytest.raises(TypeError):
        TimeSeriesLoader().available(sm=_SM, value=object())  # type: ignore[arg-type]  # deliberate non-EntityValue
