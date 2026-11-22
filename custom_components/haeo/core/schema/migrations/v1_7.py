"""Pure config transformation logic for the v1.7 migration.

A connection's power limit, price, and efficiency move from fixed sections
into its ordered list of segments, in the order they always applied: the
limit, then the price, then the efficiency. One left unset gives no segment.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import is_none_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY,
    CONF_MAX_POWER,
    CONF_PRICE,
    CONF_SEGMENT_TYPE,
    CONF_SEGMENTS,
)
from custom_components.haeo.core.schema.migrations import section_dict
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

# The config entry minor version these migrations bring an entry to
MINOR_VERSION: Final = 7

# Each former section, its field, and the segment it becomes, in the order they applied
SEGMENTS_FROM_SECTIONS: Final = (
    (SECTION_POWER_LIMITS, CONF_MAX_POWER_SOURCE_TARGET, "power_limit", CONF_MAX_POWER),
    (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET, "pricing", CONF_PRICE),
    (SECTION_EFFICIENCY, CONF_EFFICIENCY_SOURCE_TARGET, "efficiency", CONF_EFFICIENCY),
)


def segment_sources(config: Mapping[str, object]) -> list[tuple[str, str, str]]:
    """Return, for each segment a connection's sections become, the section and field it came from and its field."""
    return [
        (section, field, segment_field)
        for section, field, _segment_type, segment_field in SEGMENTS_FROM_SECTIONS
        if (value := section_dict(config, section).get(field)) is not None and not is_none_value(value)
    ]


def migrate_element_config(config: Mapping[str, object]) -> dict[str, object] | None:
    """Return a connection config with its sections as segments, or None when the config needs no change."""
    if config.get(CONF_ELEMENT_TYPE) != ElementType.CONNECTION or CONF_SEGMENTS in config:
        return None
    segments: list[dict[str, object]] = []
    for section, field, segment_type, segment_field in SEGMENTS_FROM_SECTIONS:
        value = section_dict(config, section).get(field)
        if value is not None and not is_none_value(value):
            segments.append({CONF_SEGMENT_TYPE: segment_type, segment_field: value})
    sections = {section for section, *_ in SEGMENTS_FROM_SECTIONS}
    return {**{key: value for key, value in config.items() if key not in sections}, CONF_SEGMENTS: segments}
