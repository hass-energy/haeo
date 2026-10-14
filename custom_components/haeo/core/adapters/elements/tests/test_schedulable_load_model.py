"""Tests for schedulable load element model mapping and optimization behavior."""

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.schedulable_load import (
    SCHEDULABLE_ENERGY_MISSED,
    SCHEDULABLE_LOAD_DEVICE,
    SCHEDULABLE_POWER,
    SCHEDULABLE_START,
    adapter,
)
from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
    SchedulableLoadElementConfig,
)
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.schedulable_load import SchedulableLoadConfigData

_HORIZON_START = 10_000.0
# The window in _config opened half an hour before the horizon start.
_OPEN_SINCE = _HORIZON_START - 1800.0


def _boundary_data(n_periods: int, events: list[tuple[int, int]], open_since: float | None) -> CalendarBoundaryData:
    """Build presence calendar boundary data from period-aligned (start, end) events."""
    span = np.zeros(n_periods + 1)
    edge_start = np.zeros(n_periods + 1)
    edge_end = np.zeros(n_periods + 1)
    for start, end in events:
        span[start:end] += 1.0
        edge_start[start] += 1.0
        if end <= n_periods:
            edge_end[end] += 1.0
    return CalendarBoundaryData(
        presence=(span > 0).astype(np.float64),
        value_span=span,
        value_edge_start=edge_start,
        value_edge_end=edge_end,
        open_since=open_since,
        horizon_start=_HORIZON_START,
    )


def _config(**schedule: object) -> SchedulableLoadConfigData:
    """Build a 1 kW, one-hour schedulable load with a window open over periods 0-2."""
    config: dict[str, object] = {
        "element_type": ElementType.SCHEDULABLE_LOAD,
        "name": "dishwasher",
        "connection": as_connection_target("home"),
        "schedule": {"window_calendar": _boundary_data(4, [(0, 3)], open_since=_OPEN_SINCE), **schedule},
        "profile": {"power": 1.0, "duration": 1.0},
        "pricing": {"deficit_price": 10.0},
    }
    return config  # type: ignore[return-value]  # constructed to match SchedulableLoadConfigData


def _load(config: SchedulableLoadConfigData) -> SchedulableLoadElementConfig:
    """Return the schedulable load model element the adapter builds."""
    load, _connection = adapter.model_elements(config)
    assert load["element_type"] == MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD
    return load


def test_model_elements_structure() -> None:
    """The adapter creates the load from the calendar windows and the profile, plus its connection."""
    config = _config()

    load, connection = adapter.model_elements(config)

    assert load["element_type"] == MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD
    np.testing.assert_allclose(load["in_window"], [1.0, 1.0, 1.0, 0.0])
    np.testing.assert_allclose(load["window_start"], [0.0, 0.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(load["profile_power"], [1.0])
    np.testing.assert_allclose(load["profile_duration"], [1.0])
    assert load["deficit_price"] == pytest.approx(10.0)
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
        pytest.param({"running": 0.0}, None, False, id="idle_without_history"),
        pytest.param({"running": 1.0}, 0.0, True, id="running_without_history_just_started"),
        pytest.param(
            {"running": 1.0, "running_off_periods": [(0.0, _HORIZON_START - 900.0)]},
            0.25,
            True,
            id="running_since_window_opened",
        ),
        pytest.param(
            {"running": 1.0, "running_off_periods": [(0.0, _HORIZON_START - 3600.0)]},
            1.0,
            False,
            id="running_since_before_window",
        ),
        pytest.param(
            {"running": 1.0, "running_off_periods": [(0.0, _HORIZON_START - 3600.0), (_HORIZON_START - 60.0, None)]},
            0.0,
            True,
            id="running_while_history_still_off_just_started",
        ),
        pytest.param(
            {"running": 0.0, "running_off_periods": [(0.0, _HORIZON_START - 900.0), (_HORIZON_START - 300.0, None)]},
            None,
            True,
            id="finished_inside_window",
        ),
        pytest.param(
            {"running": 0.0, "running_off_periods": [(0.0, _HORIZON_START - 3600.0), (_HORIZON_START - 2000.0, None)]},
            None,
            False,
            id="finished_before_window",
        ),
    ],
)
def test_running_sensor_sets_committed_run_and_window_state(
    schedule: dict[str, object],
    elapsed: float | None,
    window_started: bool,
) -> None:
    """The running sensor commits a run in progress and marks a window whose run already started."""
    load = _load(_config(**schedule))

    assert load.get("elapsed") == (None if elapsed is None else pytest.approx(elapsed))
    assert load.get("window_started") is window_started


def test_no_window_open_means_no_started_window() -> None:
    """A run started while no window is open never satisfies a later window."""
    config = _config(running=0.0, running_off_periods=[(0.0, _HORIZON_START - 900.0), (_HORIZON_START - 300.0, None)])
    config["schedule"]["window_calendar"] = _boundary_data(4, [(2, 4)], open_since=None)

    assert _load(config).get("window_started") is False


def test_negative_inputs_are_clamped() -> None:
    """Negative entity readings never reach the model as negative profile values or prices."""
    config = _config()
    config["profile"] = {"power": -1.0, "duration": -1.0}
    config["pricing"] = {"deficit_price": -5.0}

    load = _load(config)

    np.testing.assert_allclose(load["profile_power"], [0.0])
    np.testing.assert_allclose(load["profile_duration"], [0.0])
    assert load["deficit_price"] == pytest.approx(0.0)


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
    config = _config(running=1.0, running_off_periods=[(0.0, _HORIZON_START - 1800.0)])
    network = _solve(config, grid_price=[0.3, 0.1, 0.2, 0.1])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("dishwasher", model_outputs, config=config)[SCHEDULABLE_LOAD_DEVICE]

    np.testing.assert_allclose(outputs[SCHEDULABLE_POWER].values, [0.5, 0.0, 0.0, 0.0], atol=1e-9)
