"""Inverter element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SEGMENTS,
)
from custom_components.haeo.core.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.core.model.elements.segments import POWER_LIMIT_SOURCE_TARGET, POWER_LIMIT_TARGET_SOURCE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.inverter import ELEMENT_TYPE, InverterConfigData
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
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

type InverterDeviceName = Literal[ElementType.INVERTER]

INVERTER_DEVICE_NAMES: Final[frozenset[InverterDeviceName]] = frozenset(
    (INVERTER_DEVICE_INVERTER := ElementType.INVERTER,),
)


class InverterAdapter:
    """Adapter for Inverter elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS

    def model_elements(self, config: InverterConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Inverter configuration.

        Creates a DC bus (Node junction) and a connection to the AC side with
        efficiency and power limits for bidirectional power conversion.
        """
        power_limits = config[SECTION_POWER_LIMITS]
        max_power_source_target = power_limits.get(CONF_MAX_POWER_SOURCE_TARGET)
        max_power_target_source = power_limits.get(CONF_MAX_POWER_TARGET_SOURCE)
        if max_power_source_target is None or max_power_target_source is None:
            msg = "Inverter power limits missing - config flow validation failed"
            raise RuntimeError(msg)

        return [
            # Create Node for the DC bus (pure junction - neither source nor sink)
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config[SECTION_COMMON]["name"],
                "is_source": False,
                "is_sink": False,
            },
            # Create a connection from DC bus to AC node
            # source_target = DC to AC (inverting)
            # target_source = AC to DC (rectifying)
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config[SECTION_COMMON]['name']}:connection",
                "source": config[SECTION_COMMON]["name"],
                "target": extract_connection_target(config[SECTION_COMMON][CONF_CONNECTION]),
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_SOURCE_TARGET),
                        "efficiency_target_source": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": max_power_source_target,
                        "max_power_target_source": max_power_target_source,
                    },
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[InverterDeviceName, Mapping[InverterOutputName, OutputData]]:
        """Map model outputs to inverter-specific output names."""
        connection = model_outputs[f"{name}:connection"]
        dc_bus = model_outputs[name]
        power_source_target = expect_output_data(connection[CONNECTION_POWER_SOURCE_TARGET])
        power_target_source = expect_output_data(connection[CONNECTION_POWER_TARGET_SOURCE])

        inverter_outputs: dict[InverterOutputName, OutputData] = {}

        # source_target = DC to AC (inverting)
        # target_source = AC to DC (rectifying)
        inverter_outputs[INVERTER_POWER_DC_TO_AC] = power_source_target
        inverter_outputs[INVERTER_POWER_AC_TO_DC] = power_target_source

        # Active inverter power (DC to AC - AC to DC)
        inverter_outputs[INVERTER_POWER_ACTIVE] = replace(
            power_source_target,
            values=[
                dc_to_ac - ac_to_dc
                for dc_to_ac, ac_to_dc in zip(
                    power_source_target.values,
                    power_target_source.values,
                    strict=True,
                )
            ],
            direction=None,
            type=OutputType.POWER_FLOW,
        )

        # DC bus power balance shadow price
        inverter_outputs[INVERTER_DC_BUS_POWER_BALANCE] = expect_output_data(dc_bus[NODE_POWER_BALANCE])

        # Shadow prices from power_limit segment
        if isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping) and isinstance(
            power_limit_outputs := segments_output.get("power_limit"), Mapping
        ):
            shadow_mappings: tuple[tuple[InverterOutputName, str], ...] = (
                (INVERTER_MAX_POWER_DC_TO_AC_PRICE, POWER_LIMIT_SOURCE_TARGET),
                (INVERTER_MAX_POWER_AC_TO_DC_PRICE, POWER_LIMIT_TARGET_SOURCE),
            )
            for output_name, shadow_key in shadow_mappings:
                if (shadow := expect_output_data(power_limit_outputs.get(shadow_key))) is not None:
                    inverter_outputs[output_name] = shadow

        return {INVERTER_DEVICE_INVERTER: inverter_outputs}


adapter = InverterAdapter()
