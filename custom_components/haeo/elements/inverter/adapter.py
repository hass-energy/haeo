"""Inverter element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import ConstantLoader, TimeSeriesLoader
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.output_data import OutputData

from .flow import InverterSubentryFlowHandler
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


class InverterAdapter:
    """Adapter for Inverter elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = InverterSubentryFlowHandler
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS

    def available(self, config: InverterConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if inverter configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        if not ts_loader.available(hass=hass, value=config[CONF_MAX_POWER_DC_TO_AC]):
            return False
        return ts_loader.available(hass=hass, value=config[CONF_MAX_POWER_AC_TO_DC])

    async def load(
        self,
        config: InverterConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> InverterConfigData:
        """Load inverter configuration values from sensors."""
        ts_loader = TimeSeriesLoader()
        const_loader = ConstantLoader[float](float)

        max_power_dc_to_ac = await ts_loader.load(
            hass=hass,
            value=config[CONF_MAX_POWER_DC_TO_AC],
            forecast_times=forecast_times,
        )
        max_power_ac_to_dc = await ts_loader.load(
            hass=hass,
            value=config[CONF_MAX_POWER_AC_TO_DC],
            forecast_times=forecast_times,
        )

        data: InverterConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "max_power_dc_to_ac": max_power_dc_to_ac,
            "max_power_ac_to_dc": max_power_ac_to_dc,
        }

        # Load optional fields
        if CONF_EFFICIENCY_DC_TO_AC in config:
            data["efficiency_dc_to_ac"] = await const_loader.load(value=config[CONF_EFFICIENCY_DC_TO_AC])
        if CONF_EFFICIENCY_AC_TO_DC in config:
            data["efficiency_ac_to_dc"] = await const_loader.load(value=config[CONF_EFFICIENCY_AC_TO_DC])

        return data

    def create_model_elements(self, config: InverterConfigData) -> list[dict[str, Any]]:
        """Create model elements for Inverter configuration.

        Creates a DC bus (Node junction) and a connection to the AC side with
        efficiency and power limits for bidirectional power conversion.
        """
        name = config["name"]

        return [
            # Create Node for the DC bus (pure junction - neither source nor sink)
            {"element_type": "node", "name": name, "is_source": False, "is_sink": False},
            # Create a connection from DC bus to AC node
            # source_target = DC to AC (inverting)
            # target_source = AC to DC (rectifying)
            {
                "element_type": "connection",
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
        _config: InverterConfigData,
    ) -> Mapping[InverterDeviceName, Mapping[InverterOutputName, OutputData]]:
        """Map model outputs to inverter-specific output names."""
        connection = model_outputs[f"{name}:connection"]
        dc_bus = model_outputs[name]

        inverter_outputs: dict[InverterOutputName, OutputData] = {}

        # source_target = DC to AC (inverting)
        # target_source = AC to DC (rectifying)
        inverter_outputs[INVERTER_POWER_DC_TO_AC] = replace(
            connection[CONNECTION_POWER_SOURCE_TARGET], name=INVERTER_POWER_DC_TO_AC
        )
        inverter_outputs[INVERTER_POWER_AC_TO_DC] = replace(
            connection[CONNECTION_POWER_TARGET_SOURCE], name=INVERTER_POWER_AC_TO_DC
        )

        # Active inverter power (DC to AC - AC to DC)
        inverter_outputs[INVERTER_POWER_ACTIVE] = replace(
            connection[CONNECTION_POWER_SOURCE_TARGET],
            name=INVERTER_POWER_ACTIVE,
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
        inverter_outputs[INVERTER_DC_BUS_POWER_BALANCE] = replace(
            dc_bus[NODE_POWER_BALANCE], name=INVERTER_DC_BUS_POWER_BALANCE
        )

        # Shadow prices
        inverter_outputs[INVERTER_MAX_POWER_DC_TO_AC_PRICE] = replace(
            connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET], name=INVERTER_MAX_POWER_DC_TO_AC_PRICE
        )
        inverter_outputs[INVERTER_MAX_POWER_AC_TO_DC_PRICE] = replace(
            connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE], name=INVERTER_MAX_POWER_AC_TO_DC_PRICE
        )

        return {INVERTER_DEVICE_INVERTER: inverter_outputs}


adapter = InverterAdapter()
