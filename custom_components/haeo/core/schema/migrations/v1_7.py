"""Pure config transformation logic for the v1.7 migration.

A buffer's loads and generation become power sensor fields, where a sensor of
one of the hub's own elements stands for that element. Each element a buffer
listed by name is named by one of its sensors instead, or directly in the
field's ``elements`` when it has no sensor, as a diagnostics export names them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import CONF_GENERATION, CONF_LOADS, SECTION_PARTICIPANTS
from custom_components.haeo.core.schema.migrations import section_dict

# The config entry minor version these migrations bring an entry to
MINOR_VERSION: Final = 7

_ROLES: Final = (CONF_LOADS, CONF_GENERATION)


def _listed_names(value: object) -> list[str] | None:
    """Return the element names a participant list holds, or None when it is not a list of names."""
    if not isinstance(value, (list, tuple)) or not all(isinstance(name, str) for name in value):
        return None
    return list(value)


def migrate_element_config(
    config: Mapping[str, object], element_sensors: Mapping[str, str]
) -> dict[str, object] | None:
    """Return a buffer config naming its loads and generation by sensor, or None when the config needs no change.

    Args:
        config: Element config as stored.
        element_sensors: Map of element name to the sensor that stands for it.
            An element with no sensor is named directly.

    """
    if config.get(CONF_ELEMENT_TYPE) != ElementType.BUFFER:
        return None
    participants = section_dict(config, SECTION_PARTICIPANTS)
    for role in _ROLES:
        names = _listed_names(participants.get(role))
        if names is None:
            continue
        del participants[role]
        if not names:
            continue
        value = as_entity_value([element_sensors[name] for name in names if name in element_sensors])
        if unnamed := [name for name in names if name not in element_sensors]:
            participants[role] = {**value, "elements": unnamed}
        else:
            participants[role] = value
    return {**config, SECTION_PARTICIPANTS: participants}


__all__ = ["MINOR_VERSION", "migrate_element_config"]
