"""Tariff element adapter for model layer integration.

A tariff configures pricing rules for tagged power flow between source and
destination nodes. Unlike other adapters that produce model elements directly,
the tariff adapter produces tariff rule configs that are compiled into
tag assignments and scoped segments during the collect_model_elements step.
"""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.tariff import (
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
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

    Does not produce model elements directly. Instead, produces tariff rule
    configs that the compilation step uses to inject tags and scoped segments
    into existing connections.
    """

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def model_elements(self, config: TariffConfigData) -> list[ModelElementConfig]:  # noqa: ARG002
        """Return empty list — tariffs don't create model elements directly.

        Tariff compilation is handled separately in collect_model_elements.
        """
        return []

    def tariff_rule(self, config: TariffConfigData) -> dict[str, Any]:
        """Extract a tariff rule from the config for compilation.

        Returns:
            Dict with sources, destinations, and pricing.

        """
        endpoints = config[SECTION_ENDPOINTS]
        tag_pricing = config[SECTION_TAG_PRICING]

        return {
            "name": config["name"],
            "sources": endpoints.get("sources", ["*"]),
            "destinations": endpoints.get("destinations", ["*"]),
            "price_source_target": tag_pricing.get(CONF_PRICE_SOURCE_TARGET),
            "price_target_source": tag_pricing.get(CONF_PRICE_TARGET_SOURCE),
        }

    def outputs(
        self,
        name: str,  # noqa: ARG002
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],  # noqa: ARG002
        **_kwargs: Any,
    ) -> Mapping[TariffDeviceName, Mapping[TariffOutputName, OutputData]]:
        """Map model outputs to tariff-specific output names.

        Tariffs don't have their own model elements, so outputs are empty.
        Tagged power flows are visible on the connection sensors.
        """
        return {TARIFF_DEVICE_TARIFF: {}}


adapter = TariffAdapter()
