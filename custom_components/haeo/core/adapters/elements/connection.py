"""Connection element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER, CONNECTION_SEGMENTS
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    ConnectionConfigData,
)
from custom_components.haeo.core.schema.sections import SECTION_EFFICIENCY, SECTION_POWER_LIMITS, SECTION_PRICING

type ConnectionOutputName = Literal[
    "connection_power",
    "connection_shadow_power_max",
]

CONNECTION_SHADOW_POWER_MAX: Final[ConnectionOutputName] = "connection_shadow_power_max"

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (CONNECTION_POWER, CONNECTION_SHADOW_POWER_MAX)
)

type ConnectionDeviceName = Literal[ElementType.CONNECTION]

CONNECTION_DEVICE_NAMES: Final[frozenset[ConnectionDeviceName]] = frozenset(
    (CONNECTION_DEVICE_CONNECTION := ElementType.CONNECTION,),
)


class ConnectionAdapter:
    """Adapter for Connection elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def model_elements(self, config: ConnectionConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Connection configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": config["name"],
                "source": extract_connection_target(config[SECTION_ENDPOINTS]["source"]),
                "target": extract_connection_target(config[SECTION_ENDPOINTS]["target"]),
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_SOURCE_TARGET),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_SOURCE_TARGET),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price": config[SECTION_PRICING].get(CONF_PRICE_SOURCE_TARGET),
                    },
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[ConnectionDeviceName, Mapping[ConnectionOutputName, OutputData]]:
        """Map model outputs to connection-specific output names."""
        conn = model_outputs[name]
        connection_outputs: dict[ConnectionOutputName, OutputData] = {
            CONNECTION_POWER: expect_output_data(conn[CONNECTION_POWER]),
        }

        if (
            isinstance(segments_output := conn.get(CONNECTION_SEGMENTS), Mapping)
            and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
            and (shadow := expect_output_data(power_limit_outputs.get("power_limit"))) is not None
        ):
            connection_outputs[CONNECTION_SHADOW_POWER_MAX] = shadow

        return {CONNECTION_DEVICE_CONNECTION: connection_outputs}


adapter = ConnectionAdapter()
