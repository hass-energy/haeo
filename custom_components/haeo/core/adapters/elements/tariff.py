"""Tariff element adapter for model layer integration.

A tariff configures tagged power flow pricing on a connection between two nodes.
It adds tags to the connection and includes a tag_pricing segment to add cost
to the tagged power flow.

Unlike other adapters that create new model elements, a tariff modifies how
connections between the specified nodes behave by adding tags and tag-specific
pricing segments.
"""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.tariff import (
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_TAG,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    SECTION_TAG_PRICING,
    TariffConfigData,
)

# Tariff-specific output names
type TariffOutputName = Literal[
    "tariff_power_source_target",
    "tariff_power_target_source",
]

TARIFF_OUTPUT_NAMES: Final[frozenset[TariffOutputName]] = frozenset(
    (
        TARIFF_POWER_SOURCE_TARGET := "tariff_power_source_target",
        TARIFF_POWER_TARGET_SOURCE := "tariff_power_target_source",
    )
)

type TariffDeviceName = Literal[ElementType.TARIFF]

TARIFF_DEVICE_NAMES: Final[frozenset[TariffDeviceName]] = frozenset(
    (TARIFF_DEVICE_TARIFF := ElementType.TARIFF,),
)


class TariffAdapter:
    """Adapter for Tariff elements.

    Creates a connection between the specified source and target nodes
    with both a passthrough segment (for total power flow) and a tag_pricing
    segment (for tagged power pricing). The connection is configured with
    the tariff's tag so all segments get per-tag power variables.
    """

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def model_elements(self, config: TariffConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Tariff configuration.

        Creates a connection with tags enabled and a tag_pricing segment.
        The connection includes a passthrough segment for basic power flow
        and a tag_pricing segment for the tagged pricing.
        """
        tag_pricing = config[SECTION_TAG_PRICING]
        tag = tag_pricing[CONF_TAG]

        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:tariff_connection",
                "source": extract_connection_target(config[SECTION_ENDPOINTS]["source"]),
                "target": extract_connection_target(config[SECTION_ENDPOINTS]["target"]),
                "tags": [tag],
                "segments": {
                    "passthrough": {
                        "segment_type": "passthrough",
                    },
                    "tag_pricing": {
                        "segment_type": "pricing",
                        "tag": tag,
                        "price_source_target": tag_pricing.get(CONF_PRICE_SOURCE_TARGET),
                        "price_target_source": tag_pricing.get(CONF_PRICE_TARGET_SOURCE),
                    },
                },
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[TariffDeviceName, Mapping[TariffOutputName, OutputData]]:
        """Map model outputs to tariff-specific output names."""
        connection = model_outputs[f"{name}:tariff_connection"]

        tariff_outputs: dict[TariffOutputName, OutputData] = {}

        power_st = expect_output_data(connection[CONNECTION_POWER_SOURCE_TARGET])
        power_ts = expect_output_data(connection[CONNECTION_POWER_TARGET_SOURCE])

        if power_st is not None:
            tariff_outputs[TARIFF_POWER_SOURCE_TARGET] = power_st
        if power_ts is not None:
            tariff_outputs[TARIFF_POWER_TARGET_SOURCE] = power_ts

        return {TARIFF_DEVICE_TARIFF: tariff_outputs}


adapter = TariffAdapter()
