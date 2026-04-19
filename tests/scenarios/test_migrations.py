"""Tests for the scenario diagnostics migration layer.

Scenario fixtures are immutable on disk — we bring them forward in memory so
older captures stay usable as the diagnostics schema evolves. These tests pin
the v1 → current behaviour and the round-trip property.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from custom_components.haeo.core.const import (
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.diagnostics import DIAGNOSTICS_SCHEMA_VERSION
from custom_components.haeo.diagnostics.collector import _jsonify

from .migrations import detect_schema_version, migrate_scenario


def _v1_capture() -> dict[str, Any]:
    """Return a minimal v1-shaped diagnostics blob (pre-schema-versioning)."""
    return {
        # No ``schema_version`` — treated as v1.
        "environment": {
            "ha_version": "2025.9.4",
            "haeo_version": "0.1.0",
            "timezone": "UTC",
            # No ``timestamp`` — migration synthesizes one.
        },
        "info": {
            "diagnostic_request_time": "2025-10-05T10:59:22+00:00",
            "diagnostic_target_time": None,
            "optimization_start_time": "2025-10-05T10:59:21.998507+00:00",
            "optimization_end_time": "2025-10-05T10:59:22.100000+00:00",
            "horizon_start": "2025-10-05T11:00:00+00:00",
        },
        "config": {
            "minor_version": 3,
            "version": 1,
            CONF_TIER_1_COUNT: 5,
            CONF_TIER_1_DURATION: 1,
            CONF_TIER_2_COUNT: 11,
            CONF_TIER_2_DURATION: 5,
            CONF_TIER_3_COUNT: 46,
            CONF_TIER_3_DURATION: 30,
            CONF_TIER_4_COUNT: 48,
            CONF_TIER_4_DURATION: 60,
            "participants": {},
        },
        "inputs": [
            {
                "entity_id": "sensor.foo",
                "state": "1.0",
                "last_updated": "2025-10-05T10:59:00+00:00",
                "attributes": {},
            },
        ],
        "outputs": {},
    }


def test_detect_schema_version_defaults_to_1() -> None:
    """A capture with no ``schema_version`` key is treated as v1."""
    assert detect_schema_version({"environment": {}}) == 1
    assert detect_schema_version({"schema_version": 2, "environment": {}}) == 2


def test_detect_schema_version_rejects_non_int() -> None:
    """Non-integer ``schema_version`` is a programming/fixture error."""
    with pytest.raises(TypeError):
        detect_schema_version({"schema_version": "1.0"})


def test_migrate_v1_synthesizes_environment_timestamp_from_optimization_start() -> None:
    """v1 captures without ``environment.timestamp`` inherit the optimization start time."""
    data = _v1_capture()
    migrated = migrate_scenario(data)

    assert migrated["schema_version"] == DIAGNOSTICS_SCHEMA_VERSION
    assert migrated["environment"]["timestamp"] == "2025-10-05T10:59:21.998507+00:00"


def test_migrate_v1_falls_back_to_max_input_last_updated() -> None:
    """Lacking an ``info`` timestamp, the latest input ``last_updated`` is used."""
    data = _v1_capture()
    # Strip the info fields that would normally supply the timestamp.
    data["info"]["optimization_start_time"] = ""
    data["info"]["diagnostic_target_time"] = None
    data["inputs"] = [
        {"entity_id": "sensor.a", "state": "1", "last_updated": "2025-10-05T10:00:00+00:00"},
        {"entity_id": "sensor.b", "state": "2", "last_updated": "2025-10-05T10:30:00+00:00"},
    ]

    migrated = migrate_scenario(data)

    assert migrated["environment"]["timestamp"] == "2025-10-05T10:30:00+00:00"


def test_migrate_v1_promotes_flat_tier_fields_into_tiers_section() -> None:
    """v1's flat ``tier_N_*`` fields are moved under ``config["tiers"]``."""
    migrated = migrate_scenario(_v1_capture())
    config = migrated["config"]

    # Flat fields gone from the root.
    for field in (
        CONF_TIER_1_COUNT,
        CONF_TIER_1_DURATION,
        CONF_TIER_2_COUNT,
        CONF_TIER_2_DURATION,
        CONF_TIER_3_COUNT,
        CONF_TIER_3_DURATION,
        CONF_TIER_4_COUNT,
        CONF_TIER_4_DURATION,
    ):
        assert field not in config, f"{field} should have been moved into tiers"

    tiers = config[HUB_SECTION_TIERS]
    assert tiers[CONF_TIER_1_COUNT] == 5
    assert tiers[CONF_TIER_4_DURATION] == 60

    # Structural sections exist even when empty.
    assert config[HUB_SECTION_COMMON] == {}
    assert config[HUB_SECTION_ADVANCED] == {}

    # Non-tier fields stay where they were.
    assert config["version"] == 1
    assert config["minor_version"] == 3


def test_migrate_does_not_mutate_input() -> None:
    """Migration works on a copy so callers can safely reuse their payload."""
    original = _v1_capture()
    snapshot = json.loads(json.dumps(original))  # deep copy via JSON
    migrate_scenario(original)
    assert original == snapshot, "migrate_scenario must not mutate its argument"


def test_migrate_v2_capture_is_noop() -> None:
    """A capture already at the current schema version passes through unchanged."""
    current = {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "environment": {
            "ha_version": "2026.1.1",
            "haeo_version": "0.4.0",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "timezone": "UTC",
        },
        "info": {},
        "config": {
            HUB_SECTION_COMMON: {},
            HUB_SECTION_TIERS: {CONF_TIER_1_COUNT: 1, CONF_TIER_1_DURATION: 60},
            HUB_SECTION_ADVANCED: {},
            "participants": {},
        },
        "inputs": [],
        "outputs": {},
    }

    migrated = migrate_scenario(current)
    assert migrated == current


def test_migrate_rejects_future_schema_version() -> None:
    """Captures from a newer schema raise rather than silently downgrading."""
    data = {"schema_version": DIAGNOSTICS_SCHEMA_VERSION + 1, "environment": {}}
    with pytest.raises(ValueError, match="newer than this code"):
        migrate_scenario(data)


def test_roundtrip_through_json_matches_migration_idempotence() -> None:
    """Dump → load → migrate of a current capture should be stable.

    This mirrors what the scenario loader does: it reads JSON from disk, runs
    it through the migration chain, and the result must be JSON-serializable
    and idempotent under a second migration pass.
    """
    capture = {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "environment": {
            "ha_version": "2026.1.1",
            "haeo_version": "0.4.0",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "timezone": "UTC",
        },
        "info": {
            "diagnostic_request_time": "2026-01-01T00:00:00+00:00",
            "diagnostic_target_time": None,
            "optimization_start_time": "2026-01-01T00:00:00+00:00",
            "optimization_end_time": "2026-01-01T00:00:01+00:00",
            "horizon_start": "2026-01-01T00:00:00+00:00",
        },
        "config": _jsonify(
            {
                HUB_SECTION_COMMON: MappingProxyType({"name": "Hub"}),
                HUB_SECTION_TIERS: MappingProxyType({CONF_TIER_1_COUNT: 2, CONF_TIER_1_DURATION: 60}),
                HUB_SECTION_ADVANCED: {},
                "participants": {},
                "version": 1,
                "minor_version": 3,
            },
        ),
        "inputs": [],
        "outputs": {},
    }

    dumped = json.dumps(capture)
    loaded = json.loads(dumped)
    once = migrate_scenario(loaded)
    twice = migrate_scenario(once)

    assert once == twice == capture


def test_scenarios_on_disk_migrate_cleanly() -> None:
    """Every bundled scenario* capture must survive the migration pipeline.

    This guards against a drive-by migration breaking the existing fixtures —
    we don't rewrite them, we just verify the in-memory result is schema-valid.
    """
    scenarios_dir = Path(__file__).parent
    scenario_paths = sorted(
        p
        for p in scenarios_dir.glob("scenario*/")
        if (p / "config.json").exists() and (p / "environment.json").exists()
    )
    assert scenario_paths, "no scenario fixtures discovered"

    for scenario in scenario_paths:
        raw: dict[str, Any] = {}
        for key in ("config", "environment", "inputs", "outputs"):
            path = scenario / f"{key}.json"
            if path.exists():
                with path.open() as f:
                    raw[key] = json.load(f)

        migrated = migrate_scenario(raw)
        assert migrated["schema_version"] == DIAGNOSTICS_SCHEMA_VERSION
        assert "timestamp" in migrated["environment"], f"{scenario.name}: environment.timestamp not synthesized"
        if "config" in migrated:
            assert HUB_SECTION_TIERS in migrated["config"], f"{scenario.name}: tiers section missing after migration"
