"""Connection element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER
from custom_components.haeo.core.model.elements.segments import SegmentSpec
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import BufferRole
from custom_components.haeo.core.schema.elements.connection import (
    CONF_CONDUCTANCE,
    CONF_DRAWS_FROM_TARGET,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_CONDUCTANCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    CONF_SOURCE_TEMPERATURE,
    CONF_TARGET_TEMPERATURE,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    SECTION_LEVEL,
    ConnectionConfigData,
)
from custom_components.haeo.core.schema.sections import SECTION_EFFICIENCY, SECTION_POWER_LIMITS, SECTION_PRICING

type ConnectionOutputName = Literal["connection_power"]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset((CONNECTION_POWER,))

type ConnectionDeviceName = Literal[ElementType.CONNECTION]

CONNECTION_DEVICE_NAMES: Final[frozenset[ConnectionDeviceName]] = frozenset(
    (CONNECTION_DEVICE_CONNECTION := ElementType.CONNECTION,),
)


class ConnectionAdapter:
    """Adapter for Connection elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = False
    switchboard: bool = False
    device_names: frozenset[ConnectionDeviceName] = CONNECTION_DEVICE_NAMES
    buffer_roles: frozenset[BufferRole] = frozenset()

    def model_elements(self, config: ConnectionConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Connection configuration.

        A connection that draws from its target delivers its efficiency times its
        flow as a loss to the target rather than a gain, as a cooler removes heat.
        Conductances add segments that set or cap the flow by the difference in
        level between the endpoints, with a source or target temperature, when
        given, standing in for that endpoint's own.
        """
        efficiency = config[SECTION_EFFICIENCY]
        efficiency_value = efficiency.get(CONF_EFFICIENCY_SOURCE_TARGET)
        if efficiency_value is not None and efficiency.get(CONF_DRAWS_FROM_TARGET, False):
            efficiency_value = -efficiency_value
        # The limit and price apply to the power entering the connection, before
        # its losses, where the connection power sensor measures, so a connection
        # at its limit reads the limit.
        segments: dict[str, SegmentSpec] = {
            "power_limit": {
                "segment_type": "power_limit",
                "max_power": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_SOURCE_TARGET),
            },
            "pricing": {
                "segment_type": "pricing",
                "price": config[SECTION_PRICING].get(CONF_PRICE_SOURCE_TARGET),
            },
            "efficiency": {"segment_type": "efficiency", "efficiency": efficiency_value},
        }
        level = config.get(SECTION_LEVEL, {})
        source_temperature = level.get(CONF_SOURCE_TEMPERATURE)
        target_temperature = level.get(CONF_TARGET_TEMPERATURE)
        if (conductance := level.get(CONF_CONDUCTANCE)) is not None:
            segments["conduction"] = {
                "segment_type": "conduction",
                "conductance": conductance,
                "source_level": source_temperature,
                "target_level": target_temperature,
            }
        if (max_conductance := level.get(CONF_MAX_CONDUCTANCE)) is not None:
            segments["level_limit"] = {
                "segment_type": "level_limit",
                "conductance": max_conductance,
                "source_level": source_temperature,
                "target_level": target_temperature,
            }
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": config["name"],
                "source": extract_connection_target(config[SECTION_ENDPOINTS]["source"]),
                "target": extract_connection_target(config[SECTION_ENDPOINTS]["target"]),
                "segments": segments,
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: object,
    ) -> Mapping[ConnectionDeviceName, Mapping[ConnectionOutputName, OutputData]]:
        """Map model outputs to connection-specific output names."""
        conn = model_outputs[name]
        return {
            CONNECTION_DEVICE_CONNECTION: {
                CONNECTION_POWER: expect_output_data(conn[CONNECTION_POWER]),
            }
        }


adapter = ConnectionAdapter()
