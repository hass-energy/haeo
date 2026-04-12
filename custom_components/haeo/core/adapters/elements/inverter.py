"""Inverter element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER, CONNECTION_SEGMENTS
from custom_components.haeo.core.model.elements.node import NODE_POWER_BALANCE
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
        """Return model element parameters for Inverter configuration."""
        max_power_st = config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_SOURCE_TARGET)
        max_power_ts = config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_TARGET_SOURCE)
        inv_name = config["name"]
        target_name = extract_connection_target(config[CONF_CONNECTION])
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": inv_name,
                "is_source": False,
                "is_sink": False,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{inv_name}:connection",
                "source": inv_name,
                "target": target_name,
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_SOURCE_TARGET),
                    },
                    "power_limit": {"segment_type": "power_limit", "max_power": max_power_st},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{inv_name}:reverse",
                "source": target_name,
                "target": inv_name,
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                    "power_limit": {"segment_type": "power_limit", "max_power": max_power_ts},
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
        forward_conn = model_outputs[f"{name}:connection"]
        reverse_conn = model_outputs[f"{name}:reverse"]
        dc_bus = model_outputs[name]
        power_forward = expect_output_data(forward_conn[CONNECTION_POWER])
        power_reverse = expect_output_data(reverse_conn[CONNECTION_POWER])

        inverter_outputs: dict[InverterOutputName, OutputData] = {}

        # source_target = DC to AC (inverting)
        # target_source = AC to DC (rectifying)
        inverter_outputs[INVERTER_POWER_DC_TO_AC] = replace(power_forward, direction="+")
        inverter_outputs[INVERTER_POWER_AC_TO_DC] = replace(power_reverse, direction="-")

        # Active inverter power (DC to AC - AC to DC)
        inverter_outputs[INVERTER_POWER_ACTIVE] = replace(
            power_forward,
            values=[
                dc_to_ac - ac_to_dc
                for dc_to_ac, ac_to_dc in zip(
                    power_forward.values,
                    power_reverse.values,
                    strict=True,
                )
            ],
            direction=None,
            type=OutputType.POWER_FLOW,
        )

        # DC bus power balance shadow price
        inverter_outputs[INVERTER_DC_BUS_POWER_BALANCE] = expect_output_data(dc_bus[NODE_POWER_BALANCE])

        # Shadow prices from power_limit segments on each connection
        shadow_price_mappings: tuple[tuple[Mapping[ModelOutputName, ModelOutputValue], InverterOutputName], ...] = (
            (forward_conn, INVERTER_MAX_POWER_DC_TO_AC_PRICE),
            (reverse_conn, INVERTER_MAX_POWER_AC_TO_DC_PRICE),
        )
        for conn, output_name in shadow_price_mappings:
            if (
                isinstance(segments_output := conn.get(CONNECTION_SEGMENTS), Mapping)
                and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
                and (shadow := expect_output_data(power_limit_outputs.get("power_limit"))) is not None
            ):
                inverter_outputs[output_name] = shadow

        return {INVERTER_DEVICE_INVERTER: inverter_outputs}


adapter = InverterAdapter()
