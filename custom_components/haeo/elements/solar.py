"""Solar element configuration for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
)
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
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

ELEMENT_TYPE: Final = "solar"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_PRICE_CONSUMPTION: Final = "price_consumption"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"

type SolarOutputName = Literal[
    "solar_power",
    "solar_price",
    # Shadow prices
    "solar_forecast_limit",
]

SOLAR_OUTPUT_NAMES: Final[frozenset[SolarOutputName]] = frozenset(
    (
        SOLAR_POWER := "solar_power",
        SOLAR_PRICE := "solar_price",
        # Shadow prices
        SOLAR_FORECAST_LIMIT := "solar_forecast_limit",
    )
)

type SolarDeviceName = Literal["solar"]

SOLAR_DEVICE_NAMES: Final[frozenset[SolarDeviceName]] = frozenset(
    (SOLAR_DEVICE_SOLAR := ELEMENT_TYPE,)
)


class SolarConfigSchema(TypedDict):
    """Solar element configuration."""

    element_type: Literal["solar"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Node to connect to
    forecast: PowerSensorsFieldSchema

    # Optional fields
    price_production: NotRequired[PriceFieldSchema]
    curtailment: NotRequired[BooleanFieldSchema]


class SolarConfigData(TypedDict):
    """Solar element configuration."""

    element_type: Literal["solar"]
    name: NameFieldData
    connection: ElementNameFieldData  # Node to connect to
    forecast: PowerSensorsFieldData

    # Optional fields
    price_production: NotRequired[PriceFieldData]
    curtailment: NotRequired[BooleanFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_CURTAILMENT: True,
}


def create_model_elements(config: SolarConfigData) -> list[dict[str, Any]]:
    """Create model elements for Solar configuration."""

    return [
        {
            "element_type": "source_sink",
            "name": config["name"],
            "is_source": True,
            "is_sink": False,
        },
        {
            "element_type": "connection",
            "name": f"{config['name']}:connection",
            "source": config["name"],
            "target": config["connection"],
            "max_power_source_target": config["forecast"],
            "max_power_target_source": 0.0,
            "fixed_power": not config.get("curtailment", True),
            "price_source_target": config.get("price_production"),
        },
    ]


def outputs(
    name: str,
    outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
    _config: SolarConfigData,
) -> Mapping[SolarDeviceName, Mapping[SolarOutputName, OutputData]]:
    """Provide state updates for solar output sensors."""
    connection = outputs[f"{name}:connection"]

    solar_outputs: dict[SolarOutputName, OutputData] = {
        SOLAR_POWER: replace(
            connection[CONNECTION_POWER_SOURCE_TARGET], type=OUTPUT_TYPE_POWER
        ),
        SOLAR_FORECAST_LIMIT: connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET],
    }

    return {SOLAR_DEVICE_SOLAR: solar_outputs}
