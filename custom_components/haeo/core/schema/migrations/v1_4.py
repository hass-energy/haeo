"""Pure config transformation logic for v1.4 migration (horizon choose selector)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from custom_components.haeo.core.const import (
    CONF_HORIZON,
    CONF_HORIZON_PRESET,
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_COMMON,
)
from custom_components.haeo.core.schema.horizon_value import HORIZON_PRESET_CUSTOM, as_horizon_preset_value


@dataclass(frozen=True)
class HubMigrationStep:
    """Single hub-config migration step."""

    name: str
    transform: Callable[[dict[str, Any], dict[str, Any], str], tuple[dict[str, Any], dict[str, Any]]]


def migrate_hub_config(
    data: dict[str, Any], options: dict[str, Any], title: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Migrate hub config data/options through all v1.4 schema migration steps."""
    migrated_data = dict(data)
    migrated_options = dict(options)
    for step in HUB_MIGRATION_STEPS:
        migrated_data, migrated_options = step.transform(migrated_data, migrated_options, title)
    return migrated_data, migrated_options


def _migrate_horizon_to_choose_value(
    data: dict[str, Any], options: dict[str, Any], _title: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Migrate flat horizon_preset to common.horizon schema value."""
    common = data.get(HUB_SECTION_COMMON)
    if not isinstance(common, dict):
        return data, options

    if CONF_HORIZON in common:
        return data, options

    preset = common.get(CONF_HORIZON_PRESET) or options.get(CONF_HORIZON_PRESET)
    if preset == HORIZON_PRESET_CUSTOM or data.get(CONF_HORIZON_PRESET) == HORIZON_PRESET_CUSTOM:
        preset = HORIZON_PRESET_CUSTOM
    elif not isinstance(preset, str) or not preset:
        preset = HORIZON_PRESET_5_DAYS

    new_common = dict(common)
    new_common[CONF_HORIZON] = as_horizon_preset_value(preset)
    new_common.pop(CONF_HORIZON_PRESET, None)
    data[HUB_SECTION_COMMON] = new_common

    options.pop(CONF_HORIZON_PRESET, None)
    return data, options


HUB_MIGRATION_STEPS: tuple[HubMigrationStep, ...] = (
    HubMigrationStep(name="horizon_preset_to_choose_v1_4", transform=_migrate_horizon_to_choose_value),
)

__all__ = ["HORIZON_PRESET_CUSTOM", "HUB_MIGRATION_STEPS", "migrate_hub_config"]
