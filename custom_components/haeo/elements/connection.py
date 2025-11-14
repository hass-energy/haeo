"""Network and connection element configurations for HAEO integration."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.schema.fields import (
    ElementNameFieldData,
    ElementNameFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PercentageSensorFieldData,
    PercentageSensorFieldSchema,
    PowerSensorFieldData,
    PowerSensorFieldSchema,
    PriceSensorsFieldData,
    PriceSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "connection"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONF_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"
CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration."""

    element_type: Literal["connection"]
    name: NameFieldSchema
    source: ElementNameFieldSchema
    target: ElementNameFieldSchema

    # Optional fields
    max_power_source_target: NotRequired[PowerSensorFieldSchema]
    max_power_target_source: NotRequired[PowerSensorFieldSchema]
    efficiency_source_target: NotRequired[PercentageSensorFieldSchema]
    efficiency_target_source: NotRequired[PercentageSensorFieldSchema]
    price_source_target: NotRequired[PriceSensorsFieldSchema]
    price_target_source: NotRequired[PriceSensorsFieldSchema]


class ConnectionConfigData(TypedDict):
    """Connection element configuration."""

    element_type: Literal["connection"]
    name: NameFieldData
    source: ElementNameFieldData
    target: ElementNameFieldData

    # Optional fields
    max_power_source_target: NotRequired[PowerSensorFieldData]
    max_power_target_source: NotRequired[PowerSensorFieldData]
    efficiency_source_target: NotRequired[PercentageSensorFieldData]
    efficiency_target_source: NotRequired[PercentageSensorFieldData]
    price_source_target: NotRequired[PriceSensorsFieldData]
    price_target_source: NotRequired[PriceSensorsFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {}
