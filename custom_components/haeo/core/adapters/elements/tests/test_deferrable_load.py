"""Tests for deferrable load windows seeded by the energy meter and loaded from captured states."""

import numpy as np
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.adapters.elements.deferrable_load import adapter
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.config_loader import load_element_config
from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
    DeferrableLoadElementConfig,
)
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.deferrable_load import (
    DeferrableLoadConfigData,
    DeferrableLoadConfigSchema,
    ScheduleData,
)


def _open_window_config(metered: float | None) -> DeferrableLoadConfigData:
    """Build a pump whose 6 kWh window is already open at the horizon start and due at boundary 3."""
    schedule: ScheduleData = {
        "in_window": np.array([1.0, 1.0, 1.0, 0.0]),
        "window_start": np.zeros(5),
        "opened": np.array([6.0, 0.0, 0.0, 0.0, 0.0]),
        "due": np.array([0.0, 0.0, 0.0, 6.0, 0.0]),
    }
    if metered is not None:
        schedule["energy_meter"] = metered
    return DeferrableLoadConfigData(
        element_type=ElementType.DEFERRABLE_LOAD,
        name="pump",
        connection=as_connection_target("home"),
        schedule=schedule,
        pricing={"deficit_price": np.full(5, 10.0), "overage_price": np.zeros(5)},
        power={"max_power": 10.0},
    )


def _load(config: DeferrableLoadConfigData) -> DeferrableLoadElementConfig:
    """Return the deferrable load model element the adapter builds."""
    load, _connection = adapter.model_elements(config)
    assert load["element_type"] == MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD
    return load


def _solve(config: DeferrableLoadConfigData, grid_price: list[float]) -> Network:
    """Build and solve a grid + deferrable load network."""
    n = len(grid_price)
    network = Network(name="test", periods=np.array([1.0] * n))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "home", "is_source": False, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add(
        {
            "element_type": "connection",
            "name": "grid:import",
            "source": "grid",
            "target": "home",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array(grid_price)},
            },
        }
    )
    # Policy compilation assigns tags in production; default them here.
    for element in adapter.model_elements(config):
        if element["element_type"] == "connection":
            element.setdefault("tags", {1})  # type: ignore[typeddict-unknown-key]  # spec allows tags
        network.add(element)
    network.optimize()
    return network


@pytest.mark.parametrize(
    ("metered", "expected_initial", "expected_new"),
    [
        pytest.param(None, 0.0, 6.0, id="unconfigured"),
        pytest.param(4.0, 4.0, 2.0, id="under_target"),
        pytest.param(10.0, 10.0, 0.0, id="over_target"),
    ],
)
def test_energy_since_the_window_opened_seeds_it(
    metered: float | None, expected_initial: float, expected_new: float
) -> None:
    """Energy the meter counted since the open window started seeds it; only the remainder is planned."""
    network = _solve(_open_window_config(metered), grid_price=[0.1, 0.1, 0.1, 0.1])

    delivered = network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values
    assert delivered[0] == pytest.approx(expected_initial)
    assert delivered[3] - delivered[0] == pytest.approx(expected_new)
    shortfall = network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values
    assert shortfall[3] == pytest.approx(0.0)


def test_config_loads_from_a_captured_calendar_state() -> None:
    """A deferrable load loaded from a calendar state carrying events reaches the model as its windows."""
    event = {
        "start": "1970-01-01T02:00:00+00:00",
        "end": "1970-01-01T03:00:00+00:00",
        "summary": "Pool pump",
        "location": "6 kWh",
        "description": None,
    }
    states = {"calendar.pool_pump": FakeEntityState("calendar.pool_pump", "off", {CALENDAR_EVENTS_ATTRIBUTE: [event]})}
    config: DeferrableLoadConfigSchema = {
        "element_type": ElementType.DEFERRABLE_LOAD,
        "name": "pump",
        "connection": as_connection_target("home"),
        "schedule": {"window_calendar": as_entity_value(["calendar.pool_pump"])},
        "pricing": {"deficit_price": as_constant_value(10.0), "overage_price": as_constant_value(0.0)},
    }

    loaded = load_element_config("pump", config, FakeStateMachine(states), (0.0, 3600.0, 7200.0, 10800.0, 14400.0))
    assert loaded["element_type"] == ElementType.DEFERRABLE_LOAD
    load = _load(loaded)

    np.testing.assert_allclose(load["in_window"], [0.0, 0.0, 1.0, 0.0])
    np.testing.assert_allclose(load["window_start"], [0.0, 0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(load["opened"], [0.0, 0.0, 6.0, 0.0, 0.0])
    np.testing.assert_allclose(load["due"], [0.0, 0.0, 0.0, 6.0, 0.0])
    np.testing.assert_allclose(load["deficit_price"], [10.0] * 5)


def test_energy_meter_credits_the_open_window_with_its_rise() -> None:
    """A meter's rise since the open window started, converted to kWh, seeds that window."""
    event = {
        "start": "1970-01-01T00:00:00+00:00",
        "end": "1970-01-01T03:00:00+00:00",
        "summary": "Pool pump",
        "location": "6 kWh",
        "description": None,
    }
    meter_attributes = {
        "unit_of_measurement": "Wh",
        "device_class": "energy",
        "state_class": "total_increasing",
        METER_TOTALS_ATTRIBUTE: [(-300.0, 9000.0), (0.0, 10000.0), (1800.0, 12500.0)],
    }
    states = {
        "calendar.pool_pump": FakeEntityState("calendar.pool_pump", "on", {CALENDAR_EVENTS_ATTRIBUTE: [event]}),
        "sensor.pool_pump_energy": FakeEntityState("sensor.pool_pump_energy", "500", meter_attributes),
    }
    config: DeferrableLoadConfigSchema = {
        "element_type": ElementType.DEFERRABLE_LOAD,
        "name": "pump",
        "connection": as_connection_target("home"),
        "schedule": {
            "window_calendar": as_entity_value(["calendar.pool_pump"]),
            "energy_meter": as_entity_value(["sensor.pool_pump_energy"]),
        },
        "pricing": {"deficit_price": as_constant_value(10.0), "overage_price": as_constant_value(0.0)},
    }

    loaded = load_element_config("pump", config, FakeStateMachine(states), (1800.0, 3600.0, 7200.0, 10800.0))
    assert loaded["element_type"] == ElementType.DEFERRABLE_LOAD

    assert _load(loaded).get("initial_energy") == pytest.approx(2.5)
