"""Load element configuration for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_MAX_TARGET_SOURCE,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import (
    FORECAST_SOURCE_CUSTOM_SENSOR,
    FORECAST_SOURCE_ENERGY_TAB,
    ElementNameFieldSchema,
    ForecastSourceFieldData,
    ForecastSourceFieldSchema,
    HistoryDaysFieldData,
    HistoryDaysFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PowerSensorsFieldData,
    PowerSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST_SOURCE: Final = "forecast_source"
CONF_HISTORY_DAYS: Final = "history_days"
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"

# Default values
DEFAULT_HISTORY_DAYS: Final = 7

type LoadOutputName = Literal[
    "load_power",
    "load_power_possible",
    "load_forecast_limit_price",
]
LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        LOAD_POWER_POSSIBLE := "load_power_possible",
        # Shadow prices
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
    )
)

type LoadDeviceName = Literal["load"]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := ELEMENT_TYPE,),
)


class LoadConfigSchema(TypedDict):
    """Load element configuration.

    The forecast can be sourced from either:
    - Energy Tab: Historical consumption data from Home Assistant's Energy dashboard
    - Custom Sensor: User-provided sensor entities with forecast data
    """

    element_type: Literal["load"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Connection ID that load connects to
    forecast_source: ForecastSourceFieldSchema  # "energy_tab" or "custom_sensor"
    history_days: NotRequired[HistoryDaysFieldSchema]  # Days of history (energy_tab mode)
    forecast: NotRequired[PowerSensorsFieldSchema]  # Custom sensors (custom_sensor mode)


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values."""

    element_type: Literal["load"]
    name: NameFieldData
    connection: ElementNameFieldSchema  # Connection ID that load connects to
    forecast_source: ForecastSourceFieldData  # "energy_tab" or "custom_sensor"
    # Note: Only one of these will be present based on forecast_source
    history_days: NotRequired[HistoryDaysFieldData]  # Loaded power values from history
    forecast: NotRequired[PowerSensorsFieldData]  # Loaded power values from sensors


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_FORECAST_SOURCE: FORECAST_SOURCE_ENERGY_TAB,
    CONF_HISTORY_DAYS: DEFAULT_HISTORY_DAYS,
}


def create_model_elements(config: LoadConfigData) -> list[dict[str, Any]]:
    """Create model elements for Load configuration."""

    # Get forecast data from the appropriate source
    # Handle backward compatibility: if forecast_source is not set but forecast is provided,
    # treat it as custom_sensor mode (legacy behavior)
    # Cast to dict to allow checking for missing keys in legacy configs
    config_dict: dict[str, Any] = dict(config)
    forecast_source: str = config_dict.get("forecast_source", "")

    if not forecast_source:
        # Backward compatibility: infer source from which field is present
        forecast_source = FORECAST_SOURCE_CUSTOM_SENSOR if "forecast" in config_dict else FORECAST_SOURCE_ENERGY_TAB

    if forecast_source == FORECAST_SOURCE_ENERGY_TAB:
        # History days loader produces the forecast values directly
        forecast_data = config_dict.get("history_days", [])
    else:
        # Custom sensor mode
        forecast_data = config_dict.get("forecast", [])

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
            "max_power_target_source": forecast_data,
            "fixed_power": True,
        },
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

    return {LOAD_DEVICE_LOAD: load_outputs}
