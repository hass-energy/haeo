"""Inverter element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal, cast

from custom_components.haeo.core.adapters.output_utils import (
    balance_shadow_price_device_outputs,
    connection_power,
    expect_output_data,
)
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.connection import CONNECTION_SEGMENTS
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
    "inverter_dc_bus_tag_power_balance",
    "inverter_max_power_dc_to_ac_price",
    "inverter_max_power_ac_to_dc_price",
]

INVERTER_OUTPUT_NAMES: Final[frozenset[InverterOutputName]] = frozenset(
    (
        INVERTER_POWER_DC_TO_AC := "inverter_power_dc_to_ac",
        INVERTER_POWER_AC_TO_DC := "inverter_power_ac_to_dc",
        INVERTER_POWER_ACTIVE := "inverter_power_active",
        INVERTER_DC_BUS_POWER_BALANCE := "inverter_dc_bus_power_balance",
        INVERTER_DC_BUS_TAG_POWER_BALANCE := "inverter_dc_bus_tag_power_balance",
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
    can_source: bool = False
    can_sink: bool = False

    def model_elements(self, config: InverterConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Inverter configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": False,
                "is_sink": False,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:dc_to_ac",
                "source": config["name"],
                "target": extract_connection_target(config[CONF_CONNECTION]),
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_SOURCE_TARGET),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_SOURCE_TARGET),
                    },
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:ac_to_dc",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": config["name"],
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_TARGET_SOURCE),
                    },
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        periods: Sequence[float],
        **_kwargs: Any,
    ) -> Mapping[InverterDeviceName, Mapping[InverterOutputName, OutputData]]:
        """Map model outputs to inverter-specific output names."""
        forward_conn = model_outputs.get(f"{name}:dc_to_ac")
        reverse_conn = model_outputs.get(f"{name}:ac_to_dc")
        dc_bus = model_outputs[name]
        period_count = len(periods)
        power_forward = connection_power(forward_conn, period_count)
        power_reverse = connection_power(reverse_conn, period_count)

        inverter_outputs: dict[str, OutputData] = {}

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

        dc_bus_balance = expect_output_data(dc_bus[ELEMENT_POWER_BALANCE])
        inverter_outputs.update(
            balance_shadow_price_device_outputs(
                element_prefix="inverter_dc_bus",
                primary_output_name=INVERTER_DC_BUS_POWER_BALANCE,
                dual=dc_bus_balance,
                n_periods=period_count,
            )
        )

        # Shadow prices from power_limit segments on each connection
        shadow_price_mappings: tuple[
            tuple[Mapping[ModelOutputName, ModelOutputValue] | None, InverterOutputName],
            ...,
        ] = (
            (forward_conn, INVERTER_MAX_POWER_DC_TO_AC_PRICE),
            (reverse_conn, INVERTER_MAX_POWER_AC_TO_DC_PRICE),
        )
        for conn, output_name in shadow_price_mappings:
            if (
                conn is not None
                and isinstance(segments_output := conn.get(CONNECTION_SEGMENTS), Mapping)
                and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
                and (shadow := expect_output_data(power_limit_outputs.get("power_limit"))) is not None
            ):
                inverter_outputs[output_name] = shadow

        return {INVERTER_DEVICE_INVERTER: cast("Mapping[InverterOutputName, OutputData]", inverter_outputs)}


adapter = InverterAdapter()
