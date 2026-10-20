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
from custom_components.haeo.core.data.loader.switch import ON_PERIODS_ATTRIBUTE
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
        pytest.param({}, None, False, id="no_running_sensor"),
        pytest.param({"running": 0.0}, None, False, id="not_switched_on_in_the_window"),
        pytest.param({"running": 0.25}, 0.25, True, id="switched_on_a_quarter_hour_ago"),
        pytest.param({"running": 2.0}, 2.0, True, id="switched_on_longer_ago_than_a_run"),
    ],
)
def test_running_sensor_sets_committed_run_and_window_state(
    schedule: dict[str, float],
    elapsed: float | None,
    window_started: bool,
) -> None:
    """How long ago the load first switched on in the open window is how far through its run it is."""
    load = _load(_config(**schedule))

    assert load.get("elapsed") == (None if elapsed is None else pytest.approx(elapsed))
    assert load.get("window_started") is window_started


def test_no_window_open_means_no_started_window() -> None:
    """A switch-on never counts when no window is open at the horizon start."""
    config = _config(running=0.5)
    config["schedule"].update(_window(4, 2, 4))  # type: ignore[typeddict-item]  # the window inputs are ScheduleData keys

    load = _load(config)

    assert load.get("window_started") is False
    assert load.get("elapsed") is None


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
    config = _config(running=0.5)
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


def test_running_sensor_loads_how_long_ago_it_first_switched_on() -> None:
    """The running sensor's on periods and the window's events resolve to the hours since its first switch-on."""
    event = _event("1970-01-01T00:00:00+00:00", "1970-01-01T04:00:00+00:00")
    states = {
        "calendar.dishwasher": FakeEntityState("calendar.dishwasher", "on", {CALENDAR_EVENTS_ATTRIBUTE: [event]}),
        "binary_sensor.dishwasher_running": FakeEntityState(
            "binary_sensor.dishwasher_running", "on", {ON_PERIODS_ATTRIBUTE: [(-600.0, 300.0), (900.0, None)]}
        ),
    }
    config = _schema(running=as_entity_value(["binary_sensor.dishwasher_running"]))

    loaded = load_element_config("dishwasher", config, FakeStateMachine(states), (2700.0, 3600.0, 7200.0, 10800.0))
    assert loaded["element_type"] == ElementType.SCHEDULABLE_LOAD
    load = _load(loaded)

    # On before the window opened, so the run counts from its switch-on at -600 s, 55 minutes before the horizon.
    assert load.get("elapsed") == pytest.approx(55.0 / 60.0)
    assert load.get("window_started") is True
