"""Base SourceSink entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_var

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData

type SourceSinkConstraintName = Literal["source_sink_power_balance"]

type SourceSinkOutputName = Literal["source_sink_power_in", "source_sink_power_out"] | SourceSinkConstraintName

SOURCE_SINK_OUTPUT_NAMES: Final[frozenset[SourceSinkOutputName]] = frozenset(
    (
        SOURCE_SINK_POWER_IN := "source_sink_power_in",
        SOURCE_SINK_POWER_OUT := "source_sink_power_out",
        SOURCE_SINK_POWER_BALANCE := "source_sink_power_balance",
    )
)


class SourceSink(Element[SourceSinkOutputName, SourceSinkConstraintName]):
    """Base SourceSink entity for electrical system modeling.

    SourceSink acts as an infinite source and/or sink. Power limits and pricing are configured
    on the Connection to/from the source/sink.

    Behavior is controlled by is_source and is_sink flags:
    - is_source=True, is_sink=True: Can both produce and consume (Grid)
    - is_source=False, is_sink=True: Can only consume (Load)
    - is_source=True, is_sink=False: Can only produce (Photovoltaics)
    - is_source=False, is_sink=False: Pure junction with no generation/consumption (Node)
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        is_source: bool = True,
        is_sink: bool = True,
    ) -> None:
        """Initialize a source/sink entity.

        Args:
            name: Name of the source/sink
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            is_source: Whether this element can produce power (source behavior)
            is_sink: Whether this element can consume power (sink behavior)

        """
        super().__init__(name=name, periods=periods, solver=solver)
        n_periods = self.n_periods
        h = solver

        # Store flags
        self._is_source = is_source
        self._is_sink = is_sink

        # Create power variables (only if needed)
        # power_in: positive when accepting power from network (sink behavior)
        self.power_in: list[highs_var] | None = None
        if self._is_sink:
            self.power_in = [h.addVariable(lb=0, name=f"{name}_power_in_{i}") for i in range(n_periods)]

        # power_out: positive when providing power to network (source behavior)
        self.power_out: list[highs_var] | None = None
        if self._is_source:
            self.power_out = [h.addVariable(lb=0, name=f"{name}_power_out_{i}") for i in range(n_periods)]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the source/sink.

        This includes power balance constraints using connection_power().
        Variables are created in __init__, this method only adds constraints.
        """
        h = self._solver
        n_periods = self.n_periods

        # Build power balance constraints
        constraints = []
        for t in range(n_periods):
            expr = self.connection_power(t)
            if self.power_out is not None:
                expr = expr + self.power_out[t]
            if self.power_in is not None:
                expr = expr - self.power_in[t]
            constraints.append(expr == 0)

        self._constraints[SOURCE_SINK_POWER_BALANCE] = h.addConstrs(constraints)

    def outputs(self) -> Mapping[SourceSinkOutputName, OutputData]:
        """Return element-agnostic outputs for the source/sink.

        Adapter layer maps these to element-specific names (grid_power_imported, load_power_consumed, etc.)
        """
        solver = self._solver
        outputs: dict[SourceSinkOutputName, OutputData] = {}

        if self.power_in is not None:
            outputs[SOURCE_SINK_POWER_IN] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_in, direction="-", solver=solver
            )
        if self.power_out is not None:
            outputs[SOURCE_SINK_POWER_OUT] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_out, direction="+", solver=solver
            )

        # All constraints are power balance for SourceSink
        outputs[SOURCE_SINK_POWER_BALANCE] = OutputData(
            type=OUTPUT_TYPE_SHADOW_PRICE,
            unit="$/kW",
            values=self._constraints[SOURCE_SINK_POWER_BALANCE],
            solver=solver,
        )

        return outputs
