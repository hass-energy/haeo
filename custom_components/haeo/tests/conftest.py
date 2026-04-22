"""Shared fixtures and factories for HAEO integration tests."""

from typing import Any

from custom_components.haeo.const import INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import (
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    HORIZON_PRESET_5_DAYS,
    HubTiersSection,
)
from custom_components.haeo.core.schema.elements import HaeoConfigEntryDict

DEFAULT_TIERS: HubTiersSection = {
    "tier_1_count": DEFAULT_TIER_1_COUNT,
    "tier_1_duration": DEFAULT_TIER_1_DURATION,
    "tier_2_count": DEFAULT_TIER_2_COUNT,
    "tier_2_duration": DEFAULT_TIER_2_DURATION,
    "tier_3_count": DEFAULT_TIER_3_COUNT,
    "tier_3_duration": DEFAULT_TIER_3_DURATION,
    "tier_4_count": DEFAULT_TIER_4_COUNT,
    "tier_4_duration": DEFAULT_TIER_4_DURATION,
}


def make_config_snapshot(**overrides: Any) -> HaeoConfigEntryDict:
    """Build a complete HaeoConfigEntryDict with sensible defaults.

    Overrides are shallow-merged at the top level. To override nested fields
    (e.g. `data.tiers.tier_1_count`), pass the full sub-dict so the test stays
    explicit about its assumptions.
    """
    base: HaeoConfigEntryDict = {
        "version": 1,
        "minor_version": 3,
        "domain": "haeo",
        "title": "Test",
        "data": {
            "integration_type": INTEGRATION_TYPE_HUB,
            "common": {"name": "Test", "horizon_preset": HORIZON_PRESET_5_DAYS},
            "tiers": DEFAULT_TIERS,
            "advanced": {"debounce_seconds": DEFAULT_DEBOUNCE_SECONDS, "advanced_mode": False},
        },
        "options": {},
        "subentries": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base
