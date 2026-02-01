"""Solar element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.elements.output_utils import expect_output_data
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.connection import CONNECTION_POWER_SOURCE_TARGET, CONNECTION_SEGMENTS
from custom_components.haeo.model.elements.segments import POWER_LIMIT_SOURCE_TARGET
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.sections import (
    CONF_CONNECTION,
    CONF_FORECAST,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_ADVANCED,
    SECTION_DETAILS,
    SECTION_FORECAST,
    SECTION_PRICING,
)

from .schema import CONF_CURTAILMENT, ELEMENT_TYPE, SolarConfigData, SolarConfigSchema

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
        return ts_loader.available(hass=hass, value=config[SECTION_FORECAST][CONF_FORECAST])

    def inputs(self, config: Any) -> dict[str, dict[str, InputFieldInfo[Any]]]:
        """Return input field definitions for solar elements."""
        _ = config
        return {
            SECTION_FORECAST: {
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
            },
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_PRICE_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_PRICE_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_SOURCE_TARGET}",
                        native_min_value=-1.0,
                        native_max_value=10.0,
                        native_step=0.001,
                    ),
                    output_type=OutputType.PRICE,
                    direction="+",
                    time_series=True,
                    defaults=InputFieldDefaults(mode=None, value=0.0),
                ),
            },
            SECTION_ADVANCED: {
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
            },
        }

    def model_elements(self, config: SolarConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Solar configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config[SECTION_DETAILS]["name"],
                "is_source": True,
                "is_sink": False,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config[SECTION_DETAILS]['name']}:connection",
                "source": config[SECTION_DETAILS]["name"],
                "target": config[SECTION_DETAILS][CONF_CONNECTION],
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": config[SECTION_FORECAST][CONF_FORECAST],
                        "max_power_target_source": 0.0,
                        "fixed": not config[SECTION_ADVANCED].get(CONF_CURTAILMENT, True),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": config[SECTION_PRICING].get(CONF_PRICE_SOURCE_TARGET),
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

        power_source_target = expect_output_data(connection[CONNECTION_POWER_SOURCE_TARGET])
        solar_outputs: dict[SolarOutputName, OutputData] = {
            SOLAR_POWER: replace(power_source_target, type=OutputType.POWER),
        }

        # Shadow price from power_limit segment (if present)
        if (
            isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping)
            and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
            and (shadow := expect_output_data(power_limit_outputs.get(POWER_LIMIT_SOURCE_TARGET))) is not None
        ):
            solar_outputs[SOLAR_FORECAST_LIMIT] = shadow

        return {SOLAR_DEVICE_SOLAR: solar_outputs}


adapter = SolarAdapter()
