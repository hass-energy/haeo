"""Network and connection element configurations for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_MAX_SOURCE_TARGET as MODEL_CONNECTION_POWER_MAX_SOURCE_TARGET,
)
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_MAX_TARGET_SOURCE as MODEL_CONNECTION_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_SOURCE_TARGET as MODEL_CONNECTION_POWER_SOURCE_TARGET,
)
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_TARGET_SOURCE as MODEL_CONNECTION_POWER_TARGET_SOURCE,
)
from custom_components.haeo.model.connection import (
    CONNECTION_PRICE_SOURCE_TARGET as MODEL_CONNECTION_PRICE_SOURCE_TARGET,
)
from custom_components.haeo.model.connection import (
    CONNECTION_PRICE_TARGET_SOURCE as MODEL_CONNECTION_PRICE_TARGET_SOURCE,
)
from custom_components.haeo.model.connection import (
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET as MODEL_CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
)
from custom_components.haeo.model.connection import (
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE as MODEL_CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.connection import CONNECTION_TIME_SLICE as MODEL_CONNECTION_TIME_SLICE
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

# Connection-specific sensor names (for translation/output mapping)
CONNECTION_POWER_SOURCE_TARGET: Final = "connection_power_source_target"
CONNECTION_POWER_TARGET_SOURCE: Final = "connection_power_target_source"
CONNECTION_POWER_MAX_SOURCE_TARGET: Final = "connection_power_max_source_target"
CONNECTION_POWER_MAX_TARGET_SOURCE: Final = "connection_power_max_target_source"
CONNECTION_PRICE_SOURCE_TARGET: Final = "connection_price_source_target"
CONNECTION_PRICE_TARGET_SOURCE: Final = "connection_price_target_source"
CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: Final = "connection_shadow_power_max_source_target"
CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: Final = "connection_shadow_power_max_target_source"
CONNECTION_TIME_SLICE: Final = "connection_time_slice"

type ConnectionOutputName = Literal[
    "connection_power_source_target",
    "connection_power_target_source",
    "connection_power_max_source_target",
    "connection_power_max_target_source",
    "connection_price_source_target",
    "connection_price_target_source",
    "connection_shadow_power_max_source_target",
    "connection_shadow_power_max_target_source",
    "connection_time_slice",
]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_SOURCE_TARGET,
        CONNECTION_POWER_TARGET_SOURCE,
        CONNECTION_POWER_MAX_SOURCE_TARGET,
        CONNECTION_POWER_MAX_TARGET_SOURCE,
        CONNECTION_PRICE_SOURCE_TARGET,
        CONNECTION_PRICE_TARGET_SOURCE,
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


CONFIG_DEFAULTS: dict[str, Any] = {}


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
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
) -> Mapping[str, Mapping[ConnectionOutputName, OutputData]]:
    """Map model outputs to connection-specific output names."""
    connection = outputs[name]

    connection_outputs: dict[ConnectionOutputName, OutputData] = {
        CONNECTION_POWER_SOURCE_TARGET: connection[MODEL_CONNECTION_POWER_SOURCE_TARGET],
        CONNECTION_POWER_TARGET_SOURCE: connection[MODEL_CONNECTION_POWER_TARGET_SOURCE],
    }

    # Optional outputs (only present if configured)
    if MODEL_CONNECTION_POWER_MAX_SOURCE_TARGET in connection:
        connection_outputs[CONNECTION_POWER_MAX_SOURCE_TARGET] = connection[MODEL_CONNECTION_POWER_MAX_SOURCE_TARGET]
        connection_outputs[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = connection[
            MODEL_CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET
        ]

    if MODEL_CONNECTION_POWER_MAX_TARGET_SOURCE in connection:
        connection_outputs[CONNECTION_POWER_MAX_TARGET_SOURCE] = connection[MODEL_CONNECTION_POWER_MAX_TARGET_SOURCE]
        connection_outputs[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = connection[
            MODEL_CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE
        ]

    if MODEL_CONNECTION_PRICE_SOURCE_TARGET in connection:
        connection_outputs[CONNECTION_PRICE_SOURCE_TARGET] = connection[MODEL_CONNECTION_PRICE_SOURCE_TARGET]

    if MODEL_CONNECTION_PRICE_TARGET_SOURCE in connection:
        connection_outputs[CONNECTION_PRICE_TARGET_SOURCE] = connection[MODEL_CONNECTION_PRICE_TARGET_SOURCE]

    if MODEL_CONNECTION_TIME_SLICE in connection:
        connection_outputs[CONNECTION_TIME_SLICE] = connection[MODEL_CONNECTION_TIME_SLICE]

    return {name: connection_outputs}
