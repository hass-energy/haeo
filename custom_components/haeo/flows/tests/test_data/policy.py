"""Test data for policy configuration as the policy flow stores it."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.core.schema.elements.policy import (
    CONF_ENABLED,
    CONF_PRICE,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
)

VALID_DATA = [
    {
        "description": "Basic policy configuration with one rule",
        "config": {
            CONF_NAME: "Policies",
            CONF_RULES: [
                {
                    "name": "Solar Export Policy",
                    CONF_ENABLED: True,
                    CONF_SOURCE: ["Solar"],
                    CONF_TARGET: ["Grid"],
                    CONF_PRICE: as_constant_value(0.02),
                },
            ],
        },
    },
    {
        "description": "Policy with wildcard source (source omitted)",
        "config": {
            CONF_NAME: "Policies",
            CONF_RULES: [
                {
                    "name": "Any to Load",
                    CONF_ENABLED: True,
                    CONF_TARGET: ["Load"],
                    CONF_PRICE: as_constant_value(0.05),
                },
            ],
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
