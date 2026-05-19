"""Pure config transformation logic for v1.4 migration.

Adds an empty ``threshold`` section to existing Load configs so that the
new threshold-price field is present (and defaultable) on previously
saved entries. Other element types are unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.core.schema.elements import load as load_schema
from custom_components.haeo.core.schema.sections import CONF_THRESHOLD_PRICE, SECTION_THRESHOLD


@dataclass(frozen=True)
class ElementMigrationStep:
    """Single element-config migration step."""

    name: str
    transform: Callable[[Mapping[str, Any]], dict[str, Any] | None]


def migrate_element_config(data: Mapping[str, Any]) -> dict[str, Any] | None:
    """Migrate element config through all v1.4 schema migration steps."""
    if not ELEMENT_MIGRATION_STEPS:
        return dict(data)

    migrated: Mapping[str, Any] = data
    for step in ELEMENT_MIGRATION_STEPS:
        transformed = step.transform(migrated)
        if transformed is None:
            return None
        migrated = transformed
    return dict(migrated)


def _add_threshold_section_to_load(data: Mapping[str, Any]) -> dict[str, Any] | None:
    """Ensure Load configs have a ``threshold`` section with a default 0 price."""
    out = dict(data)
    if out.get(CONF_ELEMENT_TYPE) != load_schema.ELEMENT_TYPE:
        return out

    existing = out.get(SECTION_THRESHOLD)
    threshold = dict(existing) if isinstance(existing, Mapping) else {}
    threshold.setdefault(CONF_THRESHOLD_PRICE, as_constant_value(0.0))
    out[SECTION_THRESHOLD] = threshold
    return out


ELEMENT_MIGRATION_STEPS: tuple[ElementMigrationStep, ...] = (
    ElementMigrationStep(name="load_add_threshold_section_v1_4", transform=_add_threshold_section_to_load),
)
