"""Node element schema definitions.

A node is a pure junction: power flowing in equals power flowing out.
It has no configuration beyond its name.
"""

from typing import Final, Literal

from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.sections import CommonConfig, CommonData

ELEMENT_TYPE = ElementType.NODE

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class NodeConfigSchema(CommonConfig):
    """Node element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.NODE]


class NodeConfigData(CommonData):
    """Node element configuration with loaded values."""

    element_type: Literal[ElementType.NODE]


__all__ = [
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "NodeConfigData",
    "NodeConfigSchema",
]
