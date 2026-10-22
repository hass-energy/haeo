"""Adapter mapping cases for the policy element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.policy import POLICY_DEVICE_POLICY
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.policy import PolicyConfigData

from . import CreateCase, OutputsCase

POLICIES = PolicyConfigData(
    element_type=ElementType.POLICY,
    name="Policies",
    rules=[{"name": "Grid to house", "enabled": True, "source": ["grid"], "target": ["house"], "price": 0.1}],
)

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Policies compile into other elements' connections, not model elements of their own",
        "data": POLICIES,
        "model": [],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Policy device has no outputs",
        "data": POLICIES,
        "model_outputs": {},
        "periods": np.array([1.0]),
        "outputs": {POLICY_DEVICE_POLICY: {}},
    },
]
