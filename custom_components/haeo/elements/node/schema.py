"""Node element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.switch import SwitchEntityDescription

from custom_components.haeo.elements.input_fields import InputFieldInfo

ELEMENT_TYPE: Final = "node"

# Configuration field names
CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"

# Default values for optional fields
DEFAULTS: Final[dict[str, bool]] = {
    CONF_IS_SOURCE: False,
    CONF_IS_SINK: False,
}

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo[SwitchEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_IS_SOURCE,
        entity_description=SwitchEntityDescription(
            key=CONF_IS_SOURCE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_IS_SOURCE}",
        ),
        output_type="status",
        default=False,
    ),
    InputFieldInfo(
        field_name=CONF_IS_SINK,
        entity_description=SwitchEntityDescription(
            key=CONF_IS_SINK,
            translation_key=f"{ELEMENT_TYPE}_{CONF_IS_SINK}",
        ),
        output_type="status",
        default=False,
    ),
)


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
