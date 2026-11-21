"""Tests for the pure v1.7 migration of connections into segments."""

from collections.abc import Mapping

import pytest

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY,
    CONF_MAX_POWER,
    CONF_PRICE,
    CONF_SEGMENT_TYPE,
    CONF_SEGMENTS,
    SECTION_ENDPOINTS,
)
from custom_components.haeo.core.schema.migrations.v1_7 import migrate_element_config
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

ENDPOINTS = {"source": as_connection_target("Inverter"), "target": as_connection_target("Switchboard")}
LIMIT = as_constant_value(10.0)
PRICE = as_entity_value(["sensor.price"])
EFFICIENCY = as_constant_value(95.0)


def _connection(**sections: Mapping[str, object]) -> dict[str, object]:
    return {CONF_ELEMENT_TYPE: ElementType.CONNECTION, CONF_NAME: "Link", SECTION_ENDPOINTS: ENDPOINTS, **sections}


@pytest.mark.parametrize(
    ("config", "segments"),
    [
        pytest.param(
            _connection(
                **{
                    SECTION_EFFICIENCY: {CONF_EFFICIENCY_SOURCE_TARGET: EFFICIENCY},
                    SECTION_PRICING: {CONF_PRICE_SOURCE_TARGET: PRICE},
                    SECTION_POWER_LIMITS: {CONF_MAX_POWER_SOURCE_TARGET: LIMIT},
                }
            ),
            [
                {CONF_SEGMENT_TYPE: "power_limit", CONF_MAX_POWER: LIMIT},
                {CONF_SEGMENT_TYPE: "pricing", CONF_PRICE: PRICE},
                {CONF_SEGMENT_TYPE: "efficiency", CONF_EFFICIENCY: EFFICIENCY},
            ],
            id="all_in_the_order_they_applied",
        ),
        pytest.param(
            _connection(
                **{
                    SECTION_POWER_LIMITS: {CONF_MAX_POWER_SOURCE_TARGET: as_none_value()},
                    SECTION_PRICING: {},
                    SECTION_EFFICIENCY: {CONF_EFFICIENCY_SOURCE_TARGET: EFFICIENCY},
                }
            ),
            [{CONF_SEGMENT_TYPE: "efficiency", CONF_EFFICIENCY: EFFICIENCY}],
            id="none_and_missing_skipped",
        ),
        pytest.param(_connection(), [], id="no_sections"),
    ],
)
def test_connection_sections_become_segments(config: dict[str, object], segments: list[dict[str, object]]) -> None:
    """A connection's limit, price and efficiency become segments in that order, and the sections go."""
    assert migrate_element_config(config) == {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "Link",
        SECTION_ENDPOINTS: ENDPOINTS,
        CONF_SEGMENTS: segments,
    }


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({**_connection(), CONF_SEGMENTS: []}, id="already_migrated"),
        pytest.param({CONF_ELEMENT_TYPE: ElementType.GRID, SECTION_PRICING: {}}, id="other_element"),
    ],
)
def test_config_needing_no_change_is_left_alone(config: dict[str, object]) -> None:
    """A connection that already has segments, or any other element, needs no change."""
    assert migrate_element_config(config) is None
