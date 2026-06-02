"""Tests for v1.4 horizon choose-selector migration."""

from custom_components.haeo.core.const import CONF_HORIZON, CONF_HORIZON_PRESET, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.core.schema import HORIZON_PRESET_CUSTOM, as_horizon_preset_value, is_horizon_preset_value
from custom_components.haeo.core.schema.migrations.v1_4 import migrate_hub_config


def test_migrate_horizon_preset_to_choose_value() -> None:
    """Migrate flat horizon_preset into common.horizon preset value."""
    data = {HUB_SECTION_COMMON: {CONF_HORIZON_PRESET: "3_days", "name": "Hub"}}
    migrated_data, _migrated_options = migrate_hub_config(data, {}, "Hub")

    horizon = migrated_data[HUB_SECTION_COMMON][CONF_HORIZON]
    assert is_horizon_preset_value(horizon)
    assert horizon["value"] == "3_days"
    assert CONF_HORIZON_PRESET not in migrated_data[HUB_SECTION_COMMON]


def test_migrate_sectioned_tiers_without_preset_uses_custom() -> None:
    """Sectioned hub with tiers but no horizon preset keeps legacy custom mode."""
    data = {
        HUB_SECTION_COMMON: {"name": "Hub"},
        HUB_SECTION_TIERS: {"tier_1_count": 5, "tier_1_duration": 1},
    }
    migrated_data, _ = migrate_hub_config(data, {}, "Hub")

    horizon = migrated_data[HUB_SECTION_COMMON][CONF_HORIZON]
    assert horizon == as_horizon_preset_value(HORIZON_PRESET_CUSTOM)


def test_migrate_custom_preset_preserved() -> None:
    """Legacy custom preset is preserved for existing tier configurations."""
    data = {
        HUB_SECTION_COMMON: {CONF_HORIZON_PRESET: HORIZON_PRESET_CUSTOM, "name": "Hub"},
        "tiers": {"tier_1_count": 5},
    }
    migrated_data, _ = migrate_hub_config(data, {}, "Hub")

    horizon = migrated_data[HUB_SECTION_COMMON][CONF_HORIZON]
    assert horizon == as_horizon_preset_value(HORIZON_PRESET_CUSTOM)
