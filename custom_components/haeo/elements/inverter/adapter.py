"""Inverter element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import ConstantLoader, TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.output_data import OutputData

from .schema import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
    ELEMENT_TYPE,
    InverterConfigData,
    InverterConfigSchema,
)

# Inverter output names
type InverterOutputName = Literal[
    "inverter_power_dc_to_ac",
    "inverter_power_ac_to_dc",
    "inverter_power_active",
    "inverter_dc_bus_power_balance",
    "inverter_max_power_dc_to_ac_price",
    "inverter_max_power_ac_to_dc_price",
]

INVERTER_OUTPUT_NAMES: Final[frozenset[InverterOutputName]] = frozenset(
    (
        INVERTER_POWER_DC_TO_AC := "inverter_power_dc_to_ac",
        INVERTER_POWER_AC_TO_DC := "inverter_power_ac_to_dc",
        INVERTER_POWER_ACTIVE := "inverter_power_active",
        INVERTER_DC_BUS_POWER_BALANCE := "inverter_dc_bus_power_balance",
        # Shadow prices
        INVERTER_MAX_POWER_DC_TO_AC_PRICE := "inverter_max_power_dc_to_ac_price",
        INVERTER_MAX_POWER_AC_TO_DC_PRICE := "inverter_max_power_ac_to_dc_price",
    )
)

type InverterDeviceName = Literal["inverter"]

INVERTER_DEVICE_NAMES: Final[frozenset[InverterDeviceName]] = frozenset(
    (INVERTER_DEVICE_INVERTER := "inverter",),
)

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo[NumberEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_MAX_POWER_DC_TO_AC,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_POWER_DC_TO_AC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_DC_TO_AC}",
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
        field_name=CONF_MAX_POWER_AC_TO_DC,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_POWER_AC_TO_DC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_AC_TO_DC}",
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
        field_name=CONF_EFFICIENCY_DC_TO_AC,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY_DC_TO_AC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_DC_TO_AC}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.EFFICIENCY,
        defaults=InputFieldDefaults(mode=None, value=100.0),
    ),
    InputFieldInfo(
        field_name=CONF_EFFICIENCY_AC_TO_DC,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY_AC_TO_DC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_AC_TO_DC}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.EFFICIENCY,
        defaults=InputFieldDefaults(mode=None, value=100.0),
    ),
)


class InverterAdapter:
    """Adapter for Inverter elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS

    @property
    def flow_class(self) -> type:
        """Return the config flow handler class."""
        # Local import avoids a circular dependency: the flow imports adapter INPUT_FIELDS.
        from .flow import InverterSubentryFlowHandler  # noqa: PLC0415

        return InverterSubentryFlowHandler

    def available(self, config: InverterConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if inverter configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        if not ts_loader.available(hass=hass, value=config[CONF_MAX_POWER_DC_TO_AC]):
            return False
        return ts_loader.available(hass=hass, value=config[CONF_MAX_POWER_AC_TO_DC])

    def inputs(self, config: InverterConfigSchema) -> tuple[InputFieldInfo[Any], ...]:
        """Return input field definitions for inverter elements."""
        _ = config
        return INPUT_FIELDS

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: InverterConfigSchema,
    ) -> InverterConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name, connection)

        Returns:
            InverterConfigData with all fields populated

        """
        data: InverterConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "max_power_dc_to_ac": list(loaded_values[CONF_MAX_POWER_DC_TO_AC]),
            "max_power_ac_to_dc": list(loaded_values[CONF_MAX_POWER_AC_TO_DC]),
        }

        # Optional scalar efficiency fields
        if CONF_EFFICIENCY_DC_TO_AC in loaded_values:
            data["efficiency_dc_to_ac"] = float(loaded_values[CONF_EFFICIENCY_DC_TO_AC])
        if CONF_EFFICIENCY_AC_TO_DC in loaded_values:
            data["efficiency_ac_to_dc"] = float(loaded_values[CONF_EFFICIENCY_AC_TO_DC])

        return data

    async def load(
        self,
        config: InverterConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> InverterConfigData:
        """Load inverter configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        ts_loader = TimeSeriesLoader()
        const_loader = ConstantLoader[float](float)
        loaded_values: dict[str, list[float] | float] = {}

        # Load required time series fields
        loaded_values[CONF_MAX_POWER_DC_TO_AC] = await ts_loader.load_intervals(
            hass=hass, value=config[CONF_MAX_POWER_DC_TO_AC], forecast_times=forecast_times
        )
        loaded_values[CONF_MAX_POWER_AC_TO_DC] = await ts_loader.load_intervals(
            hass=hass, value=config[CONF_MAX_POWER_AC_TO_DC], forecast_times=forecast_times
        )

        # Load optional scalar fields
        if CONF_EFFICIENCY_DC_TO_AC in config:
            loaded_values[CONF_EFFICIENCY_DC_TO_AC] = await const_loader.load(value=config[CONF_EFFICIENCY_DC_TO_AC])
        if CONF_EFFICIENCY_AC_TO_DC in config:
            loaded_values[CONF_EFFICIENCY_AC_TO_DC] = await const_loader.load(value=config[CONF_EFFICIENCY_AC_TO_DC])

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: InverterConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Inverter configuration.

        Creates a DC bus (Node junction) and a connection to the AC side with
        efficiency and power limits for bidirectional power conversion.
        """
        name = config["name"]

        return [
            # Create Node for the DC bus (pure junction - neither source nor sink)
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": name, "is_source": False, "is_sink": False},
            # Create a connection from DC bus to AC node
            # source_target = DC to AC (inverting)
            # target_source = AC to DC (rectifying)
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": name,
                "target": config["connection"],
                "max_power_source_target": config["max_power_dc_to_ac"],
                "max_power_target_source": config["max_power_ac_to_dc"],
                "efficiency_source_target": config.get("efficiency_dc_to_ac"),
                "efficiency_target_source": config.get("efficiency_ac_to_dc"),
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        **_kwargs: Any,
    ) -> Mapping[InverterDeviceName, Mapping[InverterOutputName, OutputData]]:
        """Map model outputs to inverter-specific output names."""
        connection = model_outputs[f"{name}:connection"]
        dc_bus = model_outputs[name]

        inverter_outputs: dict[InverterOutputName, OutputData] = {}

        # source_target = DC to AC (inverting)
        # target_source = AC to DC (rectifying)
        inverter_outputs[INVERTER_POWER_DC_TO_AC] = connection[CONNECTION_POWER_SOURCE_TARGET]
        inverter_outputs[INVERTER_POWER_AC_TO_DC] = connection[CONNECTION_POWER_TARGET_SOURCE]

        # Active inverter power (DC to AC - AC to DC)
        inverter_outputs[INVERTER_POWER_ACTIVE] = replace(
            connection[CONNECTION_POWER_SOURCE_TARGET],
            values=[
                dc_to_ac - ac_to_dc
                for dc_to_ac, ac_to_dc in zip(
                    connection[CONNECTION_POWER_SOURCE_TARGET].values,
                    connection[CONNECTION_POWER_TARGET_SOURCE].values,
                    strict=True,
                )
            ],
            direction=None,
            type=OutputType.POWER_FLOW,
        )

        # DC bus power balance shadow price
        inverter_outputs[INVERTER_DC_BUS_POWER_BALANCE] = dc_bus[NODE_POWER_BALANCE]

        # Shadow prices
        inverter_outputs[INVERTER_MAX_POWER_DC_TO_AC_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]
        inverter_outputs[INVERTER_MAX_POWER_AC_TO_DC_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]

        return {INVERTER_DEVICE_INVERTER: inverter_outputs}


adapter = InverterAdapter()
