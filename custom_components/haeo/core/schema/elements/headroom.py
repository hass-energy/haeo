"""Headroom element schema definitions.

Headroom keeps enough empty space in a group of batteries to absorb the surplus
of a group of generators, less a group of loads, over a set length of time.
It shares the reserve's configuration.
"""

from typing import Final, Literal

from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.reserve import StorageRequirementConfig, StorageRequirementData

ELEMENT_TYPE = ElementType.HEADROOM

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class HeadroomConfigSchema(StorageRequirementConfig):
    """Headroom element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.HEADROOM]


class HeadroomConfigData(StorageRequirementData):
    """Headroom element configuration with loaded values."""

    element_type: Literal[ElementType.HEADROOM]


__all__ = [
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "HeadroomConfigData",
    "HeadroomConfigSchema",
]
