"""Connection element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.elements.output_utils import expect_output_data
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements.connection import CONNECTION_OUTPUT_NAMES as MODEL_CONNECTION_OUTPUT_NAMES
from custom_components.haeo.model.elements.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SEGMENTS,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
)
from custom_components.haeo.model.elements.connection import ConnectionOutputName as ModelConnectionOutputName
from custom_components.haeo.model.elements.segments import (
    POWER_LIMIT_SOURCE_TARGET,
    POWER_LIMIT_TARGET_SOURCE,
    POWER_LIMIT_TIME_SLICE,
)
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema import (
    VALUE_TYPE_CONSTANT,
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    OptionalEntityOrConstantValue,
    extract_connection_target,
)
from custom_components.haeo.sections import SECTION_COMMON, SECTION_EFFICIENCY, SECTION_POWER_LIMITS, SECTION_PRICING

from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    ConnectionConfigData,
    ConnectionConfigSchema,
)

# Adapter-synthesized output name (computed from model outputs)
CONNECTION_POWER_ACTIVE: Final = "connection_power_active"

# Connection adapter output names include model outputs + adapter-synthesized outputs
type ConnectionOutputName = (
    ModelConnectionOutputName
    | Literal[
        "connection_power_active",
        "connection_shadow_power_max_source_target",
        "connection_shadow_power_max_target_source",
        "connection_time_slice",
    ]
)

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        *MODEL_CONNECTION_OUTPUT_NAMES,
        CONNECTION_POWER_ACTIVE,
        CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
        CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
        CONNECTION_TIME_SLICE,
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

        def optional_available(value: OptionalEntityOrConstantValue | None) -> bool:
            if value is None:
                return True
            if value["type"] == VALUE_TYPE_ENTITY:
                return ts_loader.available(hass=hass, value=value)
            return value["type"] in (VALUE_TYPE_CONSTANT, VALUE_TYPE_NONE)

        # Check all optional time series fields if present
        optional_fields = [
            CONF_MAX_POWER_SOURCE_TARGET,
            CONF_MAX_POWER_TARGET_SOURCE,
            CONF_EFFICIENCY_SOURCE_TARGET,
            CONF_EFFICIENCY_TARGET_SOURCE,
            CONF_PRICE_SOURCE_TARGET,
            CONF_PRICE_TARGET_SOURCE,
        ]

        limits = config[SECTION_POWER_LIMITS]
        efficiency = config[SECTION_EFFICIENCY]
        pricing = config[SECTION_PRICING]
        for field in optional_fields:
            if not optional_available(limits.get(field)):
                return False
            if not optional_available(efficiency.get(field)):
                return False
            if not optional_available(pricing.get(field)):
                return False

        return True

    def inputs(self, config: Any) -> dict[str, dict[str, InputFieldInfo[Any]]]:
        """Return input field definitions for connection elements."""
        _ = config
        return {
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: InputFieldInfo(
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
                CONF_MAX_POWER_TARGET_SOURCE: InputFieldInfo(
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
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: InputFieldInfo(
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
                CONF_EFFICIENCY_TARGET_SOURCE: InputFieldInfo(
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
                    direction="-",
                    time_series=True,
                ),
                CONF_PRICE_TARGET_SOURCE: InputFieldInfo(
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
            },
        }

    def model_elements(self, config: ConnectionConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Connection configuration.

        Builds the segments dictionary for the Connection model element with
        explicit None values for missing configuration fields.
        """
        # Build segments using explicit None for missing parameters.
        # Efficiency values are ratios (0-1) after input normalization.
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": config[SECTION_COMMON]["name"],
                "source": extract_connection_target(config[SECTION_ENDPOINTS]["source"]),
                "target": extract_connection_target(config[SECTION_ENDPOINTS]["target"]),
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_SOURCE_TARGET),
                        "efficiency_target_source": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_SOURCE_TARGET),
                        "max_power_target_source": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_TARGET_SOURCE),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": config[SECTION_PRICING].get(CONF_PRICE_SOURCE_TARGET),
                        "price_target_source": config[SECTION_PRICING].get(CONF_PRICE_TARGET_SOURCE),
                    },
                },
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[ConnectionDeviceName, Mapping[ConnectionOutputName, OutputData]]:
        """Map model outputs to connection-specific output names."""
        connection = model_outputs[name]
        power_source_target = expect_output_data(connection[CONNECTION_POWER_SOURCE_TARGET])
        power_target_source = expect_output_data(connection[CONNECTION_POWER_TARGET_SOURCE])

        connection_outputs: dict[ConnectionOutputName, OutputData] = {
            CONNECTION_POWER_SOURCE_TARGET: power_source_target,
            CONNECTION_POWER_TARGET_SOURCE: power_target_source,
        }

        # Active connection power (source_target - target_source)
        connection_outputs[CONNECTION_POWER_ACTIVE] = replace(
            power_source_target,
            values=[
                st - ts
                for st, ts in zip(
                    power_source_target.values,
                    power_target_source.values,
                    strict=True,
                )
            ],
            direction=None,
            type=OutputType.POWER_FLOW,
        )

        # Shadow prices are exposed under the model's `segments` output map.
        if isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping) and isinstance(
            power_limit_outputs := segments_output.get("power_limit"), Mapping
        ):
            shadow_mappings: tuple[tuple[ConnectionOutputName, str], ...] = (
                (CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET, POWER_LIMIT_SOURCE_TARGET),
                (CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE, POWER_LIMIT_TARGET_SOURCE),
                (CONNECTION_TIME_SLICE, POWER_LIMIT_TIME_SLICE),
            )
            for output_name, shadow_key in shadow_mappings:
                if (shadow := expect_output_data(power_limit_outputs.get(shadow_key))) is not None:
                    connection_outputs[output_name] = shadow

        return {CONNECTION_DEVICE_CONNECTION: connection_outputs}


adapter = ConnectionAdapter()
