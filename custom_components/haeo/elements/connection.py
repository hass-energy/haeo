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


def model_description(config: ConnectionConfigSchema) -> str:
    """Generate device model string from connection configuration."""
    min_kw = config.get(CONF_MIN_POWER)
    max_kw = config.get(CONF_MAX_POWER)

    if min_kw is not None and max_kw is not None:
        return f"Connection {min_kw:.1f}kW to {max_kw:.1f}kW"
    if min_kw is not None:
        return f"Connection (min {min_kw:.1f}kW)"
    if max_kw is not None:
        return f"Connection (max {max_kw:.1f}kW)"
    return "Connection"
