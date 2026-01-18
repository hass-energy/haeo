"""Solar element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.elements.loaded_values import LoadedValues, require_loaded_array, require_loaded_bool
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.connection import CONNECTION_POWER_SOURCE_TARGET, CONNECTION_SEGMENTS
from custom_components.haeo.model.elements.segments import POWER_LIMIT_SOURCE_TARGET
from custom_components.haeo.model.output_data import OutputData

from .schema import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    ELEMENT_TYPE,
    SolarConfigData,
    SolarConfigSchema,
)

# Default values for optional fields applied by adapter
DEFAULTS: Final[dict[str, bool | float]] = {
    CONF_CURTAILMENT: True,  # Allow curtailment by default
    CONF_PRICE_PRODUCTION: 0.0,  # No production incentive
}

# Solar output names
type SolarOutputName = Literal[
    "solar_power",
    "solar_forecast_limit",
]

SOLAR_OUTPUT_NAMES: Final[frozenset[SolarOutputName]] = frozenset(
    (
        SOLAR_POWER := "solar_power",
        # Shadow price
        SOLAR_FORECAST_LIMIT := "solar_forecast_limit",
    )
)

type SolarDeviceName = Literal["solar"]

SOLAR_DEVICE_NAMES: Final[frozenset[SolarDeviceName]] = frozenset((SOLAR_DEVICE_SOLAR := "solar",))


class SolarAdapter:
    """Adapter for Solar elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: SolarConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if solar configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        return ts_loader.available(hass=hass, value=config[CONF_FORECAST])

    def inputs(self, config: Any) -> dict[str, InputFieldInfo[Any]]:
        """Return input field definitions for solar elements."""
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
                direction="-",
                time_series=True,
            ),
            CONF_PRICE_PRODUCTION: InputFieldInfo(
                field_name=CONF_PRICE_PRODUCTION,
                entity_description=NumberEntityDescription(
                    key=CONF_PRICE_PRODUCTION,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_PRODUCTION}",
                    native_min_value=-1.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="+",
                defaults=InputFieldDefaults(mode=None, value=0.0),
            ),
            CONF_CURTAILMENT: InputFieldInfo(
                field_name=CONF_CURTAILMENT,
                entity_description=SwitchEntityDescription(
                    key=CONF_CURTAILMENT,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_CURTAILMENT}",
                ),
                output_type=OutputType.STATUS,
                defaults=InputFieldDefaults(mode="value", value=True),
                force_required=True,
            ),
        }

    def build_config_data(
        self,
        loaded_values: LoadedValues,
        config: SolarConfigSchema,
    ) -> SolarConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        The coordinator uses this method after loading input entity values.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities)
            config: Original ConfigSchema for non-input fields (element_type, name, connection)

        Returns:
            SolarConfigData with all fields populated

        """
        data: SolarConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "forecast": require_loaded_array(loaded_values[CONF_FORECAST], CONF_FORECAST),
        }

        # Optional fields
        if CONF_PRICE_PRODUCTION in loaded_values:
            data["price_production"] = require_loaded_array(loaded_values[CONF_PRICE_PRODUCTION], CONF_PRICE_PRODUCTION)
        if CONF_CURTAILMENT in loaded_values:
            data["curtailment"] = require_loaded_bool(loaded_values[CONF_CURTAILMENT], CONF_CURTAILMENT)

        return data

    def model_elements(self, config: SolarConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Solar configuration."""
        n_periods = len(config["forecast"])
        price_production = config.get("price_production")

        return [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": config["name"], "is_source": True, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:connection",
                "source": config["name"],
                "target": config["connection"],
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": config["forecast"],
                        "max_power_target_source": np.zeros(n_periods),
                        "fixed": not config.get("curtailment", DEFAULTS[CONF_CURTAILMENT]),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": price_production,
                        "price_target_source": None,
                    },
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[SolarDeviceName, Mapping[SolarOutputName, OutputData]]:
        """Map model outputs to solar-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        power_source_target = connection[CONNECTION_POWER_SOURCE_TARGET]
        if not isinstance(power_source_target, OutputData):
            msg = f"Expected OutputData for {name!r} {CONNECTION_POWER_SOURCE_TARGET}"
            raise TypeError(msg)
        solar_outputs: dict[SolarOutputName, OutputData] = {
            SOLAR_POWER: replace(power_source_target, type=OutputType.POWER),
        }

        # Shadow price from power_limit segment (if present)
        segments_output = connection.get(CONNECTION_SEGMENTS)
        if isinstance(segments_output, Mapping):
            power_limit_outputs = segments_output.get("power_limit")
            if isinstance(power_limit_outputs, Mapping):
                shadow = power_limit_outputs.get(POWER_LIMIT_SOURCE_TARGET)
                if isinstance(shadow, OutputData):
                    solar_outputs[SOLAR_FORECAST_LIMIT] = shadow

        return {SOLAR_DEVICE_SOLAR: solar_outputs}


adapter = SolarAdapter()
