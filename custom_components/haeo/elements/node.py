"""Network node element configuration for HAEO integration."""

from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.schema.fields import NameFieldData, NameFieldSchema

ELEMENT_TYPE: Final = "node"


class NodeConfigSchema(TypedDict):
    """Node element configuration."""

    element_type: Literal["node"]
    name: NameFieldSchema


class NodeConfigData(TypedDict):
    """Node element configuration."""

    element_type: Literal["node"]
    name: NameFieldData


CONFIG_DEFAULTS: dict[str, Any] = {}


def model_description(_config: NodeConfigData) -> str:
    """Generate model description string for node element."""
    return "Node"
