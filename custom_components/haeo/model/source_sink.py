"""Base SourceSink entity for electrical system modeling."""

from collections.abc import Mapping
from typing import Final, Literal, TypeVar

from pulp import LpVariable

from .const import OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData

SOURCE_SINK_POWER_BALANCE: Final = "source_sink_power_balance"

type SourceSinkConstraintName = Literal["source_sink_power_balance"]

type SourceSinkOutputName = Literal["source_sink_power"] | SourceSinkConstraintName

# Type variables for subclass customization
TOutputName = TypeVar("TOutputName", bound=str)
TConstraintName = TypeVar("TConstraintName", bound=str)


class SourceSink(Element[TOutputName, TConstraintName]):
    """Base SourceSink entity for electrical system modeling.

    SourceSink acts as an infinite source or sink. Power limits and pricing are configured
    on the Connection to/from the source/sink.

    This is a base class for Grid, Load, and Photovoltaics which all behave as
    infinite sources or sinks with no internal logic beyond power balance.
    """

    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
    ) -> None:
        """Initialize a source/sink entity.

        Args:
            name: Name of the source/sink
            period: Time period in hours
            n_periods: Number of time periods

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Single power variable - positive for source (producing), negative for sink (consuming)
        self.power = [LpVariable(name=f"{name}_power_{i}") for i in range(n_periods)]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the source/sink.

        This includes power balance constraints using connection_power().
        Power limits and pricing are handled by the Connection to/from the source/sink.

        Note: Subclasses should override this to use their specific constraint names.
        """
        # Don't set constraints here - subclasses will override and use their own names

    def outputs(self) -> Mapping[TOutputName, OutputData]:
        """Return the outputs for the source/sink.

        Subclasses must override this to provide element-specific output names.
        """
        # Subclasses should override this to provide element-specific output names
        outputs: dict[TOutputName, OutputData] = {}

        for constraint_name in self._constraints:
            # Constraint names are strings that subclasses ensure match TOutputName
            outputs[constraint_name] = OutputData(  # type: ignore[index]
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
