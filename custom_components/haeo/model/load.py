"""Load entity for electrical system modeling."""

from collections.abc import Mapping
from typing import Final, Literal

from pulp import LpVariable

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from .output_data import OutputData
from .source_sink import SOURCE_SINK_POWER_BALANCE, SourceSink

LOAD_POWER_CONSUMED: Final = "load_power_consumed"

LOAD_POWER_BALANCE: Final = "load_power_balance"

type LoadConstraintName = Literal["load_power_balance"]

type LoadOutputName = Literal["load_power_consumed"] | LoadConstraintName

LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER_CONSUMED,
        LOAD_POWER_BALANCE,
    )
)


class Load(SourceSink[LoadOutputName, LoadConstraintName]):
    """Load entity for electrical system modeling.
    
    Load acts as an infinite sink. Power limits and pricing are configured
    on the Connection to the load.
    
    Inherits from SourceSink but provides load-specific output names for translations.
    """

    def __init__(self, name: str, period: float, n_periods: int) -> None:
        """Initialize a load.

        Args:
            name: Name of the load
            period: Time period in hours
            n_periods: Number of periods

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # power_consumed: positive when consuming power (load draws from network)
        self.power_consumed = [LpVariable(name=f"{name}_consumed_{i}", lowBound=0) for i in range(n_periods)]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the load.

        This includes power balance constraints using connection_power().
        Power limits are handled by the Connection to the load.
        """
        # Use load-specific constraint name for translations
        self._constraints[LOAD_POWER_BALANCE] = [
            self.connection_power(t) - self.power_consumed[t] == 0 for t in range(self.n_periods)
        ]

    def outputs(self) -> Mapping[LoadOutputName, OutputData]:
        """Return load output specifications."""

        outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_consumed, direction="-"
            ),
        }

        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
