"""Policy element schema definitions.

A policy defines tagged directional pricing for power flow between nodes.
When configured, its rules are compiled into PolicyPricing model elements
that apply costs to tagged power flows on connection min-cuts.
"""

from collections.abc import Callable, Mapping
from typing import Annotated, Final, Literal, NotRequired, TypedDict, TypeGuard

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.constant_value import ConstantValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.entity_value import EntityValue
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints

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
    enabled: bool
    source: NotRequired[list[str]]
    target: NotRequired[list[str]]
    price: EntityValue | ConstantValue


class PolicyRuleData(TypedDict):
    """A single policy rule with loaded values."""

    name: str
    enabled: bool
    source: NotRequired[list[str]]
    target: NotRequired[list[str]]
    price: NDArray[np.float64] | float


class PolicyConfigSchema(TypedDict):
    """Policy element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.POLICY]
    name: str
    rules: Annotated[
        list[PolicyRuleConfig],
        ListFieldHints(
            fields={
                CONF_ENABLED: FieldHint(
                    output_type=OutputType.STATUS,
                    default_value=True,
                ),
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


def is_policy_config_data(config: object) -> TypeGuard[PolicyConfigData]:
    """Narrow a loaded element config to policy data using the element_type discriminator."""
    return isinstance(config, dict) and config.get("element_type") == ELEMENT_TYPE


def map_references(config: Mapping[str, object], resolve: Callable[[str], str]) -> dict[str, object]:
    """Return the policy with each element its rules name replaced by what resolve returns for it.

    Renaming an element to a name other rules still hold can leave a side
    naming an element twice, or two rules over the same elements. The name is
    kept once and the later rule is dropped, as the policy flow allows neither.
    """
    rules = config[CONF_RULES]
    kept: list[dict[str, object]] = []
    patterns: set[tuple[frozenset[object], ...]] = set()
    for rule in [rule for rule in rules if isinstance(rule, Mapping)] if isinstance(rules, list) else []:
        mapped: dict[str, object] = {
            **rule,
            **{
                key: list(dict.fromkeys(resolve(name) for name in named))
                for key in (CONF_SOURCE, CONF_TARGET)
                if isinstance(named := rule.get(key), list)
            },
        }
        pattern = tuple(
            frozenset(side) if isinstance(side := mapped.get(key), list) else frozenset()
            for key in (CONF_SOURCE, CONF_TARGET)
        )
        if pattern not in patterns:
            patterns.add(pattern)
            kept.append(mapped)
    return {**config, CONF_RULES: kept}


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
    "is_policy_config_data",
    "map_references",
]
