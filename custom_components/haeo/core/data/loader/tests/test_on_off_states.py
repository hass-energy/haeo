"""Tests for reading entities whose states are words as on or off."""

from zoneinfo import ZoneInfo

import numpy as np
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.config_loader import load_element_config
from custom_components.haeo.core.data.loader.on_off_states import OnOffStateMachine, on_off_state
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import EvConfigSchema

CHARGER = "sensor.charger_status"


@pytest.mark.parametrize(
    ("state", "on_states", "off_states", "expected"),
    [
        pytest.param("Charging", ["Charging"], [], "on", id="listed_on"),
        pytest.param("Idle", [], ["Idle"], "off", id="listed_off"),
        pytest.param("Occupied", [], ["Idle"], "on", id="others_on_when_only_off_listed"),
        pytest.param("Idle", ["Charging"], [], "off", id="others_off_when_only_on_listed"),
        pytest.param("Fault", ["Charging"], ["Idle"], "unknown", id="neither_list_has_no_reading"),
        pytest.param("off", [], ["Idle"], "off", id="binary_states_keep_their_reading"),
        pytest.param("on", [], ["on"], "off", id="listed_binary_states_follow_the_list"),
        pytest.param("unavailable", [], ["Idle"], "unavailable", id="no_reading_stays"),
    ],
)
def test_on_off_state(state: str, on_states: list[str], off_states: list[str], expected: str) -> None:
    """States read as on or off from the lists; with one list empty every other state is the opposite."""
    assert on_off_state(state, on_states, off_states) == expected


def test_state_machine_reads_only_the_inputs_entities() -> None:
    """Only the input's entities are read as on or off, and captured states keep their words."""
    states = {
        CHARGER: FakeEntityState(CHARGER, "Idle", {}),
        "sensor.other": FakeEntityState("sensor.other", "Idle", {}),
    }
    sm = OnOffStateMachine(FakeStateMachine(states), as_entity_value([CHARGER], off_states=["Idle"]))

    charger = sm.get(CHARGER)
    other = sm.get("sensor.other")
    assert charger is not None
    assert other is not None
    assert charger.state == "off"
    assert charger.as_dict()["state"] == "off"
    assert other.state == "Idle"
    assert states[CHARGER].state == "Idle"


@pytest.mark.parametrize(
    ("charger_state", "expected"),
    [
        pytest.param("Idle", 0.0, id="unplugged"),
        pytest.param("Preparing Insulation", 1.0, id="any_other_state_plugged_in"),
    ],
)
def test_an_ev_reads_a_charger_reporting_words(charger_state: str, expected: float) -> None:
    """An EV whose plugged-in input lists Idle as off reads every other charger state as plugged in."""
    states = {
        CHARGER: FakeEntityState(CHARGER, charger_state, {}),
        "sensor.soc": FakeEntityState("sensor.soc", "50", {"unit_of_measurement": "%"}),
    }
    config: EvConfigSchema = {
        "element_type": ElementType.EV,
        "name": "ev",
        "connection": as_connection_target("home"),
        "vehicle": {
            "capacity": as_constant_value(50.0),
            "energy_per_distance": as_constant_value(0.2),
            "current_soc": as_entity_value(["sensor.soc"]),
        },
        "charging": {
            "max_charge_rate": as_constant_value(7.0),
            "connected": as_entity_value([CHARGER], off_states=["Idle"]),
        },
        "public_charging": {"public_charging_price": as_constant_value(0.6)},
        "efficiency": {},
        "advanced": {"charge_limit_cost": as_constant_value(100.0)},
    }

    loaded = load_element_config("ev", config, FakeStateMachine(states), (0.0, 3600.0, 7200.0))
    assert loaded["element_type"] == ElementType.EV

    np.testing.assert_allclose(loaded["charging"]["connected"], [expected, expected])


def test_state_machine_reads_in_the_base_time_zone() -> None:
    """Reading entities as on or off keeps the base state machine's time zone."""
    adelaide = ZoneInfo("Australia/Adelaide")

    sm = OnOffStateMachine(FakeStateMachine({}, time_zone=adelaide), as_entity_value([CHARGER], off_states=["Idle"]))

    assert sm.time_zone is adelaide
