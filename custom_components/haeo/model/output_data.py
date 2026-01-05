"""Output data specification for model elements."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .const import OutputType


@dataclass(slots=True)
class OutputData:
    """Specification for an output exposed by a model element.

    Attributes:
        name: The unique name identifying this output.
        type: The output type (power, energy, SOC, etc.).
        unit: The unit of measurement for the output values (e.g., "W", "Wh", "%").
        values: The sequence of output values.
        direction: Power flow direction relative to the element.
            "+" = power flowing into element (charge, import, consumption) or toward target (connections).
            "-" = power flowing out of element (discharge, export, production) or toward source (connections).
            None = non-directional output (SOC, prices, energy, shadow prices).
        advanced: Whether the output is intended for advanced diagnostics only.

    """

    name: str
    type: OutputType
    unit: str | None
    values: Sequence[Any]
    direction: Literal["+", "-"] | None = None
    advanced: bool = False

    def __init__(
        self,
        name: str,
        type: OutputType,  # noqa: A002
        unit: str | None,
        values: Sequence[Any] | Any,
        direction: Literal["+", "-"] | None = None,
        *,
        advanced: bool = False,
    ) -> None:
        """Initialize OutputData.

        Args:
            name: The unique name identifying this output.
            type: The output type (power, energy, SOC, etc.).
            unit: The unit of measurement for the output values.
            values: A single value or sequence of values (already extracted from HiGHS types).
            direction: Power flow direction relative to the element.
            advanced: Whether the output is intended for advanced diagnostics only.

        """
        self.name = name
        self.type = type
        self.unit = unit
        self.direction = direction
        self.advanced = advanced

        # Normalize to a tuple
        if isinstance(values, np.ndarray):
            # Convert numpy arrays to tuple (flattens properly)
            self.values = tuple(values.flat)
        elif isinstance(values, Sequence) and not isinstance(values, str):
            # Convert sequences to tuple
            self.values = tuple(values)
        else:
            # Wrap single values in tuple
            self.values = (values,)
