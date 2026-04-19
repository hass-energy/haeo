"""Migrations for legacy HAEO diagnostics scenario captures.

Scenario fixtures under ``tests/scenarios/`` are loaded diagnostics snapshots
that may have been captured against an older version of the collector schema.
Rather than rewriting the files on disk every time the schema moves, this module
defines a chain of in-memory migration functions keyed by their *source*
version. :func:`migrate_scenario` loads a scenario blob, detects its
``schema_version`` (treating a missing field as ``1``), and applies successive
migrations until it matches :data:`DIAGNOSTICS_SCHEMA_VERSION`.

Adding a new migration is a matter of appending a ``v{n} -> v{n+1}`` entry to
:data:`_MIGRATIONS` — the loader will pick it up automatically.

The migrations here deliberately do as little work as possible: they only
synthesize / move fields that old captures lacked, and leave the rest of the
payload untouched.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import copy
from typing import Any

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

ScenarioData = dict[str, Any]
"""Alias for a mutable scenario diagnostics blob (split-file reconstruction)."""


_FLAT_TIER_FIELDS: tuple[str, ...] = (
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
)


def _max_input_timestamp(inputs: Iterable[Any]) -> str | None:
    """Return the latest ``last_updated`` across input states (or None).

    ``inputs`` is typed as ``Iterable[Any]`` rather than ``Iterable[Mapping]``
    because it comes straight off disk: callers have no way to narrow the
    JSON-loaded shape before handing it in.
    """
    candidates: list[str] = []
    for state in inputs:
        if not isinstance(state, Mapping):
            continue
        last_updated = state.get("last_updated")
        if isinstance(last_updated, str):
            candidates.append(last_updated)
    return max(candidates) if candidates else None


def _migrate_v1_to_v2(data: ScenarioData) -> ScenarioData:
    """Bring a pre-``schema_version`` capture up to v2.

    Changes applied:

    1. Synthesize ``environment.timestamp`` if missing. Prefer
       ``info.optimization_start_time`` (added in the same schema bump) and
       fall back to the max ``last_updated`` across ``inputs`` — which is the
       wall-clock time the scenario was frozen at in practice.
    2. Promote flat ``tier_{n}_{count,duration}`` fields out of ``config`` root
       into a nested ``config["tiers"]`` section, matching the post-refactor
       ``OptimizationContext.hub_config`` layout. Also ensure ``common`` and
       ``advanced`` sections exist so the test harness can rely on them.
    """
    environment = data.setdefault("environment", {})
    if "timestamp" not in environment:
        info = data.get("info", {}) if isinstance(data.get("info"), Mapping) else {}
        timestamp = info.get("optimization_start_time") or info.get("diagnostic_target_time")
        if not timestamp:
            inputs = data.get("inputs", [])
            if isinstance(inputs, list):
                timestamp = _max_input_timestamp(inputs)
        if timestamp:
            environment["timestamp"] = timestamp

    config = data.get("config")
    if isinstance(config, dict):
        tiers = config.get(HUB_SECTION_TIERS)
        if not isinstance(tiers, dict):
            tiers = {}
            for field in _FLAT_TIER_FIELDS:
                if field in config:
                    tiers[field] = config.pop(field)
            if tiers:
                config[HUB_SECTION_TIERS] = tiers
        config.setdefault(HUB_SECTION_COMMON, {})
        config.setdefault(HUB_SECTION_ADVANCED, {})

    return data


# Ordered chain of ``source_version -> migration_fn``. Each entry migrates from
# ``source_version`` to ``source_version + 1``. Adding a new migration = append
# one line here; :func:`migrate_scenario` handles the rest.
_MIGRATIONS: dict[int, Callable[[ScenarioData], ScenarioData]] = {
    1: _migrate_v1_to_v2,
}


def detect_schema_version(data: Mapping[str, Any]) -> int:
    """Return the declared ``schema_version`` of *data*, defaulting to ``1``.

    Captures from before schema versioning was introduced are all ``v1`` by
    definition.
    """
    version = data.get("schema_version", 1)
    if not isinstance(version, int):
        msg = f"Invalid schema_version: {version!r} (expected int)"
        raise TypeError(msg)
    return version


def migrate_scenario(data: Mapping[str, Any]) -> ScenarioData:
    """Return a copy of *data* migrated up to :data:`DIAGNOSTICS_SCHEMA_VERSION`.

    The input is not mutated; we work on a shallow copy of the outer dict and
    let each migration do in-place edits of the copy. Migrations can assume
    they're free to mutate their argument.

    Raises:
        ValueError: If the capture declares a schema newer than this code
            understands, or if a migration is missing from the chain.

    """
    # Deep-copy so migrations are free to mutate nested dicts without scribbling
    # back into the caller's payload (important when the same capture is loaded
    # once per scenario and migrated in-place by the fixture).
    current = copy.deepcopy(dict(data))
    version = detect_schema_version(current)
    if version > DIAGNOSTICS_SCHEMA_VERSION:
        msg = (
            f"Scenario schema_version={version} is newer than this code "
            f"supports (max {DIAGNOSTICS_SCHEMA_VERSION}); upgrade HAEO or "
            f"re-capture the scenario."
        )
        raise ValueError(msg)

    while version < DIAGNOSTICS_SCHEMA_VERSION:
        migration = _MIGRATIONS.get(version)
        if migration is None:
            msg = f"Missing migration from schema_version={version} to {version + 1}"
            raise ValueError(msg)
        current = migration(current)
        version += 1
        current["schema_version"] = version

    return current


__all__ = [
    "DIAGNOSTICS_SCHEMA_VERSION",
    "ScenarioData",
    "detect_schema_version",
    "migrate_scenario",
]
