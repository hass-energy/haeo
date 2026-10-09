"""Tests for v1.4 connection unidirectional schema migration."""

from collections.abc import Mapping

import pytest

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    as_connection_target,
    as_constant_value,
    as_entity_value,
    as_none_value,
    get_connection_target_name,
)
from custom_components.haeo.core.schema.elements import connection
from custom_components.haeo.core.schema.migrations.v1_4 import merge_reverse_into_existing, migrate_connection_config
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)


def _section(config: Mapping[str, object], key: str) -> Mapping[str, object]:
    """Narrow a nested section value from migrated config for assertions."""
    section = config[key]
    assert isinstance(section, Mapping)
    return section


def _connection_config(**sections: object) -> dict[str, object]:
    return {
        CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
        CONF_NAME: "Inverter link",
        connection.SECTION_ENDPOINTS: {
            connection.CONF_SOURCE: as_connection_target("DC Bus"),
            connection.CONF_TARGET: as_connection_target("AC Bus"),
        },
        **sections,
    }


def test_migrate_strips_segment_order() -> None:
    """Segment order is removed from the forward connection."""
    data = _connection_config(
        segment_order={"mirror_segment_order": True},
        power_limits={},
        pricing={},
        efficiency={},
    )

    forward, _ = migrate_connection_config(data)

    assert "segment_order" not in forward


@pytest.mark.parametrize(
    "reverse_power",
    [
        pytest.param({}, id="unset"),
        pytest.param({CONF_MAX_POWER_TARGET_SOURCE: as_none_value()}, id="none"),
    ],
)
def test_migrate_unset_reverse_power_creates_unlimited_reverse(reverse_power: dict[str, object]) -> None:
    """An unset reverse max power meant unlimited reverse flow, so an unlimited reverse connection is created."""
    data = _connection_config(
        power_limits={CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0), **reverse_power},
        pricing={},
        efficiency={},
    )

    forward, reverse = migrate_connection_config(data)

    assert _section(forward, SECTION_POWER_LIMITS) == {CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0)}
    assert reverse is not None
    assert reverse[CONF_NAME] == "Inverter link (AC Bus to DC Bus)"
    assert _section(reverse, SECTION_POWER_LIMITS) == {}
    assert _section(reverse, SECTION_PRICING) == {}
    assert _section(reverse, SECTION_EFFICIENCY) == {}


@pytest.mark.parametrize("zero", [0, 0.0], ids=["int", "float"])
def test_migrate_zero_reverse_power_blocks_reverse(zero: float) -> None:
    """A constant 0 reverse max power blocked reverse flow, so no reverse connection is created."""
    data = _connection_config(
        power_limits={
            CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
            CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(zero),
        },
        pricing={CONF_PRICE_TARGET_SOURCE: as_constant_value(0.2)},
        efficiency={CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(0.9)},
    )

    forward, reverse = migrate_connection_config(data)

    assert reverse is None
    assert _section(forward, SECTION_POWER_LIMITS) == {CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0)}
    assert _section(forward, SECTION_PRICING) == {}
    assert _section(forward, SECTION_EFFICIENCY) == {}


def test_migrate_entity_reverse_power_creates_reverse() -> None:
    """A sensor-driven reverse max power is carried to the reverse connection even if it may read 0."""
    data = _connection_config(
        power_limits={CONF_MAX_POWER_TARGET_SOURCE: as_entity_value(["sensor.reverse_limit"])},
        pricing={},
        efficiency={},
    )

    _, reverse = migrate_connection_config(data)

    assert reverse is not None
    assert _section(reverse, SECTION_POWER_LIMITS) == {
        CONF_MAX_POWER_SOURCE_TARGET: as_entity_value(["sensor.reverse_limit"]),
    }


def test_migrate_splits_reverse_fields() -> None:
    """Reverse-direction fields become a second connection with swapped endpoints."""
    data = _connection_config(
        power_limits={
            CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
            CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(8.0),
        },
        pricing={
            CONF_PRICE_SOURCE_TARGET: as_constant_value(0.1),
            CONF_PRICE_TARGET_SOURCE: as_constant_value(0.2),
        },
        efficiency={
            CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(0.95),
            CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(0.90),
        },
    )

    forward, reverse = migrate_connection_config(data)

    assert reverse is not None
    assert forward[CONF_NAME] == "Inverter link"
    assert CONF_MAX_POWER_TARGET_SOURCE not in _section(forward, SECTION_POWER_LIMITS)
    assert reverse[CONF_NAME] == "Inverter link (AC Bus to DC Bus)"
    assert _section(reverse, SECTION_POWER_LIMITS)[CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(8.0)
    assert _section(reverse, SECTION_PRICING)[CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.2)
    assert _section(reverse, SECTION_EFFICIENCY)[CONF_EFFICIENCY_SOURCE_TARGET] == as_constant_value(0.90)
    reverse_endpoints = reverse[connection.SECTION_ENDPOINTS]
    assert isinstance(reverse_endpoints, dict)
    assert get_connection_target_name(reverse_endpoints[connection.CONF_SOURCE]) == "AC Bus"
    assert get_connection_target_name(reverse_endpoints[connection.CONF_TARGET]) == "DC Bus"


def test_migrate_unique_reverse_name() -> None:
    """Reverse connection names avoid collisions with existing subentry titles."""
    data = _connection_config(
        power_limits={CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0)},
        pricing={},
        efficiency={},
    )

    _, reverse = migrate_connection_config(
        data,
        existing_names={"Inverter link (AC Bus to DC Bus)"},
    )

    assert reverse is not None
    assert reverse[CONF_NAME] == "Inverter link (AC Bus to DC Bus) 2"


def test_merge_reverse_into_existing() -> None:
    """Reverse values merge only into unset fields on an existing reverse connection."""
    existing = _connection_config(
        power_limits={CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(6.0)},
        pricing={},
        efficiency={},
    )
    existing[connection.SECTION_ENDPOINTS] = {
        connection.CONF_SOURCE: as_connection_target("AC Bus"),
        connection.CONF_TARGET: as_connection_target("DC Bus"),
    }
    reverse_data = {
        SECTION_POWER_LIMITS: {CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(8.0)},
        SECTION_PRICING: {CONF_PRICE_SOURCE_TARGET: as_constant_value(0.2)},
        SECTION_EFFICIENCY: {},
    }

    merged = merge_reverse_into_existing(existing, reverse_data)

    assert _section(merged, SECTION_POWER_LIMITS)[CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(6.0)
    assert _section(merged, SECTION_PRICING)[CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.2)
