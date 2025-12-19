"""Load element configuration for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import (
    ElementNameFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PowerSensorsFieldData,
    PowerSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"

type LoadOutputName = Literal[
    "load_power",
    "load_forecast_limit_price",
]
LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        # Shadow prices
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
    )
)

type LoadDeviceName = Literal["load"]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := ELEMENT_TYPE,),
)


class LoadConfigSchema(TypedDict):
    """Load element configuration."""

    element_type: Literal["load"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Connection ID that load connects to
    forecast: PowerSensorsFieldSchema


class LoadConfigData(TypedDict):
    """Load element configuration."""

    element_type: Literal["load"]
    name: NameFieldData
    connection: ElementNameFieldSchema  # Connection ID that load connects to
    forecast: PowerSensorsFieldData


CONFIG_DEFAULTS: dict[str, Any] = {}


def create_model_elements(config: LoadConfigData) -> list[dict[str, Any]]:
    """Create model elements for Load configuration."""

    elements: list[dict[str, Any]] = [
        # Create SourceSink for the load (sink only - consumes power)
        {"element_type": "source_sink", "name": config["name"], "is_source": False, "is_sink": True},
        # Create Connection from node to load (power flows TO the load)
        {
            "element_type": "connection",
            "name": f"{config['name']}:connection",
            "source": config["name"],
            "target": config["connection"],
            "max_power_source_target": 0.0,
            "max_power_target_source": config["forecast"],
            "fixed_power": True,
        },
    ]

    return elements


def outputs(
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]], _config: LoadConfigData
) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
    """Provide state updates for load output sensors."""
    connection = outputs[f"{name}:connection"]

    load_updates: dict[LoadOutputName, OutputData] = {
        # Output sensors from optimization
        LOAD_POWER: replace(connection[CONNECTION_POWER_TARGET_SOURCE], type=OUTPUT_TYPE_POWER),
        LOAD_FORECAST_LIMIT_PRICE: connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE],
    }

    return {LOAD_DEVICE_LOAD: load_updates}
