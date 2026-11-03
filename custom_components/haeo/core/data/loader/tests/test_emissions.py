"""Tests for loading a grid emissions intensity sensor."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.emissions import load_emissions_intensity
from custom_components.haeo.core.data.util.input_values import InputError

START = datetime(2026, 11, 3, 6, tzinfo=UTC)
TIMES = [START.timestamp(), (START + timedelta(hours=1)).timestamp(), (START + timedelta(hours=2)).timestamp()]


def _sensor(state: str, unit: str | None, **attributes: object) -> FakeStateMachine:
    return FakeStateMachine(
        {
            "sensor.intensity": FakeEntityState(
                entity_id="sensor.intensity",
                state=state,
                attributes={**({} if unit is None else {"unit_of_measurement": unit}), **attributes},
            )
        }
    )


@pytest.mark.parametrize(
    ("state", "unit", "expected"),
    [
        pytest.param("600", "gCO2eq/kWh", 0.6, id="grams"),
        pytest.param("0.6", "kg/kWh", 0.6, id="kilograms"),
        pytest.param("0.6", "tCO2e/MWh", 0.6, id="tonnes_per_megawatt_hour"),
        pytest.param("600", "kgCO2-e/MWh", 0.6, id="kilograms_per_megawatt_hour"),
    ],
)
def test_reading_holds_for_every_period_in_kilograms_per_kilowatt_hour(state: str, unit: str, expected: float) -> None:
    """A reading without a forecast holds for the whole plan, converted to kg/kWh."""
    np.testing.assert_allclose(
        load_emissions_intensity(_sensor(state, unit), "sensor.intensity", TIMES), [expected] * 2
    )


def test_forecast_is_averaged_over_each_period() -> None:
    """A forecast is averaged over each period, as forecasts of prices are."""
    forecast = [
        {"time": START.isoformat(), "value": 800},
        {"time": (START + timedelta(hours=1)).isoformat(), "value": 400},
        {"time": (START + timedelta(hours=2)).isoformat(), "value": 400},
    ]
    sm = _sensor("800", "gCO2eq/kWh", forecast=forecast)

    np.testing.assert_allclose(load_emissions_intensity(sm, "sensor.intensity", TIMES), [0.6, 0.4])


@pytest.mark.parametrize(
    ("sm", "key"),
    [
        pytest.param(FakeStateMachine({}), "emissions_intensity_unavailable", id="missing"),
        pytest.param(_sensor("unavailable", "gCO2eq/kWh"), "emissions_intensity_unavailable", id="no_reading"),
        pytest.param(_sensor("40", "%"), "emissions_intensity_unit", id="percent"),
        pytest.param(_sensor("600", None), "emissions_intensity_unit", id="no_unit"),
    ],
)
def test_sensor_without_an_intensity_is_rejected(sm: FakeStateMachine, key: str) -> None:
    """A sensor that is missing, has no reading, or is not a mass per energy cannot be used."""
    with pytest.raises(InputError) as error:
        load_emissions_intensity(sm, "sensor.intensity", TIMES)

    assert error.value.translation_key == key
