"""Power limit segment — constrains maximum power flow."""

from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; segments only use these via hasattr/isinstance duck typing.
    Final,
    Literal,
    NotRequired,
)

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import LinearArray, Rows
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import FlowProvider, Segment

SHORTFALL_PRICE: Final = 1000.0
"""Cost of each kWh a fixed flow falls short of its limit ($/kWh), a value of lost load.

High enough that a fixed flow only falls short when the network cannot carry it,
so an unmeetable period gives an expensive plan rather than an infeasible one.
"""


class PowerLimitSegmentSpec(TypedDict):
    """Specification for creating a PowerLimitSegment.

    Directional fields are resolved by the Connection into `max_power`.
    """

    segment_type: Literal["power_limit"]
    max_power: NotRequired[NDArray[np.float64] | float | None]
    fixed: NotRequired[bool | None]
    # Directional aliases — resolved by Connection, not used by segment directly
    max_power_source_target: NotRequired[NDArray[np.float64] | float | None]
    max_power_target_source: NotRequired[NDArray[np.float64] | float | None]


class PowerLimitSegment(Segment):
    """Constrains maximum power flow.

    A fixed limit holds the flow at the limit, less a shortfall priced at
    ``SHORTFALL_PRICE`` for the periods the network cannot carry it.
    """

    max_power: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Solver,
        *,
        spec: PowerLimitSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize power limit segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            upstream=upstream,
        )
        self._shortfall = solver.add_variables(n_periods, name=f"{segment_id}.shortfall") if spec.get("fixed") else None
        self.max_power = broadcast_to_sequence(spec.get("max_power"), self._n_periods)

    @constraint(output=True, unit="$/kWh")
    def power_limit(self) -> Rows:
        """Directional power limit constraint (energy-native).

        Formulated as energy: power * dt <= max_power * dt, or for a fixed limit
        (power + shortfall) * dt == max_power * dt.
        Shadow prices are $/kWh. Without a max power the rows are free, so they
        stay in the LP and can bind later without changing its shape.
        """
        if self._shortfall is None:
            energy = self.total_power_in * self.periods
        else:
            energy = (self.total_power_in + self._shortfall) * self.periods
        if self.max_power is None:
            return energy.free()
        if self._shortfall is None:
            return energy <= self.max_power * self.periods
        return energy == self.max_power * self.periods

    @cost
    def shortfall_cost(self) -> LinearArray | None:
        """Value of the energy a fixed flow falls short of its limit, which the network could not carry."""
        if self._shortfall is None:
            return None
        return (self._shortfall * SHORTFALL_PRICE * self.periods).total()

    @output
    def shortfall(self) -> OutputData | None:
        """Output: power a fixed flow falls short of its limit."""
        if self._shortfall is None:
            return None
        return OutputData(
            type=OutputType.POWER,
            unit="kW",
            values=tuple(self._shortfall.value(self._solver.column_values()).tolist()),
        )


__all__ = [
    "SHORTFALL_PRICE",
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
]
