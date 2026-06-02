"""Schema values for hub planning horizon configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, TypeGuard

from custom_components.haeo.core.const import (
    CONF_HORIZON,
    CONF_HORIZON_PRESET,
    CONF_TIER_1_COUNT,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.core.schema.entity_value import EntityValue, is_entity_value

VALUE_TYPE_PRESET = "preset"
HORIZON_PRESET_CUSTOM: Literal["custom"] = "custom"


class HorizonPresetValue(TypedDict):
    """Schema value for a planning horizon day preset."""

    type: Literal["preset"]
    value: str


@dataclass(frozen=True, slots=True)
class ParsedHorizonConfig:
    """Resolved horizon configuration from hub config data."""

    mode: Literal["preset", "entity", "legacy_custom"]
    preset: str | None = None
    entity_id: str | None = None


def as_horizon_preset_value(value: str) -> HorizonPresetValue:
    """Create a preset horizon schema value."""
    return {"type": VALUE_TYPE_PRESET, "value": value}


def is_horizon_preset_value(value: Any) -> TypeGuard[HorizonPresetValue]:
    """Return True if value is a preset horizon schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_PRESET:
        return False
    preset = value.get("value")
    return isinstance(preset, str) and bool(preset)


def is_horizon_entity_value(value: Any) -> TypeGuard[EntityValue]:
    """Return True if value is an entity-based horizon configuration."""
    return is_entity_value(value)


def get_horizon_entity_id(value: EntityValue) -> str:
    """Return the single entity ID from a horizon entity value."""
    entities = value["value"]
    return entities[0]


def _horizon_from_common(common: Mapping[str, Any]) -> Any | None:
    if CONF_HORIZON in common:
        return common[CONF_HORIZON]
    return common.get(CONF_HORIZON_PRESET)


def parse_horizon_config(config: Mapping[str, Any]) -> ParsedHorizonConfig:
    """Parse hub config into a resolved horizon mode.

    Supports new ``horizon`` schema values and legacy ``horizon_preset`` strings.
    """
    common_raw = config.get(HUB_SECTION_COMMON)
    common = common_raw if isinstance(common_raw, Mapping) else None
    tiers_raw = config.get(HUB_SECTION_TIERS)
    tiers_section = tiers_raw if isinstance(tiers_raw, Mapping) else None

    if common is None:
        legacy = config.get(CONF_HORIZON_PRESET)
        if legacy == HORIZON_PRESET_CUSTOM:
            return ParsedHorizonConfig(mode="legacy_custom")
        if isinstance(legacy, str) and legacy and legacy != HORIZON_PRESET_CUSTOM:
            return ParsedHorizonConfig(mode="preset", preset=legacy)
        if tiers_section or CONF_TIER_1_COUNT in config:
            return ParsedHorizonConfig(mode="legacy_custom")
        return ParsedHorizonConfig(mode="preset", preset="5_days")

    horizon = _horizon_from_common(common)
    if is_horizon_entity_value(horizon):
        return ParsedHorizonConfig(mode="entity", entity_id=get_horizon_entity_id(horizon))
    if is_horizon_preset_value(horizon):
        preset = horizon["value"]
        if preset == HORIZON_PRESET_CUSTOM:
            return ParsedHorizonConfig(mode="legacy_custom")
        return ParsedHorizonConfig(mode="preset", preset=preset)
    if horizon == HORIZON_PRESET_CUSTOM:
        return ParsedHorizonConfig(mode="legacy_custom")
    if isinstance(horizon, str) and horizon:
        if horizon == HORIZON_PRESET_CUSTOM:
            return ParsedHorizonConfig(mode="legacy_custom")
        return ParsedHorizonConfig(mode="preset", preset=horizon)
    return ParsedHorizonConfig(mode="preset", preset="5_days")


__all__ = [
    "HORIZON_PRESET_CUSTOM",
    "VALUE_TYPE_PRESET",
    "HorizonPresetValue",
    "ParsedHorizonConfig",
    "as_horizon_preset_value",
    "get_horizon_entity_id",
    "is_horizon_entity_value",
    "is_horizon_preset_value",
    "parse_horizon_config",
]
