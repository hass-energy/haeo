"""Tests for converting battery partitions into buffers in the v1.4 schema migration."""

from collections.abc import Mapping
import copy
from typing import TypedDict

import pytest

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import battery, buffer
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
from custom_components.haeo.core.schema.migrations.v1_4 import PARTITION_BUFFER_WINDOW, migrate_battery_partitions

UNDERCHARGE = {
    partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(5.0),
    partitions.CONF_PARTITION_COST: as_constant_value(0.03),
}
OVERCHARGE = {
    partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(95.0),
    partitions.CONF_PARTITION_COST: as_constant_value(0.04),
}
MIN_CHARGE = as_constant_value(10.0)
MAX_CHARGE = as_constant_value(90.0)


def _battery(
    *,
    undercharge: Mapping[str, object] | None = None,
    overcharge: Mapping[str, object] | None = None,
    limits: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return a stored 10 kWh battery config with the given limits, min 10% and max 90% by default, and partitions."""
    config: dict[str, object] = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
        battery.CONF_CONNECTION: as_connection_target("Bus"),
        battery.SECTION_STORAGE: {
            battery.CONF_CAPACITY: as_constant_value(10.0),
            battery.CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.soc"]),
        },
        battery.SECTION_LIMITS: dict(DEFAULT_LIMITS if limits is None else limits),
        partitions.SECTION_PARTITIONING: {partitions.CONF_CONFIGURE_PARTITIONS: True},
    }
    if undercharge is not None:
        config[partitions.SECTION_UNDERCHARGE] = dict(undercharge)
    if overcharge is not None:
        config[partitions.SECTION_OVERCHARGE] = dict(overcharge)
    return config


def _buffer(name: str, kind: buffer.BufferKind, level: object, cost: object) -> dict[str, object]:
    return {
        CONF_ELEMENT_TYPE: buffer.ELEMENT_TYPE,
        CONF_NAME: name,
        buffer.CONF_KIND: kind,
        buffer.SECTION_PARTICIPANTS: {buffer.CONF_STORAGE: ["Battery"]},
        buffer.SECTION_REQUIREMENT: {
            buffer.CONF_WINDOW: as_constant_value(PARTITION_BUFFER_WINDOW),
            buffer.CONF_LEVEL: level,
        },
        buffer.SECTION_PRICING: {buffer.CONF_SHORTFALL_COST: cost},
    }


class PartitionCase(TypedDict):
    """A battery config, the names already taken, and what its partitions become."""

    data: dict[str, object]
    existing_names: set[str]
    limits: Mapping[str, object]
    buffers: list[dict[str, object]]


DEFAULT_LIMITS: dict[str, object] = {
    battery.CONF_MIN_CHARGE_PERCENTAGE: MIN_CHARGE,
    battery.CONF_MAX_CHARGE_PERCENTAGE: MAX_CHARGE,
}

SENSOR_PERCENTAGE = as_entity_value(["sensor.floor"])
SENSOR_COST = as_entity_value(["sensor.cost"])
SENSOR_LIMIT = as_entity_value(["sensor.min"])

PARTITION_CASES: dict[str, PartitionCase] = {
    "undercharge_only": {
        "data": _battery(undercharge=UNDERCHARGE),
        "existing_names": {"Battery"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0)},
        "buffers": [_buffer("Battery reserve", "reserve", MIN_CHARGE, as_constant_value(0.03))],
    },
    "overcharge_only": {
        "data": _battery(overcharge=OVERCHARGE),
        "existing_names": {"Battery"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0)},
        "buffers": [_buffer("Battery headroom", "headroom", MAX_CHARGE, as_constant_value(0.04))],
    },
    "both": {
        "data": _battery(undercharge=UNDERCHARGE, overcharge=OVERCHARGE),
        "existing_names": {"Battery"},
        "limits": {
            battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0),
            battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0),
        },
        "buffers": [
            _buffer("Battery reserve", "reserve", MIN_CHARGE, as_constant_value(0.03)),
            _buffer("Battery headroom", "headroom", MAX_CHARGE, as_constant_value(0.04)),
        ],
    },
    "sensor_values_move_as_they_are": {
        "data": _battery(
            undercharge={
                partitions.CONF_PARTITION_PERCENTAGE: SENSOR_PERCENTAGE,
                partitions.CONF_PARTITION_COST: SENSOR_COST,
            },
            limits={battery.CONF_MIN_CHARGE_PERCENTAGE: SENSOR_LIMIT},
        ),
        "existing_names": {"Battery"},
        "limits": {battery.CONF_MIN_CHARGE_PERCENTAGE: SENSOR_PERCENTAGE},
        "buffers": [_buffer("Battery reserve", "reserve", SENSOR_LIMIT, SENSOR_COST)],
    },
    "unset_limit_only_moves_limit": {
        "data": _battery(undercharge=UNDERCHARGE, overcharge=OVERCHARGE, limits={}),
        "existing_names": {"Battery"},
        "limits": {
            battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0),
            battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0),
        },
        "buffers": [],
    },
    "none_limit_only_moves_limit": {
        "data": _battery(undercharge=UNDERCHARGE, limits={battery.CONF_MIN_CHARGE_PERCENTAGE: as_none_value()}),
        "existing_names": {"Battery"},
        "limits": {battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0)},
        "buffers": [],
    },
    "name_collision_gets_unique_name": {
        "data": _battery(undercharge=UNDERCHARGE),
        "existing_names": {"Battery", "Battery reserve", "Battery reserve 2"},
        "limits": {**DEFAULT_LIMITS, battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0)},
        "buffers": [_buffer("Battery reserve 3", "reserve", MIN_CHARGE, as_constant_value(0.03))],
    },
    "unpriced_partitions_ignored": {
        "data": _battery(
            undercharge={
                partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(5.0),
                partitions.CONF_PARTITION_COST: as_none_value(),
            },
            overcharge={partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(95.0)},
        ),
        "existing_names": {"Battery"},
        "limits": DEFAULT_LIMITS,
        "buffers": [],
    },
}


@pytest.mark.parametrize("case", PARTITION_CASES.values(), ids=PARTITION_CASES.keys())
def test_migrate_battery_partitions(case: PartitionCase) -> None:
    """Partitions become limits plus buffers that charge what the partitions priced."""
    original = copy.deepcopy(case["data"])
    existing_names = set(case["existing_names"])

    result = migrate_battery_partitions(case["data"], existing_names=existing_names)

    expected_battery = {
        key: value
        for key, value in original.items()
        if key not in (partitions.SECTION_PARTITIONING, partitions.SECTION_UNDERCHARGE, partitions.SECTION_OVERCHARGE)
    }
    assert result.battery == {**expected_battery, battery.SECTION_LIMITS: case["limits"]}
    assert list(result.buffers) == case["buffers"]
    assert case["data"] == original
    assert existing_names == case["existing_names"] | {str(b[CONF_NAME]) for b in result.buffers}


def test_migrate_battery_partitions_moves_the_value_objects() -> None:
    """The partition's values and the old limit move into the battery and buffer as the same objects."""
    data = _battery(
        undercharge={
            partitions.CONF_PARTITION_PERCENTAGE: SENSOR_PERCENTAGE,
            partitions.CONF_PARTITION_COST: SENSOR_COST,
        },
        limits={battery.CONF_MIN_CHARGE_PERCENTAGE: SENSOR_LIMIT},
    )

    result = migrate_battery_partitions(data, existing_names=set())

    limits = result.battery[battery.SECTION_LIMITS]
    (reserve,) = result.buffers
    requirement = reserve[buffer.SECTION_REQUIREMENT]
    pricing = reserve[buffer.SECTION_PRICING]
    assert isinstance(limits, dict)
    assert isinstance(requirement, dict)
    assert isinstance(pricing, dict)
    assert limits[battery.CONF_MIN_CHARGE_PERCENTAGE] is SENSOR_PERCENTAGE
    assert requirement[buffer.CONF_LEVEL] is SENSOR_LIMIT
    assert pricing[buffer.CONF_SHORTFALL_COST] is SENSOR_COST
