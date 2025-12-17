"""Photovoltaics element configuration for HAEO integration."""

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

ELEMENT_TYPE: Final = "photovoltaics"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_PRICE_CONSUMPTION: Final = "price_consumption"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"

type PhotovoltaicsOutputName = Literal[
    "photovoltaics_power",
    "photovoltaics_price",
    # Shadow prices
    "photovoltaics_forecast_limit",
]

PHOTOVOLTAIC_OUTPUT_NAMES: Final[frozenset[PhotovoltaicsOutputName]] = frozenset(
    (
        PHOTOVOLTAICS_POWER := "photovoltaics_power",
        PHOTOVOLTAICS_PRICE := "photovoltaics_price",
        # Shadow prices
        PHOTOVOLTAICS_FORECAST_LIMIT := "photovoltaics_forecast_limit",
    )
)

type PhotovoltaicsDeviceName = Literal["photovoltaics"]

PHOTOVOLTAICS_DEVICE_NAMES: Final[frozenset[PhotovoltaicsDeviceName]] = frozenset(
    (PHOTOVOLTAICS_DEVICE_PHOTOVOLTAICS := ELEMENT_TYPE,)
)


class PhotovoltaicsConfigSchema(TypedDict):
    """Photovoltaics element configuration."""

    element_type: Literal["photovoltaics"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Node to connect to
    forecast: PowerSensorsFieldSchema

    # Optional fields
    price_production: NotRequired[PriceFieldSchema]
    curtailment: NotRequired[BooleanFieldSchema]


class PhotovoltaicsConfigData(TypedDict):
    """Photovoltaics element configuration."""

    element_type: Literal["photovoltaics"]
    name: NameFieldData
    connection: ElementNameFieldData  # Node to connect to
    forecast: PowerSensorsFieldData

    # Optional fields
    price_production: NotRequired[PriceFieldData]
    curtailment: NotRequired[BooleanFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_CURTAILMENT: True,
}


def create_model_elements(config: PhotovoltaicsConfigData) -> list[dict[str, Any]]:
    """Create model elements for Photovoltaics configuration."""

    return [
        {"element_type": "source_sink", "name": config["name"], "is_source": True, "is_sink": False},
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


def updates(
    name: str, model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]], _config: PhotovoltaicsConfigData
) -> Mapping[PhotovoltaicsDeviceName, Mapping[PhotovoltaicsOutputName, OutputData]]:
    """Provide state updates for photovoltaics output sensors."""
    connection = model_outputs[f"{name}:connection"]

    pv_updates: dict[PhotovoltaicsOutputName, OutputData] = {
        # Output sensors from optimization
        PHOTOVOLTAICS_POWER: replace(connection[CONNECTION_POWER_SOURCE_TARGET], type=OUTPUT_TYPE_POWER),
        PHOTOVOLTAICS_FORECAST_LIMIT: connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET],
    }

    return {PHOTOVOLTAICS_DEVICE_PHOTOVOLTAICS: pv_updates}
