"""Unique IDs of HAEO entities and devices.

Entities and devices that belong to an element are keyed
``{entry_id}_{subentry_id}_{key}``, and those that belong to the hub as a whole
``{entry_id}_{key}``. Subentry IDs are ULIDs, so an element ID can be told apart
from a hub ID and read back into its subentry ID and key.
"""

from __future__ import annotations

import re
from typing import NamedTuple

_ULID = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")


class ElementUniqueId(NamedTuple):
    """The parts of an element entity or device ID that follow the config entry ID."""

    subentry_id: str
    key: str


def element_unique_id(entry_id: str, subentry_id: str, key: str) -> str:
    """Return the ID of an entity or device that belongs to an element."""
    return f"{entry_id}_{subentry_id}_{key}"


def element_output_unique_id(entry_id: str, subentry_id: str, device_name: str, output_name: str) -> str:
    """Return the ID of an output sensor on one of an element's devices."""
    return element_unique_id(entry_id, subentry_id, f"{device_name}_{output_name}")


def hub_unique_id(entry_id: str, key: str) -> str:
    """Return the ID of an entity that belongs to the hub as a whole."""
    return f"{entry_id}_{key}"


def parse_element_unique_id(entry_id: str, unique_id: str) -> ElementUniqueId | None:
    """Split an element entity or device ID of this config entry, or return None if it is not one."""
    prefix = f"{entry_id}_"
    if not unique_id.startswith(prefix):
        return None
    subentry_id, _, key = unique_id.removeprefix(prefix).partition("_")
    if not key or not _ULID.fullmatch(subentry_id):
        return None
    return ElementUniqueId(subentry_id, key)


__all__ = [
    "ElementUniqueId",
    "element_output_unique_id",
    "element_unique_id",
    "hub_unique_id",
    "parse_element_unique_id",
]
