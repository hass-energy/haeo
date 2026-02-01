"""Node element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    SECTION_ADVANCED,
    SECTION_DETAILS,
    AdvancedConfig,
    AdvancedData,
    DetailsConfig,
    DetailsData,
)

ELEMENT_TYPE: Final = "node"

CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IS_SOURCE, CONF_IS_SINK})


class NodeConfigSchema(TypedDict):
    """Node element configuration as stored in Home Assistant."""

    element_type: Literal["node"]
    details: DetailsConfig
    advanced: AdvancedConfig


class NodeConfigData(TypedDict):
    """Node element configuration with loaded values."""

    element_type: Literal["node"]
    details: DetailsData
    advanced: AdvancedData


__all__ = [
    "CONF_IS_SINK",
    "CONF_IS_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_DETAILS",
    "NodeConfigData",
    "NodeConfigSchema",
]
