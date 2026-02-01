"""Node element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import SECTION_ADVANCED, SECTION_BASIC, BasicNameConfig, BasicNameData

ELEMENT_TYPE: Final = "node"

CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IS_SOURCE, CONF_IS_SINK})


class NodeRolesConfig(TypedDict, total=False):
    """Optional node roles configuration."""

    is_source: bool
    is_sink: bool


class NodeRolesData(TypedDict, total=False):
    """Loaded node roles values."""

    is_source: bool
    is_sink: bool


class NodeConfigSchema(TypedDict):
    """Node element configuration as stored in Home Assistant."""

    element_type: Literal["node"]
    basic: BasicNameConfig
    advanced: NodeRolesConfig


class NodeConfigData(TypedDict):
    """Node element configuration with loaded values."""

    element_type: Literal["node"]
    basic: BasicNameData
    advanced: NodeRolesData


__all__ = [
    "CONF_IS_SINK",
    "CONF_IS_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_BASIC",
    "NodeConfigData",
    "NodeConfigSchema",
]
