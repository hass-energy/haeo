"""Tests for horizon schema values."""

from custom_components.haeo.core.const import CONF_HORIZON, CONF_HORIZON_PRESET, HUB_SECTION_COMMON
from custom_components.haeo.core.schema import (
    HORIZON_PRESET_CUSTOM,
    as_entity_value,
    as_horizon_preset_value,
    parse_horizon_config,
)


def test_parse_horizon_preset_value() -> None:
    """Parse new preset horizon schema value."""
    config = {HUB_SECTION_COMMON: {CONF_HORIZON: as_horizon_preset_value("5_days")}}
    parsed = parse_horizon_config(config)
    assert parsed.mode == "preset"
    assert parsed.preset == "5_days"
    assert parsed.entity_id is None


def test_parse_horizon_entity_value() -> None:
    """Parse entity horizon schema value."""
    config = {HUB_SECTION_COMMON: {CONF_HORIZON: as_entity_value(["sensor.external_grid"])}}
    parsed = parse_horizon_config(config)
    assert parsed.mode == "entity"
    assert parsed.entity_id == "sensor.external_grid"


def test_parse_legacy_horizon_preset_custom() -> None:
    """Parse legacy custom horizon preset string."""
    config = {HUB_SECTION_COMMON: {CONF_HORIZON_PRESET: HORIZON_PRESET_CUSTOM}}
    parsed = parse_horizon_config(config)
    assert parsed.mode == "legacy_custom"


def test_parse_legacy_horizon_preset_days() -> None:
    """Parse legacy flat horizon preset string."""
    config = {"horizon_preset": "3_days"}
    parsed = parse_horizon_config(config)
    assert parsed.mode == "preset"
    assert parsed.preset == "3_days"
