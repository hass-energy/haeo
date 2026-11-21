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
    CONF_SEGMENTS,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    ConnectionConfigData,
    SegmentData,
)

type ConnectionOutputName = Literal["connection_power"]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset((CONNECTION_POWER,))

type ConnectionDeviceName = Literal[ElementType.CONNECTION]

CONNECTION_DEVICE_NAMES: Final[frozenset[ConnectionDeviceName]] = frozenset(
    (CONNECTION_DEVICE_CONNECTION := ElementType.CONNECTION,),
)


def _segment_spec(segment: SegmentData) -> SegmentSpec:
    """Return the model's specification of a configured segment."""
    if segment["segment_type"] == "power_limit":
        return {"segment_type": "power_limit", "max_power": segment.get("max_power")}
    if segment["segment_type"] == "pricing":
        return {"segment_type": "pricing", "price": segment.get("price")}
    return {"segment_type": "efficiency", "efficiency": segment.get("efficiency")}


class ConnectionAdapter:
    """Adapter for Connection elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = False
    switchboard: bool = False
    dc: bool = False
    dc_bus: bool = False
    device_names: frozenset[ConnectionDeviceName] = CONNECTION_DEVICE_NAMES
    buffer_roles: frozenset[BufferRole] = frozenset()

    def model_elements(self, config: ConnectionConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Connection configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": config["name"],
                "source": extract_connection_target(config[SECTION_ENDPOINTS]["source"]),
                "target": extract_connection_target(config[SECTION_ENDPOINTS]["target"]),
                # Power passes through the segments in the order they are listed. The
                # connection power sensor measures the power entering its last limit.
                "segments": {
                    f"{index}_{segment['segment_type']}": _segment_spec(segment)
                    for index, segment in enumerate(config[CONF_SEGMENTS])
                },
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
