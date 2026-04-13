"""Policy element adapter for model layer integration.

A policy configures power flow pricing rules between nodes.
The policy adapter does not create model elements directly — instead,
policy rules are compiled into tagged power flow constraints by the
compile_policies() pipeline in policy_compilation.py.
"""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    PolicyConfigData,
)

type PolicyOutputName = Literal["policy_power"]

POLICY_OUTPUT_NAMES: Final[frozenset[PolicyOutputName]] = frozenset(("policy_power",))

POLICY_POWER: Final[PolicyOutputName] = "policy_power"

type PolicyDeviceName = Literal[ElementType.POLICY]

POLICY_DEVICE_NAMES: Final[frozenset[PolicyDeviceName]] = frozenset(
    (POLICY_DEVICE_POLICY := ElementType.POLICY,),
)


def _to_name_list(value: str | list[str]) -> list[str]:
    """Normalize a source/target value to a list of element names or wildcard."""
    if isinstance(value, str):
        return [value]
    return value


def extract_policy_rules(config: PolicyConfigData) -> list[dict[str, Any]]:
    """Transform loaded policy rules into the format compile_policies() expects.

    Each rule becomes a dict with:
        sources: list of element names, or ["*"] for wildcard
        destinations: list of element names, or ["*"] for wildcard
        price_source_target: float or None
        price_target_source: float or None
    """
    result: list[dict[str, Any]] = []
    for rule in config.get("rules", []):
        compiled: dict[str, Any] = {
            "sources": _to_name_list(rule[CONF_SOURCE]),
            "destinations": _to_name_list(rule[CONF_TARGET]),
        }
        if CONF_PRICE_SOURCE_TARGET in rule:
            compiled["price_source_target"] = rule[CONF_PRICE_SOURCE_TARGET]
        if CONF_PRICE_TARGET_SOURCE in rule:
            compiled["price_target_source"] = rule[CONF_PRICE_TARGET_SOURCE]
        result.append(compiled)
    return result


class PolicyAdapter:
    """Adapter for Policy elements. Policies are compiled separately."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def model_elements(self, config: PolicyConfigData) -> list[ModelElementConfig]:  # noqa: ARG002
        """Policy does not create model elements — policies are compiled separately."""
        return []

    def outputs(
        self,
        name: str,  # noqa: ARG002
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],  # noqa: ARG002
        **_kwargs: Any,
    ) -> Mapping[PolicyDeviceName, Mapping[PolicyOutputName, OutputData]]:
        """Map model outputs to policy-specific output names."""
        return {POLICY_DEVICE_POLICY: {}}


adapter = PolicyAdapter()
