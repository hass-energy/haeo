"""Tariff element adapter for model layer integration.

A tariff configures power flow pricing policies between nodes.
The tariff adapter does not create model elements directly — instead,
policy rules are compiled into tagged power flow constraints by the
compile_policies() pipeline in tariff_compilation.py.

The adapter produces policy rule configs that are consumed by the
compilation pipeline during model construction.
"""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.tariff import ELEMENT_TYPE, TariffConfigData

# Tariff-specific output names
type TariffOutputName = Literal["tariff_power",]

TARIFF_OUTPUT_NAMES: Final[frozenset[TariffOutputName]] = frozenset((TARIFF_POWER := "tariff_power",))

type TariffDeviceName = Literal[ElementType.TARIFF]

TARIFF_DEVICE_NAMES: Final[frozenset[TariffDeviceName]] = frozenset(
    (TARIFF_DEVICE_TARIFF := ElementType.TARIFF,),
)


class TariffAdapter:
    """Adapter for Tariff elements.

    Tariffs produce policy rules, not model elements directly.
    The compile_policies() pipeline handles model-level integration.
    """

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def model_elements(self, _config: TariffConfigData) -> list[ModelElementConfig]:
        """Tariff does not create model elements — policies are compiled separately."""
        return []

    def outputs(
        self,
        _name: str,
        _model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[TariffDeviceName, Mapping[TariffOutputName, OutputData]]:
        """Map model outputs to tariff-specific output names."""
        return {TARIFF_DEVICE_TARIFF: {}}


adapter = TariffAdapter()
