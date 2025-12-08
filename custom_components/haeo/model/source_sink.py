"""Base SourceSink entity for electrical system modeling."""

from collections.abc import Mapping
from typing import Final, Literal, TypeVar

from pulp import LpVariable

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData

# Element-agnostic output names
SOURCE_SINK_POWER_IN: Final = "source_sink_power_in"
SOURCE_SINK_POWER_OUT: Final = "source_sink_power_out"
SOURCE_SINK_POWER_BALANCE: Final = "source_sink_power_balance"

type SourceSinkConstraintName = Literal["source_sink_power_balance"]

type SourceSinkOutputName = Literal["source_sink_power_in", "source_sink_power_out"] | SourceSinkConstraintName

SOURCE_SINK_OUTPUT_NAMES: Final[frozenset[SourceSinkOutputName]] = frozenset(
    (
        SOURCE_SINK_POWER_IN,
        SOURCE_SINK_POWER_OUT,
        SOURCE_SINK_POWER_BALANCE,
    )
)

# Type variables for subclass customization (for adapter layer mapping)
TOutputName = TypeVar("TOutputName", bound=str)
TConstraintName = TypeVar("TConstraintName", bound=str)


class SourceSink(Element[TOutputName, TConstraintName]):
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
        period: float,
        n_periods: int,
        *,
        is_source: bool = True,
        is_sink: bool = True,
    ) -> None:
        """Initialize a source/sink entity.

        Args:
            name: Name of the source/sink
            period: Time period in hours
            n_periods: Number of time periods
            is_source: Whether this element can produce power (source behavior)
            is_sink: Whether this element can consume power (sink behavior)

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        self.is_source = is_source
        self.is_sink = is_sink

        # Element-agnostic power variables (only create if needed)
        # power_in: positive when accepting power from network (sink behavior)
        self.power_in = (
            [LpVariable(name=f"{name}_power_in_{i}", lowBound=0) for i in range(n_periods)] if is_sink else None
        )
        # power_out: positive when providing power to network (source behavior)
        self.power_out = (
            [LpVariable(name=f"{name}_power_out_{i}", lowBound=0) for i in range(n_periods)] if is_source else None
        )

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the source/sink.

        This includes power balance constraints using connection_power().
        Power limits and pricing are handled by the Connection to/from the source/sink.
        """
        # Build power balance based on is_source and is_sink flags
        if not self.is_source and not self.is_sink:
            # Pure junction (Node): connection power must be zero
            self._constraints[SOURCE_SINK_POWER_BALANCE] = [
                self.connection_power(t) == 0 for t in range(self.n_periods)
            ]
        elif self.is_source and not self.is_sink:
            # Source only: connection power equals power out
            if self.power_out is None:
                msg = f"Source-only SourceSink '{self.name}' must have power_out configured"
                raise ValueError(msg)
            self._constraints[SOURCE_SINK_POWER_BALANCE] = [
                self.connection_power(t) - self.power_out[t] == 0 for t in range(self.n_periods)
            ]
        elif not self.is_source and self.is_sink:
            # Sink only: connection power equals negative power in
            if self.power_in is None:
                msg = f"Sink-only SourceSink '{self.name}' must have power_in configured"
                raise ValueError(msg)
            self._constraints[SOURCE_SINK_POWER_BALANCE] = [
                self.connection_power(t) + self.power_in[t] == 0 for t in range(self.n_periods)
            ]
        else:
            # Both source and sink: connection power equals power out minus power in
            if self.power_out is None or self.power_in is None:
                msg = f"SourceSink '{self.name}' with both source and sink must have both power_out and power_in configured"
                raise ValueError(msg)
            self._constraints[SOURCE_SINK_POWER_BALANCE] = [
                self.connection_power(t) - self.power_out[t] + self.power_in[t] == 0 for t in range(self.n_periods)
            ]

    def outputs(self) -> Mapping[SourceSinkOutputName, OutputData]:
        """Return element-agnostic outputs for the source/sink.

        Adapter layer maps these to element-specific names (grid_power_imported, load_power_consumed, etc.)
        """
        outputs: dict[SourceSinkOutputName, OutputData] = {}

        if self.power_in is not None:
            outputs[SOURCE_SINK_POWER_IN] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_in, direction="-"
            )
        if self.power_out is not None:
            outputs[SOURCE_SINK_POWER_OUT] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_out, direction="+"
            )

        for constraint_name in self._constraints:
            # All constraints are power balance for SourceSink
            outputs[SOURCE_SINK_POWER_BALANCE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
