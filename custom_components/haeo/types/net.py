"""Network node element configuration for HAEO integration."""

from typing import Any, Literal, TypedDict

from custom_components.haeo.schema.fields import NameFieldData, NameFieldSchema


class NetConfigSchema(TypedDict):
    """Net element configuration."""

    element_type: Literal["net"]
    name: NameFieldSchema


class NetConfigData(TypedDict):
    """Net element configuration."""

    element_type: Literal["net"]
    name: NameFieldData


NET_CONFIG_DEFAULTS: dict[str, Any] = {}
