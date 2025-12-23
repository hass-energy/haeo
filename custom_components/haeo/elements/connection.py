"""Network and connection element configurations for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import OUTPUT_TYPE_POWER_FLOW, ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
)
from custom_components.haeo.model.output_data import OutputData
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

# Output names for connection elements
type ConnectionOutputName = Literal[
    "connection_power_source_target",
    "connection_power_target_source",
    "connection_power_active",
    "connection_shadow_power_max_source_target",
    "connection_shadow_power_max_target_source",
    "connection_time_slice",
]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_SOURCE_TARGET,
        CONNECTION_POWER_TARGET_SOURCE,
        CONNECTION_POWER_ACTIVE := "connection_power_active",
        # Shadow prices
        CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
        CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
        CONNECTION_TIME_SLICE,
    )
)


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


type ConnectionDeviceName = Literal["connection"]

CONNECTION_DEVICE_NAMES: Final[frozenset[ConnectionDeviceName]] = frozenset(
    (CONNECTION_DEVICE_CONNECTION := ELEMENT_TYPE,),
)


def create_model_elements(config: ConnectionConfigData) -> list[dict[str, Any]]:
    """Create model elements for Connection configuration."""
    return [
        {
            "element_type": "connection",
            "name": config["name"],
            "source": config["source"],
            "target": config["target"],
            "max_power_source_target": config.get("max_power_source_target"),
            "max_power_target_source": config.get("max_power_target_source"),
            "efficiency_source_target": config.get("efficiency_source_target"),
            "efficiency_target_source": config.get("efficiency_target_source"),
            "price_source_target": config.get("price_source_target"),
            "price_target_source": config.get("price_target_source"),
        }
    ]


def outputs(
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]], config: ConnectionConfigData
) -> Mapping[ConnectionDeviceName, Mapping[ConnectionOutputName, OutputData]]:
    """Provide state updates for connection output sensors."""
    connection = outputs[name]

    connection_outputs: dict[ConnectionOutputName, OutputData] = {
        CONNECTION_POWER_SOURCE_TARGET: connection[CONNECTION_POWER_SOURCE_TARGET],
        CONNECTION_POWER_TARGET_SOURCE: connection[CONNECTION_POWER_TARGET_SOURCE],
    }

    # Active connection power (source_target - target_source)
    connection_outputs[CONNECTION_POWER_ACTIVE] = replace(
        connection[CONNECTION_POWER_SOURCE_TARGET],
        values=[
            st - ts
            for st, ts in zip(
                connection[CONNECTION_POWER_SOURCE_TARGET].values,
                connection[CONNECTION_POWER_TARGET_SOURCE].values,
                strict=True,
            )
        ],
        direction=None,
        type=OUTPUT_TYPE_POWER_FLOW,
    )

    # Shadow prices for power limits (only if limits are set)
    if CONF_MAX_POWER_SOURCE_TARGET in config:
        connection_outputs[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = connection[
            CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET
        ]

    if CONF_MAX_POWER_TARGET_SOURCE in config:
        connection_outputs[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = connection[
            CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE
        ]

    if CONNECTION_TIME_SLICE in connection:
        connection_outputs[CONNECTION_TIME_SLICE] = connection[CONNECTION_TIME_SLICE]

    return {CONNECTION_DEVICE_CONNECTION: connection_outputs}


__all__ = [
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_SOURCE",
    "CONF_TARGET",
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_ACTIVE",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET",
    "CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
    "ELEMENT_TYPE",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
    "ConnectionOutputName",
    "create_model_elements",
    "outputs",
]
