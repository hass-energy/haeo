"""Policy element schema definitions.

A single Policies subentry stores a list of policy rules.
Each rule specifies a source, target, and optional pricing that controls
how the optimizer routes power between elements.
Tags are auto-assigned by the compilation pipeline.
"""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.schema.elements.element_type import ElementType

ELEMENT_TYPE = ElementType.POLICY

# Config keys
CONF_RULES: Final = "rules"
CONF_RULE_NAME: Final = "name"
CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"

# Wildcard sentinel for "any element"
WILDCARD: Final = "*"


class PolicyRuleConfig(TypedDict):
    """A single policy rule as stored in Home Assistant config."""

    name: str
    source: str | list[str]
    target: str | list[str]
    price_source_target: NotRequired[float]
    price_target_source: NotRequired[float]


class PolicyRuleData(TypedDict):
    """A single policy rule with loaded values."""

    name: str
    source: str | list[str]
    target: str | list[str]
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float]


class PolicyConfigSchema(TypedDict):
    """Policy element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.POLICY]
    name: str
    rules: list[PolicyRuleConfig]


class PolicyConfigData(TypedDict):
    """Policy element configuration with loaded values."""

    element_type: Literal[ElementType.POLICY]
    name: str
    rules: list[PolicyRuleData]


__all__ = [
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_RULES",
    "CONF_RULE_NAME",
    "CONF_SOURCE",
    "CONF_TARGET",
    "ELEMENT_TYPE",
    "WILDCARD",
    "PolicyConfigData",
    "PolicyConfigSchema",
    "PolicyRuleConfig",
    "PolicyRuleData",
]
