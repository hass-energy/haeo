"""Output data specification for model elements."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .const import OutputType


@dataclass(slots=True)
class OutputData:
    """Specification for an output exposed by a model element.

    Attributes:
        type: The output type (power, energy, SOC, etc.).
        unit: The unit of measurement for the output values (e.g., "W", "Wh", "%").
        values: The sequence of output values.
        direction: Power flow direction from the energy system's perspective.
            "+" = production: power added to the system (solar generation, battery discharge, grid import).
            "-" = consumption: power removed from the system (load demand, battery charge, grid export).
            None = non-directional output (SOC, prices, energy, shadow prices).
        advanced: Whether the output is intended for advanced diagnostics only.
        state_last: If True, the sensor state uses the last value instead of the first.
            Use for cumulative values where the total is the meaningful current state.
        state: Optional scalar that overrides the sensor state (taking precedence over
            ``state_last`` / ``values[0]``). Use when the per-interval ``values``
            sequence should drive the forecast attribute but a separately computed
            scalar (e.g. a clipped 24h total or a running total) is the meaningful
            state.
        priority: Connection time-preference priority. Lower values are preferred
            earlier by the secondary objective. None for non-connection outputs.
        fixed: Whether the output is constrained to equal its forecast (no curtailment).
        display_precision: Suggested number of decimal places to display in the UI.
            Surfaces as Home Assistant's ``suggested_display_precision`` on the
            sensor entity. Use to override HAEO's smart-rounding default when a
            sensor has a natural display scale (e.g. dollars to 2 dp). None
            preserves the existing smart-rounding behaviour.
        range_up: Upper capacity range (how much RHS can increase at same shadow price).
        range_dn: Lower capacity range (how much RHS can decrease at same shadow price).

    """

    type: OutputType
    unit: str | None
    values: Sequence[Any]
    direction: Literal["+", "-"] | None = None
    advanced: bool = False
    state_last: bool = False
    state: float | None = None
    priority: int | None = None
    fixed: bool = False
    display_precision: int | None = None
    range_up: Sequence[Any] | None = None
    range_dn: Sequence[Any] | None = None

    def __init__(
        self,
        type: OutputType,  # noqa: A002 (shadows builtin but matches OutputType field naming convention)
        unit: str | None,
        values: Sequence[Any] | Any,
        direction: Literal["+", "-"] | None = None,
        *,
        advanced: bool = False,
        state_last: bool = False,
        state: float | None = None,
        priority: int | None = None,
        fixed: bool = False,
        display_precision: int | None = None,
        range_up: Sequence[Any] | None = None,
        range_dn: Sequence[Any] | None = None,
    ) -> None:
        """Initialize OutputData.

        Args:
            type: The output type (power, energy, SOC, etc.).
            unit: The unit of measurement for the output values.
            values: A single value or sequence of values (already extracted from HiGHS types).
            direction: Power flow direction relative to the element.
            advanced: Whether the output is intended for advanced diagnostics only.
            state_last: If True, the sensor state uses the last value instead of the first.
            state: Optional scalar that overrides the sensor state. When provided,
                takes precedence over ``state_last`` so the forecast and state can
                report different views of the same series.
            priority: The connection priority for this output, if applicable.
            fixed: Whether the output is constrained to equal its forecast (no curtailment).
            display_precision: Optional suggested decimal places for the sensor UI.
            range_up: Upper capacity range (how much RHS can increase at same shadow price).
            range_dn: Lower capacity range (how much RHS can decrease at same shadow price).

        """
        self.type = type
        self.unit = unit
        self.direction = direction
        self.advanced = advanced
        self.state_last = state_last
        self.state = state
        self.priority = priority
        self.fixed = fixed
        self.display_precision = display_precision
        self.range_up = range_up
        self.range_dn = range_dn

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


type ModelOutputValue = OutputData | Mapping[str, OutputData] | Mapping[str, Mapping[str, OutputData]]
