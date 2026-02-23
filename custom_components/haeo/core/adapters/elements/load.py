"""Load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER_TARGET_SOURCE, CONNECTION_SEGMENTS
from custom_components.haeo.core.model.elements.segments import POWER_LIMIT_TARGET_SOURCE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.load import ELEMENT_TYPE, LoadConfigData
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
)

# Load output names
type LoadOutputName = Literal[
    "load_power",
    "load_forecast_limit_price",
]

LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        # Shadow price
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
    )
)

type LoadDeviceName = Literal[ElementType.LOAD]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := ElementType.LOAD,),
)


class LoadAdapter:
    """Adapter for Load elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def model_elements(self, config: LoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for Load configuration."""
        value = config[SECTION_PRICING].get(CONF_PRICE_TARGET_SOURCE)

        return [
            # Create Node for the load (sink only - consumes power)
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config[SECTION_COMMON]["name"],
                "is_source": False,
                "is_sink": True,
            },
            # Create Connection from node to load (power flows TO the load)
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config[SECTION_COMMON]['name']}:connection",
                "source": config[SECTION_COMMON]["name"],
                "target": extract_connection_target(config[SECTION_COMMON][CONF_CONNECTION]),
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 0.0,
                        "max_power_target_source": config[SECTION_FORECAST][CONF_FORECAST],
                        "fixed": not config[SECTION_CURTAILMENT].get(CONF_CURTAILMENT, False),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": None,
                        "price_target_source": -value if value is not None else None,
                    },
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
        """Map model outputs to load-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        power_target_source = expect_output_data(connection[CONNECTION_POWER_TARGET_SOURCE])
        load_outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER: replace(power_target_source, type=OutputType.POWER),
        }

        # Shadow price from power_limit segment (if present)
        if (
            isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping)
            and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
            and (shadow := expect_output_data(power_limit_outputs.get(POWER_LIMIT_TARGET_SOURCE))) is not None
        ):
            load_outputs[LOAD_FORECAST_LIMIT_PRICE] = shadow

        return {LOAD_DEVICE_LOAD: load_outputs}


adapter = LoadAdapter()
