"""Load element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.model import OutputName as ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_MAX_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
)
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

# Load-specific sensor names (for translation/output mapping)
LOAD_POWER: Final = "load_power"
LOAD_POWER_POSSIBLE: Final = "load_power_possible"
LOAD_FORECAST_LIMIT_PRICE: Final = "load_forecast_limit_price"

type LoadOutputName = Literal[
    "load_power",
    "load_power_possible",
    "load_forecast_limit_price",
]
LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER,
        LOAD_POWER_POSSIBLE,
        # Shadow prices
        LOAD_FORECAST_LIMIT_PRICE,
    )
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
            "source": config["connection"],
            "target": config["name"],
            "max_power_source_target": config["forecast"],
            "fixed_power": True,
        },
    ]

    return elements


def outputs(
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
) -> dict[str, dict[LoadOutputName, OutputData]]:
    """Map model outputs to load-specific output names."""

    connection = outputs[f"{name}:connection"]

    load_outputs: dict[LoadOutputName, OutputData] = {
        LOAD_POWER: connection[CONNECTION_POWER_TARGET_SOURCE],
    }

    if CONNECTION_POWER_MAX_SOURCE_TARGET in connection:
        load_outputs[LOAD_POWER_POSSIBLE] = connection[CONNECTION_POWER_MAX_SOURCE_TARGET]

    # Only the max limit has meaning, the source sink power balance is always zero as it will never influence cost
    load_outputs[LOAD_FORECAST_LIMIT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]

    return {name: load_outputs}
