"""Node element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ELEMENT_TYPE: Final = "node"

# Configuration field names
CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"


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
    name: str
    is_source: NotRequired[bool]
    is_sink: NotRequired[bool]


class NodeConfigData(TypedDict):
    """Node element configuration with loaded values.

    Data mode is identical to schema mode for nodes (no sensor loading needed).
    """

    element_type: Literal["node"]
    name: str
    is_source: bool
    is_sink: bool
