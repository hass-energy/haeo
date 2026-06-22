"""Inverter element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.output_utils import connection_power, connection_power_out, expect_output_data
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
            # ac_to_dc (rectifying): source = AC bus, target = DC bus.
            # Segment order [power_limit, efficiency] places the cap on the AC
            # (source) side, matching how OEM hybrid-inverter rectifier limits
            # are specified (AC-side ``max_active_power`` style caps).
            # Mirrors dc_to_ac where [efficiency, power_limit] also lands the
            # cap on the AC (target) side per upstream PR #297.
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:ac_to_dc",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": config["name"],
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_TARGET_SOURCE),
                    },
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_TARGET_SOURCE),
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
        forward_conn = model_outputs.get(f"{name}:dc_to_ac")
        reverse_conn = model_outputs.get(f"{name}:ac_to_dc")
        dc_bus = model_outputs[name]
        period_count = len(expect_output_data(dc_bus[ELEMENT_POWER_BALANCE]).values)

        # DC-side flows for the per-direction sensors (matches the existing
        # convention that *_dc_to_ac / *_ac_to_dc describe what the LP draws
        # from / pushes onto the DC bus). For the forward (inverting)
        # connection source = DC bus, so total_power_in is the DC-side flow.
        # For the reverse (rectifying) connection target = DC bus, so
        # total_power_out is the DC-side flow.
        power_forward_dc = connection_power(forward_conn, period_count)
        power_reverse_dc = connection_power_out(reverse_conn, period_count)

        # AC-side flows for the active sensor (matches OEM inverter monitoring
        # which reports AC-side power). Forward target = AC, so
        # total_power_out is AC-side; reverse source = AC, so total_power_in
        # is AC-side.
        power_forward_ac = connection_power_out(forward_conn, period_count)
        power_reverse_ac = connection_power(reverse_conn, period_count)

        inverter_outputs: dict[InverterOutputName, OutputData] = {}

        # source_target = DC to AC (inverting)
        # target_source = AC to DC (rectifying)
        inverter_outputs[INVERTER_POWER_DC_TO_AC] = replace(power_forward_dc, direction="+")
        inverter_outputs[INVERTER_POWER_AC_TO_DC] = replace(power_reverse_dc, direction="-")

        # Active inverter power (AC-side net: DC to AC - AC to DC, both AC-side)
        # Matches what an OEM inverter's "Active Power" sensor reports.
        # Signed: positive = net DC to AC (exporting to AC grid).
        inverter_outputs[INVERTER_POWER_ACTIVE] = replace(
            power_forward_ac,
            values=[
                dc_to_ac - ac_to_dc
                for dc_to_ac, ac_to_dc in zip(
                    power_forward_ac.values,
                    power_reverse_ac.values,
                    strict=True,
                )
            ],
            direction=None,
            type=OutputType.POWER_FLOW,
        )

        # DC bus power balance shadow price
        inverter_outputs[INVERTER_DC_BUS_POWER_BALANCE] = expect_output_data(dc_bus[ELEMENT_POWER_BALANCE])

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

        return {INVERTER_DEVICE_INVERTER: inverter_outputs}


adapter = InverterAdapter()
