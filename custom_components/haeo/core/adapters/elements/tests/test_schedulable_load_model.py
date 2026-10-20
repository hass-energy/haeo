"""Tests for schedulable load element model mapping and optimization behavior."""

import numpy as np
from numpy.typing import NDArray
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.adapters.elements.schedulable_load import (
    SCHEDULABLE_ENERGY_MISSED,
    SCHEDULABLE_LOAD_DEVICE,
    SCHEDULABLE_POWER,
    SCHEDULABLE_START,
    adapter,
)
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.config_loader import load_element_config
from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
    SchedulableLoadElementConfig,
)
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.schedulable_load import (
    SchedulableLoadConfigData,
    SchedulableLoadConfigSchema,
)


def _window(n_periods: int, start: int, end: int) -> dict[str, NDArray[np.float64]]:
    """Build the loaded window inputs for one window over periods ``start`` to ``end``.

    A window starting before the horizon is open at its start, so it does not start.
    """
    in_window = np.zeros(n_periods)
    in_window[max(start, 0) : end] = 1.0
    window_start = np.zeros(n_periods + 1)
    if start > 0:
        window_start[start] = 1.0
    return {"in_window": in_window, "window_start": window_start}


def _config(**schedule: object) -> SchedulableLoadConfigData:
    """Build a 1 kW, one-hour schedulable load whose window is open over periods 0-2."""
    config: dict[str, object] = {
        "element_type": ElementType.SCHEDULABLE_LOAD,
        "name": "dishwasher",
        "connection": as_connection_target("home"),
        "schedule": {**_window(4, -1, 3), **schedule},
        "profile": {"power": 1.0, "duration": 1.0},
        "pricing": {"deficit_price": np.full(5, 10.0)},
    }
    return config  # type: ignore[return-value]  # constructed to match SchedulableLoadConfigData


def _load(config: SchedulableLoadConfigData) -> SchedulableLoadElementConfig:
    """Return the schedulable load model element the adapter builds."""
    load, _connection = adapter.model_elements(config)
    assert load["element_type"] == MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD
    return load


def test_model_elements_structure() -> None:
    """The adapter creates the load from the window inputs and the profile, plus its connection."""
    load, connection = adapter.model_elements(_config())

    assert load["element_type"] == MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD
    np.testing.assert_allclose(load["in_window"], [1.0, 1.0, 1.0, 0.0])
    np.testing.assert_allclose(load["window_start"], [0.0] * 5)
    np.testing.assert_allclose(load["profile_power"], [1.0])
    np.testing.assert_allclose(load["profile_duration"], [1.0])
    np.testing.assert_allclose(load["deficit_price"], [10.0] * 5)
    assert load.get("integer_mode") == "first"
    assert connection["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION
    assert connection["source"] == "home"
    assert connection["target"] == "dishwasher"


def test_integer_mode_comes_from_advanced_section() -> None:
    """The advanced section selects which starts are integer."""
    config = _config()
    config["advanced"] = {"integer_mode": "all"}

    assert _load(config).get("integer_mode") == "all"


@pytest.mark.parametrize(
    ("schedule", "elapsed", "window_started"),
    [
        pytest.param({}, None, False, id="no_running_sensor_or_meter"),
        pytest.param({"running": 0.0}, None, False, id="idle_without_meter"),
        pytest.param({"running": 1.0}, 0.0, True, id="running_without_meter_just_started"),
        pytest.param({"running": 1.0, "energy_meter": 0.25}, 0.25, True, id="running_quarter_through"),
        pytest.param({"running": 1.0, "energy_meter": 2.0}, 1.0, True, id="running_past_the_profile"),
        pytest.param({"running": 0.0, "energy_meter": 0.9}, None, True, id="idle_after_its_run"),
        pytest.param({"running": 0.0, "energy_meter": 0.1}, None, False, id="idle_with_standby_use"),
        pytest.param({"energy_meter": 0.9}, None, True, id="meter_alone_marks_the_run_done"),
    ],
)
def test_running_sensor_and_meter_set_committed_run_and_window_state(
    schedule: dict[str, float],
    elapsed: float | None,
    window_started: bool,
) -> None:
    """The meter's rise since the window opened is how far through its run the load is."""
    load = _load(_config(**schedule))

    assert load.get("elapsed") == (None if elapsed is None else pytest.approx(elapsed))
    assert load.get("window_started") is window_started


def test_progress_follows_a_multi_step_profile() -> None:
    """Energy used maps to time through each profile step at that step's power."""
    config = _config(running=1.0, energy_meter=2.5)
    config["profile"] = {"power": 2.0, "duration": 2.0}

    assert _load(config).get("elapsed") == pytest.approx(1.25)


def test_no_window_open_means_no_started_window() -> None:
    """A run never satisfies a window that is not open at the horizon start."""
    config = _config(running=1.0, energy_meter=0.5)
    config["schedule"].update(_window(4, 2, 4))  # type: ignore[typeddict-item]  # the window inputs are ScheduleData keys

    load = _load(config)

    assert load.get("window_started") is False
    assert load.get("elapsed") == pytest.approx(0.5)


def _solve(config: SchedulableLoadConfigData, grid_price: list[float]) -> Network:
    """Build and solve a grid + schedulable load network."""
    n = len(grid_price)
    network = Network(name="test", periods=np.array([1.0] * n))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "home", "is_source": False, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "grid_to_home",
            "source": "grid",
            "target": "home",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": np.array(grid_price)}},
        }
    )
    for element in adapter.model_elements(config):
        if element["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION:
            element["tags"] = {1}
        network.add(element)
    network.optimize()
    return network


def test_outputs_report_power_start_and_missed_energy() -> None:
    """The device reports the planned power, the start schedule, and missed energy."""
    config = _config()
    network = _solve(config, grid_price=[0.3, 0.1, 0.2, 0.1])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("dishwasher", model_outputs, config=config)[SCHEDULABLE_LOAD_DEVICE]

    np.testing.assert_allclose(outputs[SCHEDULABLE_POWER].values, [0.0, 1.0, 0.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(outputs[SCHEDULABLE_START].values, [0.0, 1.0, 0.0, 0.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(outputs[SCHEDULABLE_ENERGY_MISSED].values, [0.0] * 5, atol=1e-9)


def test_run_in_progress_finishes_before_anything_else() -> None:
    """A run in progress finishes its remaining profile from the horizon start."""
    config = _config(running=1.0, energy_meter=0.5)
    network = _solve(config, grid_price=[0.3, 0.1, 0.2, 0.1])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("dishwasher", model_outputs, config=config)[SCHEDULABLE_LOAD_DEVICE]

    np.testing.assert_allclose(outputs[SCHEDULABLE_POWER].values, [0.5, 0.0, 0.0, 0.0], atol=1e-9)


def _event(start: str, end: str) -> dict[str, object]:
    return {"start": start, "end": end, "summary": "Dishwasher", "location": None, "description": None}


def _schema(**schedule: object) -> SchedulableLoadConfigSchema:
    return {
        "element_type": ElementType.SCHEDULABLE_LOAD,
        "name": "dishwasher",
        "connection": as_connection_target("home"),
        "schedule": {"window_calendar": as_entity_value(["calendar.dishwasher"]), **schedule},  # type: ignore[typeddict-item]  # loose test overrides
        "profile": {"power": as_constant_value(1.8), "duration": as_constant_value(2.0)},
        "pricing": {"deficit_price": as_constant_value(10.0)},
    }


def test_calendar_events_load_as_windows() -> None:
    """Every calendar event is a window, whatever its text says."""
    event = _event("1970-01-01T01:00:00+00:00", "1970-01-01T03:00:00+00:00")
    states = {
        "calendar.dishwasher": FakeEntityState("calendar.dishwasher", "off", {CALENDAR_EVENTS_ATTRIBUTE: [event]})
    }

    loaded = load_element_config(
        "dishwasher", _schema(), FakeStateMachine(states), (0.0, 3600.0, 7200.0, 10800.0, 14400.0)
    )
    assert loaded["element_type"] == ElementType.SCHEDULABLE_LOAD
    load = _load(loaded)

    np.testing.assert_allclose(load["in_window"], [0.0, 1.0, 1.0, 0.0])
    np.testing.assert_allclose(load["window_start"], [0.0, 1.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(load["profile_duration"], [2.0])


def test_energy_meter_rise_sets_progress_through_the_run() -> None:
    """A running load's meter rise since the window opened, converted to kWh, sets how far through its run it is."""
    event = _event("1970-01-01T00:00:00+00:00", "1970-01-01T04:00:00+00:00")
    meter_attributes = {
        "unit_of_measurement": "Wh",
        "device_class": "energy",
        "state_class": "total_increasing",
        METER_TOTALS_ATTRIBUTE: [(-300.0, 9000.0), (0.0, 10000.0), (1800.0, 10900.0)],
    }
    states = {
        "calendar.dishwasher": FakeEntityState("calendar.dishwasher", "on", {CALENDAR_EVENTS_ATTRIBUTE: [event]}),
        "sensor.dishwasher_energy": FakeEntityState("sensor.dishwasher_energy", "900", meter_attributes),
        "binary_sensor.dishwasher_running": FakeEntityState("binary_sensor.dishwasher_running", "on", {}),
    }
    config = _schema(
        running=as_entity_value(["binary_sensor.dishwasher_running"]),
        energy_meter=as_entity_value(["sensor.dishwasher_energy"]),
    )

    loaded = load_element_config("dishwasher", config, FakeStateMachine(states), (1800.0, 3600.0, 7200.0, 10800.0))
    assert loaded["element_type"] == ElementType.SCHEDULABLE_LOAD
    load = _load(loaded)

    # 0.9 kWh of a 1.8 kW run is half an hour in.
    assert load.get("elapsed") == pytest.approx(0.5)
    assert load.get("window_started") is True
