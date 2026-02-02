"""Node element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import SECTION_COMMON, SECTION_ROLE, CommonConfig, CommonData, RoleConfig, RoleData

ELEMENT_TYPE: Final = "node"

CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IS_SOURCE, CONF_IS_SINK})


class NodeConfigSchema(TypedDict):
    """Node element configuration as stored in Home Assistant."""

    element_type: Literal["node"]
    common: CommonConfig
    role: RoleConfig


class NodeConfigData(TypedDict):
    """Node element configuration with loaded values."""

    element_type: Literal["node"]
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
]
