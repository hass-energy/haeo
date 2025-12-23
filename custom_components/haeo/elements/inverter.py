"""Inverter element configuration for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER_FLOW
from custom_components.haeo.model.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import (
    ElementNameFieldData,
    ElementNameFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PercentageSensorFieldData,
    PercentageSensorFieldSchema,
    PowerSensorFieldData,
    PowerSensorFieldSchema,
)

ELEMENT_TYPE: Final = "inverter"

# Configuration field names
CONF_CONNECTION: Final = "connection"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"
CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_MAX_POWER_DC_TO_AC: Final = "max_power_dc_to_ac"
CONF_MAX_POWER_AC_TO_DC: Final = "max_power_ac_to_dc"

# Inverter-specific sensor names (for translation/output mapping)
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
    (INVERTER_DEVICE_INVERTER := ELEMENT_TYPE,),
)


class InverterConfigSchema(TypedDict):
    """Inverter element configuration."""

    element_type: Literal["inverter"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # AC side node to connect to
    max_power_dc_to_ac: PowerSensorFieldSchema
    max_power_ac_to_dc: PowerSensorFieldSchema

    # Optional fields
    efficiency_dc_to_ac: NotRequired[PercentageSensorFieldSchema]
    efficiency_ac_to_dc: NotRequired[PercentageSensorFieldSchema]


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded sensor values."""

    element_type: Literal["inverter"]
    name: NameFieldData
    connection: ElementNameFieldData  # AC side node to connect to
    max_power_dc_to_ac: PowerSensorFieldData
    max_power_ac_to_dc: PowerSensorFieldData

    # Optional fields
    efficiency_dc_to_ac: NotRequired[PercentageSensorFieldData]
    efficiency_ac_to_dc: NotRequired[PercentageSensorFieldData]


def create_model_elements(config: InverterConfigData) -> list[dict[str, Any]]:
    """Create model elements for Inverter configuration.

    Creates a DC bus (Node junction) and a connection to the AC side with
    efficiency and power limits for bidirectional power conversion.
    """
    name = config["name"]

    return [
        # Create Node for the DC bus (pure junction - neither source nor sink)
        {
            "element_type": "node",
            "name": name,
            "is_source": False,
            "is_sink": False,
        },
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
    name: str,
    outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
    _config: InverterConfigData,
) -> Mapping[InverterDeviceName, Mapping[InverterOutputName, OutputData]]:
    """Provide state updates for inverter output sensors."""
    connection = outputs[f"{name}:connection"]
    dc_bus = outputs[name]

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
        type=OUTPUT_TYPE_POWER_FLOW,
    )

    # DC bus power balance shadow price
    inverter_outputs[INVERTER_DC_BUS_POWER_BALANCE] = dc_bus[NODE_POWER_BALANCE]

    # Shadow prices for power limits
    inverter_outputs[INVERTER_MAX_POWER_DC_TO_AC_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]
    inverter_outputs[INVERTER_MAX_POWER_AC_TO_DC_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]

    return {INVERTER_DEVICE_INVERTER: inverter_outputs}
