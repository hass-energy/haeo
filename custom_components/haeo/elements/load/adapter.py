"""Load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.elements.output_utils import expect_output_data
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.connection import CONNECTION_POWER_TARGET_SOURCE, CONNECTION_SEGMENTS
from custom_components.haeo.model.elements.segments import POWER_LIMIT_TARGET_SOURCE
from custom_components.haeo.model.output_data import OutputData

from .schema import (
    CONF_CONNECTION,
    CONF_FORECAST,
    CONF_SECTION_BASIC,
    CONF_SECTION_INPUTS,
    ELEMENT_TYPE,
    LoadConfigData,
    LoadConfigSchema,
)

# Load output names
type LoadOutputName = Literal[
    "load_power",
    "load_forecast_limit_price",
]

LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        # Shadow price
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
    )
)

type LoadDeviceName = Literal["load"]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := "load",),
)


class LoadAdapter:
    """Adapter for Load elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: LoadConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if load configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        return ts_loader.available(hass=hass, value=config[CONF_SECTION_INPUTS][CONF_FORECAST])

    def inputs(self, config: Any) -> dict[str, dict[str, InputFieldInfo[Any]]]:
        """Return input field definitions for load elements."""
        _ = config
        return {
            CONF_SECTION_INPUTS: {
                CONF_FORECAST: InputFieldInfo(
                    field_name=CONF_FORECAST,
                    entity_description=NumberEntityDescription(
                        key=CONF_FORECAST,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_FORECAST}",
                        native_unit_of_measurement=UnitOfPower.KILO_WATT,
                        device_class=NumberDeviceClass.POWER,
                        native_min_value=0.0,
                        native_max_value=1000.0,
                        native_step=0.01,
                    ),
                    output_type=OutputType.POWER,
                    direction="+",
                    time_series=True,
                ),
            },
        }

    def model_elements(self, config: LoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for Load configuration."""
        return [
            # Create Node for the load (sink only - consumes power)
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config[CONF_SECTION_BASIC]["name"],
                "is_source": False,
                "is_sink": True,
            },
            # Create Connection from node to load (power flows TO the load)
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config[CONF_SECTION_BASIC]['name']}:connection",
                "source": config[CONF_SECTION_BASIC]["name"],
                "target": config[CONF_SECTION_BASIC][CONF_CONNECTION],
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 0.0,
                        "max_power_target_source": config[CONF_SECTION_INPUTS][CONF_FORECAST],
                        "fixed": True,
                    }
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
        """Map model outputs to load-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        power_target_source = expect_output_data(connection[CONNECTION_POWER_TARGET_SOURCE])
        load_outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER: replace(power_target_source, type=OutputType.POWER),
        }

        # Shadow price from power_limit segment (if present)
        if (
            isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping)
            and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
            and (shadow := expect_output_data(power_limit_outputs.get(POWER_LIMIT_TARGET_SOURCE))) is not None
        ):
            load_outputs[LOAD_FORECAST_LIMIT_PRICE] = shadow

        return {LOAD_DEVICE_LOAD: load_outputs}


adapter = LoadAdapter()
