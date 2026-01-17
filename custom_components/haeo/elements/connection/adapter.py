"""Connection element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
    POWER_CONNECTION_OUTPUT_NAMES,
    PowerConnectionOutputName,
)
from custom_components.haeo.model.output_data import OutputData

from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    ConnectionConfigData,
    ConnectionConfigSchema,
)

# Adapter-synthesized output name (computed from model outputs)
CONNECTION_POWER_ACTIVE: Final = "connection_power_active"

# Connection adapter output names include model outputs + adapter-synthesized outputs
type ConnectionOutputName = PowerConnectionOutputName | Literal["connection_power_active"]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        *POWER_CONNECTION_OUTPUT_NAMES,
        CONNECTION_POWER_ACTIVE,
    )
)

type ConnectionDeviceName = Literal["connection"]

CONNECTION_DEVICE_NAMES: Final[frozenset[ConnectionDeviceName]] = frozenset(
    (CONNECTION_DEVICE_CONNECTION := "connection",),
)


class ConnectionAdapter:
    """Adapter for Connection elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def available(self, config: ConnectionConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if connection configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Check all optional time series fields if present
        optional_fields = [
            CONF_MAX_POWER_SOURCE_TARGET,
            CONF_MAX_POWER_TARGET_SOURCE,
            CONF_EFFICIENCY_SOURCE_TARGET,
            CONF_EFFICIENCY_TARGET_SOURCE,
            CONF_PRICE_SOURCE_TARGET,
            CONF_PRICE_TARGET_SOURCE,
        ]

        for field in optional_fields:
            if field in config and not ts_loader.available(hass=hass, value=config[field]):
                return False

        return True

    def inputs(self, config: Any) -> tuple[InputFieldInfo[Any], ...]:
        """Return input field definitions for connection elements."""
        _ = config
        return (
            InputFieldInfo(
                field_name=CONF_MAX_POWER_SOURCE_TARGET,
                entity_description=NumberEntityDescription(
                    key=CONF_MAX_POWER_SOURCE_TARGET,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_SOURCE_TARGET}",
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    device_class=NumberDeviceClass.POWER,
                    native_min_value=0.0,
                    native_max_value=1000.0,
                    native_step=0.1,
                ),
                output_type=OutputType.POWER_LIMIT,
                time_series=True,
            ),
            InputFieldInfo(
                field_name=CONF_MAX_POWER_TARGET_SOURCE,
                entity_description=NumberEntityDescription(
                    key=CONF_MAX_POWER_TARGET_SOURCE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_TARGET_SOURCE}",
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    device_class=NumberDeviceClass.POWER,
                    native_min_value=0.0,
                    native_max_value=1000.0,
                    native_step=0.1,
                ),
                output_type=OutputType.POWER_LIMIT,
                time_series=True,
            ),
            InputFieldInfo(
                field_name=CONF_EFFICIENCY_SOURCE_TARGET,
                entity_description=NumberEntityDescription(
                    key=CONF_EFFICIENCY_SOURCE_TARGET,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_SOURCE_TARGET}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.POWER_FACTOR,
                    native_min_value=50.0,
                    native_max_value=100.0,
                    native_step=0.1,
                ),
                output_type=OutputType.EFFICIENCY,
                time_series=True,
            ),
            InputFieldInfo(
                field_name=CONF_EFFICIENCY_TARGET_SOURCE,
                entity_description=NumberEntityDescription(
                    key=CONF_EFFICIENCY_TARGET_SOURCE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_TARGET_SOURCE}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.POWER_FACTOR,
                    native_min_value=50.0,
                    native_max_value=100.0,
                    native_step=0.1,
                ),
                output_type=OutputType.EFFICIENCY,
                time_series=True,
            ),
            InputFieldInfo(
                field_name=CONF_PRICE_SOURCE_TARGET,
                entity_description=NumberEntityDescription(
                    key=CONF_PRICE_SOURCE_TARGET,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_SOURCE_TARGET}",
                    native_min_value=-1.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="-",
                time_series=True,
            ),
            InputFieldInfo(
                field_name=CONF_PRICE_TARGET_SOURCE,
                entity_description=NumberEntityDescription(
                    key=CONF_PRICE_TARGET_SOURCE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_TARGET_SOURCE}",
                    native_min_value=-1.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="-",
                time_series=True,
            ),
        )

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: ConnectionConfigSchema,
    ) -> ConnectionConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name, source, target)

        Returns:
            ConnectionConfigData with all fields populated

        """
        data: ConnectionConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "source": config[CONF_SOURCE],
            "target": config[CONF_TARGET],
        }

        # Optional time series fields
        if CONF_MAX_POWER_SOURCE_TARGET in loaded_values:
            data["max_power_source_target"] = list(loaded_values[CONF_MAX_POWER_SOURCE_TARGET])
        if CONF_MAX_POWER_TARGET_SOURCE in loaded_values:
            data["max_power_target_source"] = list(loaded_values[CONF_MAX_POWER_TARGET_SOURCE])
        if CONF_EFFICIENCY_SOURCE_TARGET in loaded_values:
            data["efficiency_source_target"] = list(loaded_values[CONF_EFFICIENCY_SOURCE_TARGET])
        if CONF_EFFICIENCY_TARGET_SOURCE in loaded_values:
            data["efficiency_target_source"] = list(loaded_values[CONF_EFFICIENCY_TARGET_SOURCE])
        if CONF_PRICE_SOURCE_TARGET in loaded_values:
            data["price_source_target"] = list(loaded_values[CONF_PRICE_SOURCE_TARGET])
        if CONF_PRICE_TARGET_SOURCE in loaded_values:
            data["price_target_source"] = list(loaded_values[CONF_PRICE_TARGET_SOURCE])

        return data

    async def load(
        self,
        config: ConnectionConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> ConnectionConfigData:
        """Load connection configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        ts_loader = TimeSeriesLoader()
        loaded_values: dict[str, list[float]] = {}

        # Load optional time series fields
        if CONF_MAX_POWER_SOURCE_TARGET in config:
            loaded_values[CONF_MAX_POWER_SOURCE_TARGET] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_MAX_POWER_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_MAX_POWER_TARGET_SOURCE in config:
            loaded_values[CONF_MAX_POWER_TARGET_SOURCE] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_MAX_POWER_TARGET_SOURCE], forecast_times=forecast_times
            )
        if CONF_EFFICIENCY_SOURCE_TARGET in config:
            loaded_values[CONF_EFFICIENCY_SOURCE_TARGET] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_EFFICIENCY_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_EFFICIENCY_TARGET_SOURCE in config:
            loaded_values[CONF_EFFICIENCY_TARGET_SOURCE] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_EFFICIENCY_TARGET_SOURCE], forecast_times=forecast_times
            )
        if CONF_PRICE_SOURCE_TARGET in config:
            loaded_values[CONF_PRICE_SOURCE_TARGET] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_PRICE_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_PRICE_TARGET_SOURCE in config:
            loaded_values[CONF_PRICE_TARGET_SOURCE] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_PRICE_TARGET_SOURCE], forecast_times=forecast_times
            )

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: ConnectionConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Connection configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": config["name"],
                "source": config["source"],
                "target": config["target"],
                "max_power_source_target": config.get("max_power_source_target"),
                "max_power_target_source": config.get("max_power_target_source"),
                "efficiency_source_target": config.get("efficiency_source_target"),
                "efficiency_target_source": config.get("efficiency_target_source"),
                "price_source_target": config.get("price_source_target"),
                "price_target_source": config.get("price_target_source"),
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        **_kwargs: Any,
    ) -> Mapping[ConnectionDeviceName, Mapping[ConnectionOutputName, OutputData]]:
        """Map model outputs to connection-specific output names."""
        connection = model_outputs[name]

        connection_outputs: dict[ConnectionOutputName, OutputData] = {
            CONNECTION_POWER_SOURCE_TARGET: connection[CONNECTION_POWER_SOURCE_TARGET],
            CONNECTION_POWER_TARGET_SOURCE: connection[CONNECTION_POWER_TARGET_SOURCE],
        }

        # Active connection power (source_target - target_source)
        connection_outputs[CONNECTION_POWER_ACTIVE] = replace(
            connection[CONNECTION_POWER_SOURCE_TARGET],
            values=[
                st - ts
                for st, ts in zip(
                    connection[CONNECTION_POWER_SOURCE_TARGET].values,
                    connection[CONNECTION_POWER_TARGET_SOURCE].values,
                    strict=True,
                )
            ],
            direction=None,
            type=OutputType.POWER_FLOW,
        )

        # Shadow prices (computed by optimization) - only if constraints exist
        if CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET in connection:
            connection_outputs[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = connection[
                CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET
            ]

        if CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE in connection:
            connection_outputs[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = connection[
                CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE
            ]

        if CONNECTION_TIME_SLICE in connection:
            connection_outputs[CONNECTION_TIME_SLICE] = connection[CONNECTION_TIME_SLICE]

        return {CONNECTION_DEVICE_CONNECTION: connection_outputs}


adapter = ConnectionAdapter()
