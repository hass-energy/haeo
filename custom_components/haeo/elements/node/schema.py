"""Node element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ELEMENT_TYPE: Final = "node"

# Configuration field names
CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_ADVANCED: Final = "advanced"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IS_SOURCE, CONF_IS_SINK})


class NodeBasicConfig(TypedDict):
    """Basic configuration for node elements."""

    name: str


class NodeAdvancedConfig(TypedDict, total=False):
    """Advanced configuration for node elements."""

    is_source: bool
    is_sink: bool


class NodeConfigSchema(TypedDict):
    """Node element configuration as stored in Home Assistant.

    In standard mode, nodes are pure junctions (is_source=False, is_sink=False).
    In advanced mode, is_source and is_sink can be configured to create:
    - Grid-like nodes (is_source=True, is_sink=True): Can import and export power
    - Load-like nodes (is_source=False, is_sink=True): Can only consume power
    - Source-like nodes (is_source=True, is_sink=False): Can only produce power
    - Pure junctions (is_source=False, is_sink=False): Power must balance
    """

    element_type: Literal["node"]
    basic: NodeBasicConfig
    advanced: NodeAdvancedConfig


class NodeBasicData(TypedDict):
    """Loaded basic values for node elements."""

    name: str


class NodeAdvancedData(TypedDict, total=False):
    """Loaded advanced values for node elements."""

    is_source: bool
    is_sink: bool


class NodeConfigData(TypedDict):
    """Node element configuration with loaded values.

    Data mode is identical to schema mode for nodes (no sensor loading needed).
    """

    element_type: Literal["node"]
    basic: NodeBasicData
    advanced: NodeAdvancedData
