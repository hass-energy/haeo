"""Adapter mapping cases, one module per registered element type.

Each module defines ``CREATE_CASES`` for ``model_elements`` and ``OUTPUTS_CASES`` for ``outputs``.
Modules are found through the adapter registry, so a registered type without a module fails collection.
"""

from collections.abc import Mapping
from importlib import import_module
from typing import TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementConfigData


class CreateCase(TypedDict):
    """A loaded config and the model elements its adapter builds from it."""

    description: str
    data: ElementConfigData
    model: list[dict[str, object]]


class OutputsCase(TypedDict):
    """Model outputs for an element and the device outputs its adapter maps them to."""

    description: str
    data: ElementConfigData
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    periods: NDArray[np.float64]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: list[CreateCase] = [
    case for element_type in ELEMENT_TYPES for case in import_module(f"{__name__}.{element_type}").CREATE_CASES
]
OUTPUTS_CASES: list[OutputsCase] = [
    case for element_type in ELEMENT_TYPES for case in import_module(f"{__name__}.{element_type}").OUTPUTS_CASES
]
