"""Policy element adapter for model layer integration.

A policy configures power flow pricing rules between nodes.
The policy adapter does not create model elements directly — instead,
policy rules are compiled into tagged power flow constraints by the
compile_policies() pipeline in policy_compilation.py.
"""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.policy_compilation import CompiledPolicyRule
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    WILDCARD,
    PolicyConfigData,
)

type PolicyOutputName = Literal["policy_power"]

POLICY_OUTPUT_NAMES: Final[frozenset[PolicyOutputName]] = frozenset(("policy_power",))

POLICY_POWER: Final[PolicyOutputName] = "policy_power"

type PolicyDeviceName = Literal[ElementType.POLICY]

POLICY_DEVICE_NAMES: Final[frozenset[PolicyDeviceName]] = frozenset(
    (POLICY_DEVICE_POLICY := ElementType.POLICY,),
)


def extract_policy_rules(config: Mapping[str, Any]) -> list[CompiledPolicyRule]:
    """Transform loaded policy rules into the format compile_policies() expects.

    Each rule becomes a dict with:
        sources: list of element names, or ["*"] for wildcard
        destinations: list of element names, or ["*"] for wildcard
        price: float, NDArray, or None
    """
    result: list[CompiledPolicyRule] = []
    for rule in config.get("rules", []):
        if not rule.get("enabled", True):
            continue
        source = rule.get(CONF_SOURCE, [])
        target = rule.get(CONF_TARGET, [])
        compiled = CompiledPolicyRule(
            sources=source if source else [WILDCARD],
            destinations=target if target else [WILDCARD],
        )
        if CONF_PRICE in rule:
            compiled["price"] = rule[CONF_PRICE]
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
