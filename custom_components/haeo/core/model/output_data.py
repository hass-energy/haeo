"""Output data specification for model elements."""

from collections.abc import Mapping, Sequence
from dataclasses import KW_ONLY, dataclass
from typing import (
    Any,  # noqa: TID251  # values mixes float (most outputs) and str (STATUS); adapters outside
    # core/ do float arithmetic on values without narrowing, so a precise union would break them
    Literal,
)

from .const import OutputType


@dataclass(slots=True)
class OutputData:
    """Specification for an output exposed by a model element.

    Attributes:
        type: The output type (power, energy, SOC, etc.).
        unit: The unit of measurement for the output values (e.g., "W", "Wh", "%").
        values: The sequence of output values, stored as a tuple.
        direction: Power flow direction from the energy system's perspective.
            "+" = production: power added to the system (solar generation, battery discharge, grid import).
            "-" = consumption: power removed from the system (load demand, battery charge, grid export).
            For a state of charge line, the flow the line holds the batteries ready for:
            "+" for a level held to discharge from (a reserve), "-" for room held to charge into (headroom).
            None = non-directional output (plain SOC, prices, energy, shadow prices).
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

    """

    type: OutputType
    unit: str | None
    values: Sequence[Any]
    direction: Literal["+", "-"] | None = None
    _: KW_ONLY
    advanced: bool = False
    state_last: bool = False
    state: float | None = None
    priority: int | None = None
    fixed: bool = False
    display_precision: int | None = None

    def __post_init__(self) -> None:
        """Store the values as a tuple, so the output does not share a list its caller may change."""
        self.values = tuple(self.values)


type ModelOutputValue = OutputData | Mapping[str, OutputData] | Mapping[str, Mapping[str, OutputData]]
