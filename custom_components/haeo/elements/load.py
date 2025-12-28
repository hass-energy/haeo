"""Load element configuration for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.power_connection import (
    CONNECTION_POWER_MAX_TARGET_SOURCE,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_PRICE_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.schema import Default
from custom_components.haeo.schema.fields import (
    BooleanFieldData,
    BooleanFieldSchema,
    ElementNameFieldData,
    ElementNameFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PowerSensorsFieldData,
    PowerSensorsFieldSchema,
    PriceFieldData,
    PriceFieldSchema,
)

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"
CONF_VALUE_RUNNING: Final = "value_running"
CONF_SHEDDING: Final = "shedding"

type LoadOutputName = Literal[
    "load_power",
    "load_power_possible",
    "load_value",
    "load_forecast_limit_price",
]
LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        LOAD_POWER_POSSIBLE := "load_power_possible",
        LOAD_VALUE := "load_value",
        # Shadow prices
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
    )
)

type LoadDeviceName = Literal["load"]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := ELEMENT_TYPE,),
)

# Field type aliases with defaults
SheddingFieldSchema = Annotated[BooleanFieldSchema, Default(value=True)]
SheddingFieldData = Annotated[BooleanFieldData, Default(value=True)]


class LoadConfigSchema(TypedDict):
    """Load element configuration."""

    element_type: Literal["load"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Connection ID that load connects to
    forecast: PowerSensorsFieldSchema

    # Optional fields
    value_running: NotRequired[PriceFieldSchema]
    shedding: NotRequired[SheddingFieldSchema]


class LoadConfigData(TypedDict):
    """Load element configuration."""

    element_type: Literal["load"]
    name: NameFieldData
    connection: ElementNameFieldData  # Connection ID that load connects to
    forecast: PowerSensorsFieldData

    # Optional fields
    value_running: NotRequired[PriceFieldData]
    shedding: NotRequired[SheddingFieldData]


def create_model_elements(config: LoadConfigData) -> list[dict[str, Any]]:
    """Create model elements for Load configuration."""

    connection_params: dict[str, Any] = {
        "element_type": "connection",
        "name": f"{config['name']}:connection",
        "source": config["name"],
        "target": config["connection"],
        "max_power_source_target": 0.0,
        "max_power_target_source": config["forecast"],
        "fixed_power": not config.get("shedding", True),
    }

    # Only include price_target_source if value_running is specified
    if (value_running := config.get("value_running")) is not None:
        connection_params["price_target_source"] = value_running

    elements: list[dict[str, Any]] = [
        # Create Node for the load (sink only - consumes power)
        {"element_type": "node", "name": config["name"], "is_source": False, "is_sink": True},
        # Create Connection from node to load (power flows TO the load)
        connection_params,
    ]

    return elements


def outputs(
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]], _config: LoadConfigData
) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
    """Map model outputs to load-specific output names."""

    connection = outputs[f"{name}:connection"]

    load_outputs: dict[LoadOutputName, OutputData] = {
        LOAD_POWER: replace(connection[CONNECTION_POWER_TARGET_SOURCE], type=OUTPUT_TYPE_POWER),
        LOAD_POWER_POSSIBLE: connection[CONNECTION_POWER_MAX_TARGET_SOURCE],
        # Only the max limit has meaning, the source sink power balance is always zero as it will never influence cost
        LOAD_FORECAST_LIMIT_PRICE: connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE],
    }

    if CONNECTION_PRICE_TARGET_SOURCE in connection:
        load_outputs[LOAD_VALUE] = connection[CONNECTION_PRICE_TARGET_SOURCE]

    return {LOAD_DEVICE_LOAD: load_outputs}
