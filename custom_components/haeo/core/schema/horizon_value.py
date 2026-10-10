"""Schema values for the hub's planning horizon."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, TypedDict, TypeGuard

from custom_components.haeo.core.schema.entity_value import EntityValue

VALUE_TYPE_PRESET = "preset"


class HorizonPresetValue(TypedDict):
    """Schema value for a planning horizon preset."""

    type: Literal["preset"]
    value: str


type HorizonValue = HorizonPresetValue | EntityValue


def as_horizon_preset_value(preset: str) -> HorizonPresetValue:
    """Create a planning horizon preset schema value."""
    return {"type": VALUE_TYPE_PRESET, "value": preset}


def is_horizon_preset_value(value: object) -> TypeGuard[HorizonPresetValue]:
    """Return True if value is a planning horizon preset schema value."""
    return isinstance(value, Mapping) and value.get("type") == VALUE_TYPE_PRESET and isinstance(value.get("value"), str)


__all__ = [
    "VALUE_TYPE_PRESET",
    "HorizonPresetValue",
    "HorizonValue",
    "as_horizon_preset_value",
    "is_horizon_preset_value",
]
