"""Photovoltaics element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import SOURCE_SINK_POWER_BALANCE, SOURCE_SINK_POWER_OUT
from custom_components.haeo.schema.fields import (
    BooleanFieldData,
    BooleanFieldSchema,
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
CONF_NODE: Final = "node"

# Photovoltaics-specific sensor names (for translation/output mapping)
PHOTOVOLTAICS_POWER_PRODUCED: Final = "photovoltaics_power_produced"
PHOTOVOLTAICS_POWER_BALANCE: Final = "photovoltaics_power_balance"


class PhotovoltaicsConfigSchema(TypedDict):
    """Photovoltaics element configuration."""

    element_type: Literal["photovoltaics"]
    name: NameFieldSchema
    node: NameFieldSchema  # Node to connect to
    forecast: PowerSensorsFieldSchema

    # Optional fields
    price_production: NotRequired[PriceFieldSchema]
    curtailment: NotRequired[BooleanFieldSchema]


class PhotovoltaicsConfigData(TypedDict):
    """Photovoltaics element configuration."""

    element_type: Literal["photovoltaics"]
    name: NameFieldData
    node: NameFieldData  # Node to connect to
    forecast: PowerSensorsFieldData

    # Optional fields
    price_production: NotRequired[PriceFieldData]
    curtailment: NotRequired[BooleanFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_CURTAILMENT: False,
}


def create_model_elements(
    config: PhotovoltaicsConfigData,
    period: float,  # noqa: ARG001
    n_periods: int,  # noqa: ARG001
) -> list[dict[str, Any]]:
    """Create model elements for Photovoltaics configuration.

    Returns a list of element configurations that should be added to the network:
    - A SourceSink element for the photovoltaics
    - A Connection from the photovoltaics to the specified node

    Args:
        config: Photovoltaics configuration data
        period: Time period in hours
        n_periods: Number of periods

    Returns:
        List of element configs to add to network

    """
    elements: list[dict[str, Any]] = []

    # Create SourceSink for the photovoltaics
    elements.append(
        {
            "element_type": "source_sink",
            "name": config["name"],
        }
    )

    # Create Connection from photovoltaics to node (PV produces power)
    connection_config: dict[str, Any] = {
        "element_type": "connection",
        "name": f"{config['name']}_connection",
        "source": config["name"],
        "target": config["node"],
        "max_power_source_target": config["forecast"],  # Forecast becomes power limit
    }

    # Add production pricing if provided
    if "price_production" in config:
        connection_config["price_source_target"] = config["price_production"]

    elements.append(connection_config)

    return elements


def outputs(
    element_name: str,
    model_outputs: Mapping[str, OutputData],
) -> dict[str, dict[str, OutputData]]:
    """Map model outputs to photovoltaics-specific output names.

    Args:
        element_name: Name of the photovoltaics element
        model_outputs: Outputs from the model SourceSink and Connection

    Returns:
        Nested dict mapping {element_name: {sensor_name: OutputData}}

    """
    pv_outputs: dict[str, OutputData] = {}

    # Map SourceSink power_out to photovoltaics_power_produced (PV producing power TO network)
    if SOURCE_SINK_POWER_OUT in model_outputs:
        pv_outputs[PHOTOVOLTAICS_POWER_PRODUCED] = model_outputs[SOURCE_SINK_POWER_OUT]

    # Map power balance shadow price
    if SOURCE_SINK_POWER_BALANCE in model_outputs:
        pv_outputs[PHOTOVOLTAICS_POWER_BALANCE] = model_outputs[SOURCE_SINK_POWER_BALANCE]

    return {element_name: pv_outputs}
