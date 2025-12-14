"""Output data specification for model elements."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from highspy import Highs

from .const import OutputType
from .util import extract_values


@dataclass(slots=True)
class OutputData:
    """Specification for an output exposed by a model element.

    Attributes:
        type: The output type (power, energy, SOC, etc.).
        unit: The unit of measurement for the output values (e.g., "W", "Wh", "%").
        values: The sequence of output values. HiGHS types are automatically extracted.
        direction: Power flow direction relative to the element.
            "+" = power flowing into element (charge, import, consumption) or toward target (connections).
            "-" = power flowing out of element (discharge, export, production) or toward source (connections).
            None = non-directional output (SOC, prices, energy, shadow prices).
        advanced: Whether the output is intended for advanced diagnostics only.

    """

    type: OutputType
    unit: str | None
    values: Sequence[Any]
    direction: Literal["+", "-"] | None = None
    advanced: bool = False

    def __init__(
        self,
        type: OutputType,  # noqa: A002
        unit: str | None,
        values: Sequence[Any] | Any,
        direction: Literal["+", "-"] | None = None,
        *,
        advanced: bool = False,
        solver: Highs | None = None,
    ) -> None:
        """Initialize OutputData with optional HiGHS value extraction.

        Args:
            type: The output type (power, energy, SOC, etc.).
            unit: The unit of measurement for the output values.
            values: A single value or sequence of values. HiGHS types are automatically
                converted to floats if solver is provided, otherwise stored raw.
            direction: Power flow direction relative to the element.
            advanced: Whether the output is intended for advanced diagnostics only.
            solver: The HiGHS solver instance for value extraction. If provided,
                values are extracted immediately. If None, raw values are stored.

        """
        self.type = type
        self.unit = unit
        self.direction = direction
        self.advanced = advanced

        # Normalize to a sequence (single values wrapped in tuple)
        raw = tuple(values) if isinstance(values, Sequence) and not isinstance(values, str) else (values,)

        # Extract values (with or without solver)
        self.values = extract_values(raw, solver)
