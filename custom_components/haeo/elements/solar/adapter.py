"""Solar element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
)
from custom_components.haeo.model.output_data import OutputData

from .schema import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    DEFAULTS,
    ELEMENT_TYPE,
    SolarConfigData,
    SolarConfigSchema,
)

if TYPE_CHECKING:
    from .flow import SolarSubentryFlowHandler

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

# Input field definitions for creating input entities (mix of Number and Switch)
INPUT_FIELDS: Final[tuple[InputFieldInfo[Any], ...]] = (
    InputFieldInfo(
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
    InputFieldInfo(
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
    ),
    InputFieldInfo(
        field_name=CONF_CURTAILMENT,
        entity_description=SwitchEntityDescription(
            key=CONF_CURTAILMENT,
            translation_key=f"{ELEMENT_TYPE}_{CONF_CURTAILMENT}",
        ),
        output_type=OutputType.STATUS,
        default=True,
    ),
)


class SolarAdapter:
    """Adapter for Solar elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    @property
    def flow_class(self) -> type["SolarSubentryFlowHandler"]:
        """Return the flow handler class for solar elements."""
        from .flow import SolarSubentryFlowHandler  # noqa: PLC0415

        return SolarSubentryFlowHandler

    def available(self, config: SolarConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if solar configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        return ts_loader.available(hass=hass, value=config[CONF_FORECAST])

    def inputs(
        self,
        config: SolarConfigSchema,  # noqa: ARG002
    ) -> tuple[InputFieldInfo[Any], ...]:
        """Return input field definitions for creating solar input entities.

        Solar has fixed device structure - all inputs belong to the main solar device.
        """
        return INPUT_FIELDS

    def model_elements(self, config: SolarConfigData) -> list[dict[str, Any]]:
        """Return model element parameters for Solar configuration."""
        return [
            {"element_type": "node", "name": config["name"], "is_source": True, "is_sink": False},
            {
                "element_type": "connection",
                "name": f"{config['name']}:connection",
                "source": config["name"],
                "target": config["connection"],
                "max_power_source_target": config["forecast"],
                "max_power_target_source": 0.0,
                "fixed_power": not config.get("curtailment", DEFAULTS[CONF_CURTAILMENT]),
                "price_source_target": config.get("price_production"),
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: SolarConfigData,
    ) -> Mapping[SolarDeviceName, Mapping[SolarOutputName, OutputData]]:
        """Map model outputs to solar-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        solar_outputs: dict[SolarOutputName, OutputData] = {
            SOLAR_POWER: replace(connection[CONNECTION_POWER_SOURCE_TARGET], type=OutputType.POWER),
            SOLAR_FORECAST_LIMIT: connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET],
        }

        return {SOLAR_DEVICE_SOLAR: solar_outputs}


adapter = SolarAdapter()
