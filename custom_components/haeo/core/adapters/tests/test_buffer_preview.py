"""Tests for planning with a buffer as its form has it."""

from typing import Final

import numpy as np
import pytest

from custom_components.haeo.core.adapters.buffer_preview import (
    buffer_config,
    preview_buffer,
    storage_state_of_charge,
    unused_name,
)
from custom_components.haeo.core.adapters.network_builder import build_network
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_none_value
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.buffer import BufferConfigData
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData
from custom_components.haeo.core.schema.elements.node import NodeConfigData

N_PERIODS: Final = 4
HOURS: Final = [3600.0] * N_PERIODS

FORM: Final[dict[str, object]] = {
    "name": "Outage",
    "kind": "reserve",
    "participants": {"loads": ["House"], "generation": [], "storage": ["Battery"]},
    "requirement": {"window": as_constant_value(2.0), "level": as_none_value()},
    "pricing": {"shortfall_cost": as_constant_value(10.0)},
}


def _hub() -> dict[str, ElementConfigData]:
    """Return a battery at half charge, a house drawing 1 kW, and a grid paying well for exports in the first hour."""
    bus = as_connection_target("Bus")
    node: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "Bus",
        "role": {"is_source": False, "is_sink": False},
    }
    battery = BatteryConfigData(
        element_type=ElementType.BATTERY,
        name="Battery",
        connection=bus,
        storage={"capacity": np.full(N_PERIODS + 1, 10.0), "initial_charge_percentage": 0.5},
        limits={},
        power_limits={},
        pricing={"salvage_value": 0.0},
        efficiency={},
        advanced={"charge_limit_cost": 100.0},
    )
    house = LoadConfigData(
        element_type=ElementType.LOAD,
        name="House",
        connection=bus,
        forecast={"forecast": np.ones(N_PERIODS)},
        curtailment={"curtailment": False},
    )
    grid = GridConfigData(
        element_type=ElementType.GRID,
        name="Grid",
        connection=bus,
        pricing={
            "price_source_target": np.array([1.0, 0.1, 0.1, 0.1]),
            "price_target_source": np.array([0.5, 0.0, 0.0, 0.0]),
        },
        power_limits={},
    )
    return {"Bus": node, "Battery": battery, "House": house, "Grid": grid}


def _buffer(shortfall_cost: float = 10.0) -> BufferConfigData:
    """Return a reserve keeping two hours of the house's load in the battery."""
    return BufferConfigData(
        element_type=ElementType.BUFFER,
        name="Outage",
        kind="reserve",
        participants={"loads": ["House"], "generation": [], "storage": ["Battery"]},
        requirement={"window": 2.0},
        pricing={"shortfall_cost": np.full(N_PERIODS, shortfall_cost)},
    )


def test_a_complete_form_is_a_buffer_config_without_its_unset_fields() -> None:
    """The form's values become the buffer's config, leaving out a level the form has no value for."""
    assert buffer_config("Draft", FORM) == {
        "element_type": ElementType.BUFFER,
        "name": "Draft",
        "kind": "reserve",
        "participants": {"loads": ["House"], "storage": ["Battery"]},
        "requirement": {"window": as_constant_value(2.0)},
        "pricing": {"shortfall_cost": as_constant_value(10.0)},
    }


@pytest.mark.parametrize(
    ("section", "field"),
    [
        pytest.param("participants", "storage", id="no_battery"),
        pytest.param("requirement", "window", id="no_window"),
        pytest.param("pricing", "shortfall_cost", id="no_shortfall_cost"),
    ],
)
def test_a_form_missing_what_a_buffer_needs_is_not_a_config(section: str, field: str) -> None:
    """A buffer cannot be planned until it has a battery, a window, and a shortfall cost."""
    values = FORM[section]
    assert isinstance(values, dict)
    form = {**FORM, section: {key: value for key, value in values.items() if key != field}}

    assert buffer_config("Draft", form) is None


def test_preview_holds_the_reserve_the_plan_now_would_sell() -> None:
    """With the buffer the battery keeps two hours of load that it would otherwise export in the first hour."""
    preview = preview_buffer(_hub(), _buffer(), HOURS)

    assert preview["kind"] == "reserve"
    assert preview["storage"] == ["Battery"]
    assert preview["current"] is not None
    assert preview["plan"] is not None
    assert preview["current"][1] == pytest.approx(0.0)
    assert preview["plan"][1] == pytest.approx(0.2)
    assert preview["buffer"][1] == pytest.approx(0.2)


def test_preview_replaces_the_buffer_of_the_same_name() -> None:
    """Reconfiguring a buffer compares the hub's plan with it against the plan with the draft in its place."""
    preview = preview_buffer({**_hub(), "Outage": _buffer()}, _buffer(shortfall_cost=0.0), HOURS)

    assert preview["current"] is not None
    assert preview["plan"] is not None
    assert preview["current"][1] == pytest.approx(0.2)
    assert preview["plan"][1] == pytest.approx(0.0)


def test_state_of_charge_is_none_for_batteries_the_network_does_not_have() -> None:
    """A preview naming a battery the hub's plan has no battery for has no plan now to compare against."""
    network = build_network("now", _hub(), HOURS)
    network.optimize()

    assert storage_state_of_charge(network, ["Battery", "Spare"]) is None


def test_unused_name_numbers_a_name_an_element_already_has() -> None:
    """The draft buffer takes a name no element of the hub has."""
    assert unused_name({"Bus": 1}, "Draft") == "Draft"
    assert unused_name({"Draft": 1, "Draft 2": 2}, "Draft") == "Draft 3"
