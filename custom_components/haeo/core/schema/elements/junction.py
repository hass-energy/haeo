"""Junction element schema definitions.

A junction is a pure power balance point: power flowing in equals power flowing out.
It has no configuration beyond its name.
"""

from typing import Final, Literal

from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.sections import CommonConfig, CommonData

ELEMENT_TYPE = ElementType.JUNCTION

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class JunctionConfigSchema(CommonConfig):
    """Junction element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.JUNCTION]


class JunctionConfigData(CommonData):
    """Junction element configuration with loaded values."""

    element_type: Literal[ElementType.JUNCTION]


__all__ = [
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "JunctionConfigData",
    "JunctionConfigSchema",
]
