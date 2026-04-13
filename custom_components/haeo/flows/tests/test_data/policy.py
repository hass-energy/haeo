"""Test data and validation for policy flow configuration."""

from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
)

VALID_DATA = [
    {
        "description": "Basic policy configuration with one rule",
        "config": {
            CONF_RULES: [
                {
                    "name": "Solar Export Policy",
                    CONF_SOURCE: "Solar",
                    CONF_TARGET: "Grid",
                    CONF_PRICE: 0.02,
                },
            ],
        },
    },
    {
        "description": "Policy with wildcard source (source omitted)",
        "config": {
            CONF_RULES: [
                {
                    "name": "Any to Load",
                    CONF_TARGET: "Load",
                    CONF_PRICE: 0.05,
                },
            ],
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
