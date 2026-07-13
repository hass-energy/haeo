"""Tests for v1.4 connection unidirectional schema migration."""

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    as_connection_target,
    as_constant_value,
    as_none_value,
    get_connection_target_name,
)
from custom_components.haeo.core.schema.elements import connection
from custom_components.haeo.core.schema.migrations.v1_4 import (
    merge_reverse_into_existing,
    migrate_connection_config,
)
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


def test_migrate_strips_segment_order_only() -> None:
    """Segment order is removed without creating a reverse connection."""
    data = _connection_config(
        segment_order={"mirror_segment_order": True},
        power_limits={},
        pricing={},
        efficiency={},
    )

    forward, reverse = migrate_connection_config(data)

    assert reverse is None
    assert "segment_order" not in forward


def test_migrate_forward_only_unchanged() -> None:
    """Forward-only configuration is unchanged aside from cleanup."""
    data = _connection_config(
        power_limits={CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0)},
        pricing={},
        efficiency={},
    )

    forward, reverse = migrate_connection_config(data)

    assert reverse is None
    assert forward[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(10.0)
    assert CONF_MAX_POWER_TARGET_SOURCE not in forward[SECTION_POWER_LIMITS]


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
    assert CONF_MAX_POWER_TARGET_SOURCE not in forward[SECTION_POWER_LIMITS]
    assert reverse[CONF_NAME] == "Inverter link (AC Bus to DC Bus)"
    assert reverse[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(8.0)
    assert reverse[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.2)
    assert reverse[SECTION_EFFICIENCY][CONF_EFFICIENCY_SOURCE_TARGET] == as_constant_value(0.90)
    reverse_endpoints = reverse[connection.SECTION_ENDPOINTS]
    assert isinstance(reverse_endpoints, dict)
    assert get_connection_target_name(reverse_endpoints[connection.CONF_SOURCE]) == "AC Bus"
    assert get_connection_target_name(reverse_endpoints[connection.CONF_TARGET]) == "DC Bus"


def test_migrate_ignores_none_reverse_values() -> None:
    """Explicit none reverse values do not trigger a split."""
    data = _connection_config(
        power_limits={
            CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
            CONF_MAX_POWER_TARGET_SOURCE: as_none_value(),
        },
        pricing={},
        efficiency={},
    )

    forward, reverse = migrate_connection_config(data)

    assert reverse is None
    assert CONF_MAX_POWER_TARGET_SOURCE not in forward[SECTION_POWER_LIMITS]


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

    assert merged[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(6.0)
    assert merged[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.2)

