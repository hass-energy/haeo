"""Pure config transformation logic for v1.4 migration (junction-only nodes)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements import node

# Node role fields that v1.4 removes. Nodes are always pure junctions from v1.4 on.
NODE_SECTION_ROLE: Final = "role"
NODE_ROLE_FIELDS: Final[tuple[str, ...]] = ("is_source", "is_sink")


def migrate_element_config(data: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate element config to v1.4.

    Strips the source/sink role from node elements, turning every node into a
    pure junction. A node acting as a source or sink gave the optimizer free,
    unlimited power or an unlimited free dump, which it could exploit to
    fabricate profit through priced connections.
    """
    migrated = dict(data)
    if migrated.get(CONF_ELEMENT_TYPE) == node.ELEMENT_TYPE:
        migrated.pop(NODE_SECTION_ROLE, None)
    return migrated


__all__ = ["NODE_ROLE_FIELDS", "NODE_SECTION_ROLE", "migrate_element_config"]
