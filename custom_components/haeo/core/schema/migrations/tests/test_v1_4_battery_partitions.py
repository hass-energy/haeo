"""Tests for converting battery partitions into reserves and headroom in the v1.4 schema migration."""

from collections.abc import Mapping
import copy
from typing import TypedDict

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import battery, headroom, reserve
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
from custom_components.haeo.core.schema.migrations.v1_4 import (
    PARTITION_REQUIREMENT_WINDOW,
    migrate_battery_partitions,
    state_value_resolver,
)
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    SECTION_EFFICIENCY,
)

UNDERCHARGE = {
    partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(5.0),
    partitions.CONF_PARTITION_COST: as_constant_value(0.03),
}
OVERCHARGE = {
    partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(95.0),
    partitions.CONF_PARTITION_COST: as_constant_value(0.04),
}


def _sm(**states: str) -> FakeStateMachine:
    """Return a state machine holding each entity's state, keyed by its object id."""
    return FakeStateMachine(
        {
            f"sensor.{object_id}": FakeEntityState(entity_id=f"sensor.{object_id}", state=state, attributes={})
            for object_id, state in states.items()
        }
    )


def _battery(
    *,
    undercharge: Mapping[str, object] | None = None,
    overcharge: Mapping[str, object] | None = None,
    efficiency: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return a stored 10 kWh battery config with min 10% and max 90%, plus any partitions."""
    config: dict[str, object] = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
        battery.CONF_CONNECTION: as_connection_target("Bus"),
        battery.SECTION_STORAGE: {
            battery.CONF_CAPACITY: as_constant_value(10.0),
            battery.CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.soc"]),
        },
        battery.SECTION_LIMITS: {
            battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(10.0),
            battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(90.0),
        },
        SECTION_EFFICIENCY: dict(efficiency or {}),
        partitions.SECTION_PARTITIONING: {partitions.CONF_CONFIGURE_PARTITIONS: True},
    }
    if undercharge is not None:
        config[partitions.SECTION_UNDERCHARGE] = dict(undercharge)
    if overcharge is not None:
        config[partitions.SECTION_OVERCHARGE] = dict(overcharge)
    return config


def _approx_constant(value: float) -> dict[str, object]:
    """Return a constant schema value that compares equal to any constant within float tolerance of value."""
    return {"type": "constant", "value": pytest.approx(value)}


def _requirement(element_type: str, name: str, minimum: float, cost: object) -> dict[str, object]:
    return {
        CONF_ELEMENT_TYPE: element_type,
        CONF_NAME: name,
        reserve.SECTION_PARTICIPANTS: {reserve.CONF_STORAGE: ["Battery"]},
        reserve.SECTION_REQUIREMENT: {
            reserve.CONF_WINDOW: as_constant_value(PARTITION_REQUIREMENT_WINDOW),
            reserve.CONF_MINIMUM: _approx_constant(minimum),
        },
        reserve.SECTION_PRICING: {reserve.CONF_SHORTFALL_COST: cost},
    }


class PartitionCase(TypedDict):
    """A battery config, the state it is read against, and what its partitions become."""

    data: dict[str, object]
    states: dict[str, str]
    existing_names: set[str]
    limits: Mapping[str, object]
    requirements: list[dict[str, object]]
    unconverted: tuple[str, ...]


DEFAULT_LIMITS: dict[str, object] = {
    battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(10.0),
    battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(90.0),
}

PARTITION_CASES: dict[str, PartitionCase] = {
    "undercharge_only": {
        "data": _battery(undercharge=UNDERCHARGE),
        "states": {},
        "existing_names": {"Battery"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0)},
        "requirements": [_requirement(reserve.ELEMENT_TYPE, "Battery reserve", 0.5, as_constant_value(0.03))],
        "unconverted": (),
    },
    "overcharge_only": {
        "data": _battery(overcharge=OVERCHARGE),
        "states": {},
        "existing_names": {"Battery"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0)},
        "requirements": [_requirement(headroom.ELEMENT_TYPE, "Battery headroom", 0.5, as_constant_value(0.04))],
        "unconverted": (),
    },
    "both": {
        "data": _battery(undercharge=UNDERCHARGE, overcharge=OVERCHARGE),
        "states": {},
        "existing_names": {"Battery"},
        "limits": {
            battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0),
            battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0),
        },
        "requirements": [
            _requirement(reserve.ELEMENT_TYPE, "Battery reserve", 0.5, as_constant_value(0.03)),
            _requirement(headroom.ELEMENT_TYPE, "Battery headroom", 0.5, as_constant_value(0.04)),
        ],
        "unconverted": (),
    },
    "efficiency_scales_minimum_and_cost": {
        "data": _battery(
            undercharge=UNDERCHARGE,
            overcharge=OVERCHARGE,
            efficiency={
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(80.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_entity_value(["sensor.charge_efficiency"]),
            },
        ),
        "states": {"charge_efficiency": "50.0"},
        "existing_names": {"Battery"},
        "limits": {
            battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0),
            battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0),
        },
        "requirements": [
            _requirement(reserve.ELEMENT_TYPE, "Battery reserve", 0.5 * 0.8, _approx_constant(0.03 / 0.8)),
            _requirement(headroom.ELEMENT_TYPE, "Battery headroom", 0.5 / 0.5, _approx_constant(0.04 * 0.5)),
        ],
        "unconverted": (),
    },
    "unit_efficiency_keeps_entity_cost": {
        "data": _battery(
            undercharge={
                partitions.CONF_PARTITION_PERCENTAGE: as_entity_value(["sensor.floor"]),
                partitions.CONF_PARTITION_COST: as_entity_value(["sensor.cost"]),
            },
            efficiency={CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(100.0)},
        ),
        "states": {"floor": "4.0"},
        "existing_names": {"Battery"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MIN_CHARGE_PERCENTAGE: as_entity_value(["sensor.floor"])},
        "requirements": [
            _requirement(reserve.ELEMENT_TYPE, "Battery reserve", 0.6, as_entity_value(["sensor.cost"])),
        ],
        "unconverted": (),
    },
    "partition_inside_limit_only_moves_limit": {
        "data": _battery(
            undercharge={
                partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(20.0),
                partitions.CONF_PARTITION_COST: as_constant_value(0.03),
            }
        ),
        "states": {},
        "existing_names": {"Battery"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(20.0)},
        "requirements": [],
        "unconverted": (),
    },
    "unresolvable_entity_is_unconverted": {
        "data": _battery(
            undercharge={
                partitions.CONF_PARTITION_PERCENTAGE: as_entity_value(["sensor.floor"]),
                partitions.CONF_PARTITION_COST: as_constant_value(0.03),
            },
            overcharge=OVERCHARGE,
        ),
        "states": {"floor": "unavailable"},
        "existing_names": {"Battery"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0)},
        "requirements": [_requirement(headroom.ELEMENT_TYPE, "Battery headroom", 0.5, as_constant_value(0.04))],
        "unconverted": (partitions.SECTION_UNDERCHARGE,),
    },
    "unresolvable_efficiency_is_unconverted": {
        "data": _battery(
            undercharge=UNDERCHARGE,
            efficiency={CONF_EFFICIENCY_SOURCE_TARGET: as_entity_value(["sensor.missing"])},
        ),
        "states": {},
        "existing_names": {"Battery"},
        "limits": DEFAULT_LIMITS,
        "requirements": [],
        "unconverted": (partitions.SECTION_UNDERCHARGE,),
    },
    "name_collision_gets_unique_name": {
        "data": _battery(undercharge=UNDERCHARGE),
        "states": {},
        "existing_names": {"Battery", "Battery reserve", "Battery reserve 2"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0)},
        "requirements": [_requirement(reserve.ELEMENT_TYPE, "Battery reserve 3", 0.5, as_constant_value(0.03))],
        "unconverted": (),
    },
    "unpriced_partitions_ignored": {
        "data": _battery(
            undercharge={
                partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(5.0),
                partitions.CONF_PARTITION_COST: as_none_value(),
            },
            overcharge={partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(95.0)},
        ),
        "states": {},
        "existing_names": {"Battery"},
        "limits": DEFAULT_LIMITS,
        "requirements": [],
        "unconverted": (),
    },
}


@pytest.mark.parametrize("case", PARTITION_CASES.values(), ids=PARTITION_CASES.keys())
def test_migrate_battery_partitions(case: PartitionCase) -> None:
    """Partitions become limits plus reserves and headroom that hold the energy they priced."""
    original = copy.deepcopy(case["data"])
    existing_names = set(case["existing_names"])

    result = migrate_battery_partitions(
        case["data"], state_value_resolver(_sm(**case["states"])), existing_names=existing_names
    )

    expected_battery = {
        key: value
        for key, value in original.items()
        if key not in (partitions.SECTION_PARTITIONING, partitions.SECTION_UNDERCHARGE, partitions.SECTION_OVERCHARGE)
    }
    assert result.battery == {**expected_battery, battery.SECTION_LIMITS: case["limits"]}
    assert list(result.requirements) == case["requirements"]
    assert result.unconverted == case["unconverted"]
    assert case["data"] == original
    assert existing_names == case["existing_names"] | {str(r[CONF_NAME]) for r in result.requirements}


@pytest.mark.parametrize(
    ("value", "output_type", "states", "expected"),
    [
        pytest.param(as_constant_value(25.0), OutputType.STATE_OF_CHARGE, {}, 0.25, id="constant_percent_as_ratio"),
        pytest.param(as_constant_value(0.03), OutputType.PRICE_RATE, {}, 0.03, id="constant_price"),
        pytest.param(as_entity_value(["sensor.soc"]), OutputType.STATE_OF_CHARGE, {"soc": "40"}, 0.4, id="entity"),
        pytest.param(as_entity_value(["sensor.missing"]), OutputType.ENERGY, {}, None, id="missing_entity"),
        pytest.param(as_none_value(), OutputType.ENERGY, {}, None, id="none_value"),
        pytest.param(as_constant_value(True), OutputType.ENERGY, {}, None, id="non_numeric_constant"),
        pytest.param("legacy", OutputType.ENERGY, {}, None, id="not_a_schema_value"),
    ],
)
def test_state_value_resolver(
    value: object, output_type: OutputType, states: dict[str, str], expected: float | None
) -> None:
    """The resolver reads constants as stored and entities from their current state, with percentages as ratios."""
    assert state_value_resolver(_sm(**states))(value, output_type) == (
        pytest.approx(expected) if expected is not None else None
    )
