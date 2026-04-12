"""Connection element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements.connection import (
    CONNECTION_OUTPUT_NAMES as MODEL_CONNECTION_OUTPUT_NAMES,
)
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER
from custom_components.haeo.core.model.elements.connection import ConnectionOutputName as ModelConnectionOutputName
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    ConnectionConfigData,
)
from custom_components.haeo.core.schema.sections import SECTION_EFFICIENCY, SECTION_POWER_LIMITS, SECTION_PRICING

# Adapter-synthesized output name (computed from model outputs)
CONNECTION_POWER_ACTIVE: Final = "connection_power_active"

# Connection adapter output names include model outputs + adapter-synthesized outputs
type ConnectionOutputName = (
    ModelConnectionOutputName
    | Literal[
        "connection_power_active",
        "connection_shadow_power_max_source_target",
        "connection_shadow_power_max_target_source",
    ]
)

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        *MODEL_CONNECTION_OUTPUT_NAMES,
        CONNECTION_POWER_ACTIVE,
    )
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
        """Return model element parameters for Connection configuration.

        Builds the segments dictionary for the Connection model element with
        explicit None values for missing configuration fields.
        """
        # Build segments using explicit None for missing parameters.
        # Efficiency values are ratios (0-1) after input normalization.
        source_name = extract_connection_target(config[SECTION_ENDPOINTS]["source"])
        target_name = extract_connection_target(config[SECTION_ENDPOINTS]["target"])
        return [
            # Source -> Target
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:forward",
                "source": source_name,
                "target": target_name,
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
            # Target -> Source
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:reverse",
                "source": target_name,
                "target": source_name,
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": config[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_TARGET_SOURCE),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price": config[SECTION_PRICING].get(CONF_PRICE_TARGET_SOURCE),
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
        forward_conn = model_outputs[f"{name}:forward"]
        reverse_conn = model_outputs[f"{name}:reverse"]

        connection_outputs: dict[ConnectionOutputName, OutputData] = {}

        power_forward = expect_output_data(forward_conn[CONNECTION_POWER])
        power_reverse = expect_output_data(reverse_conn[CONNECTION_POWER])

        if power_forward is not None:
            connection_outputs[CONNECTION_POWER] = power_forward

        if power_forward is not None and power_reverse is not None:
            connection_outputs[CONNECTION_POWER_ACTIVE] = replace(
                power_forward,
                values=[fwd - rev for fwd, rev in zip(power_forward.values, power_reverse.values, strict=True)],
                direction=None,
                type=OutputType.POWER_FLOW,
            )

        return {CONNECTION_DEVICE_CONNECTION: connection_outputs}


adapter = ConnectionAdapter()
