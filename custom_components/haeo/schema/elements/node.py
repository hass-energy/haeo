"""Node element schema definitions."""

from typing import Annotated, Final, Literal, TypedDict

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.sections import SECTION_COMMON, CommonConfig, CommonData
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.field_hints import FieldHint, SectionHints

ELEMENT_TYPE = ElementType.NODE

SECTION_ROLE: Final = "role"

CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IS_SOURCE, CONF_IS_SINK})


class RoleConfig(TypedDict, total=False):
    """Role configuration for node behavior."""

    is_source: bool
    is_sink: bool


class RoleData(TypedDict, total=False):
    """Loaded role values for node behavior."""

    is_source: bool
    is_sink: bool


class NodeConfigSchema(TypedDict):
    """Node element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.NODE]
    common: CommonConfig
    role: Annotated[
        RoleConfig,
        SectionHints(
            {
                CONF_IS_SOURCE: FieldHint(
                    output_type=OutputType.STATUS,
                    default_mode="value",
                    default_value=False,
                ),
                CONF_IS_SINK: FieldHint(
                    output_type=OutputType.STATUS,
                    default_mode="value",
                    default_value=False,
                ),
            }
        ),
    ]


class NodeConfigData(TypedDict):
    """Node element configuration with loaded values."""

    element_type: Literal[ElementType.NODE]
    common: CommonData
    role: RoleData


__all__ = [
    "CONF_IS_SINK",
    "CONF_IS_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_ROLE",
    "NodeConfigData",
    "NodeConfigSchema",
    "RoleConfig",
    "RoleData",
]
