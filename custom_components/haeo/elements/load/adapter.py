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
from custom_components.haeo.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.output_data import OutputData

from .schema import CONF_FORECAST, ELEMENT_TYPE, LoadConfigData, LoadConfigSchema

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
        return ts_loader.available(hass=hass, value=config[CONF_FORECAST])

    def inputs(self, config: Any) -> dict[str, InputFieldInfo[Any]]:
        """Return input field definitions for load elements."""
        _ = config
        return {
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
            )
        }

    def model_elements(self, config: LoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for Load configuration."""
        return [
            # Create Node for the load (sink only - consumes power)
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": False,
                "is_sink": True,
            },
            # Create Connection from node to load (power flows TO the load)
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:connection",
                "source": config["name"],
                "target": config["connection"],
                "max_power_source_target": 0.0,
                "max_power_target_source": config["forecast"],
                "fixed_power": True,
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        **_kwargs: Any,
    ) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
        """Map model outputs to load-specific output names."""
        connection = model_outputs[f"{name}:connection"]
        load_outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER: replace(connection[CONNECTION_POWER_TARGET_SOURCE], type=OutputType.POWER),
            LOAD_FORECAST_LIMIT_PRICE: connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE],
        }

        return {LOAD_DEVICE_LOAD: load_outputs}


adapter = LoadAdapter()
