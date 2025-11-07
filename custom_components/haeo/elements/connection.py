"""Network and connection element configurations for HAEO integration."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.schema.fields import (
    ElementNameFieldData,
    ElementNameFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PowerFlowFieldData,
    PowerFlowFieldSchema,
)

ELEMENT_TYPE: Final = "connection"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_MIN_POWER: Final = "min_power"
CONF_MAX_POWER: Final = "max_power"


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration."""

    element_type: Literal["connection"]
    name: NameFieldSchema
    source: ElementNameFieldSchema
    target: ElementNameFieldSchema

    # Optional fields
    min_power: NotRequired[PowerFlowFieldSchema]
    max_power: NotRequired[PowerFlowFieldSchema]


class ConnectionConfigData(TypedDict):
    """Connection element configuration."""

    element_type: Literal["connection"]
    name: NameFieldData
    source: ElementNameFieldData
    target: ElementNameFieldData

    # Optional fields
    min_power: NotRequired[PowerFlowFieldData]
    max_power: NotRequired[PowerFlowFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {}
