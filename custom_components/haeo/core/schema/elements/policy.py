"""Policy element schema definitions.

A policy defines tagged directional pricing for power flow between nodes.
When configured, its rules are compiled into tag_costs on existing connections
rather than creating separate model elements.
"""

from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.constant_value import ConstantValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.entity_value import EntityValue
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints
from custom_components.haeo.core.schema.none_value import NoneValue

ELEMENT_TYPE = ElementType.POLICY

# Config keys
CONF_RULES: Final = "rules"
CONF_RULE_NAME: Final = "name"
CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_PRICE: Final = "price"
CONF_ENABLED: Final = "enabled"

# Wildcard sentinel for "any element"
WILDCARD: Final = "*"


class PolicyRuleConfig(TypedDict):
    """A single policy rule as stored in Home Assistant config."""

    name: str
    enabled: NotRequired[bool]
    source: NotRequired[list[str]]
    target: NotRequired[list[str]]
    price: NotRequired[EntityValue | ConstantValue | NoneValue]


class PolicyRuleData(TypedDict):
    """A single policy rule with loaded values."""

    name: str
    enabled: NotRequired[bool]
    source: NotRequired[list[str]]
    target: NotRequired[list[str]]
    price: NotRequired[NDArray[np.floating[Any]] | float]


class PolicyConfigSchema(TypedDict):
    """Policy element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.POLICY]
    name: str
    rules: Annotated[
        list[PolicyRuleConfig],
        ListFieldHints(
            fields={
                CONF_PRICE: FieldHint(
                    output_type=OutputType.PRICE,
                    time_series=True,
                ),
            },
        ),
    ]


class PolicyConfigData(TypedDict):
    """Policy element configuration with loaded values."""

    element_type: Literal[ElementType.POLICY]
    name: str
    rules: list[PolicyRuleData]


__all__ = [
    "CONF_ENABLED",
    "CONF_PRICE",
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
