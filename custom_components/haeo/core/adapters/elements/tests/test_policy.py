"""Tests for extracting policy rules from a loaded policy config."""

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE,
    CONF_SOURCE,
    CONF_TARGET,
    WILDCARD,
    PolicyConfigData,
)


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (
            {"rules": []},
            [],
        ),
        (
            {
                "rules": [
                    {
                        "enabled": True,
                        CONF_SOURCE: [],
                        CONF_TARGET: [],
                        CONF_PRICE: 0.05,
                    },
                ],
            },
            [{"sources": [WILDCARD], "destinations": [WILDCARD], "enabled": True, "price": 0.05}],
        ),
        (
            {
                "rules": [
                    {"enabled": True, "source": ["a"], "target": ["b"], "price": {"type": "constant", "value": 0.0}},
                ],
            },
            [{"sources": ["a"], "destinations": ["b"], "enabled": True, "price": {"type": "constant", "value": 0.0}}],
        ),
        (
            {
                "rules": [
                    {"enabled": True, "source": ["g"], "target": ["l"], "price": np.array([0.1, 0.2])},
                ],
            },
            [{"sources": ["g"], "destinations": ["l"], "enabled": True, "price": np.array([0.1, 0.2])}],
        ),
        (
            {
                "rules": [
                    {"enabled": False, "source": ["a"], "target": ["b"], "price": 0.1},
                    {"enabled": True, "source": ["c"], "target": ["d"], "price": 0.2},
                ],
            },
            [
                {"sources": ["a"], "destinations": ["b"], "enabled": False, "price": 0.1},
                {"sources": ["c"], "destinations": ["d"], "enabled": True, "price": 0.2},
            ],
        ),
    ],
)
def test_extract_policy_rules(config: PolicyConfigData, expected: list[dict[str, object]]) -> None:
    """Rules map to compile_policies input shape; empty endpoints become wildcards."""
    actual = extract_policy_rules(config)
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected, strict=True):
        assert got.keys() == want.keys()
        for key in want:
            gv, wv = got[key], want[key]
            if isinstance(wv, np.ndarray):
                np.testing.assert_array_equal(gv, wv)
            else:
                assert gv == wv
