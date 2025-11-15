"""Load entity for electrical system modeling."""

from collections.abc import Mapping, Sequence

from pulp import LpAffineExpression

from .const import CONSTRAINT_NAME_POWER_BALANCE, OUTPUT_NAME_POWER_CONSUMED, OUTPUT_TYPE_POWER, OutputData, OutputName
from .element import Element
from .util import broadcast_to_sequence, extract_values


class Load(Element):
    """Load entity for electrical system modeling."""

    def __init__(self, name: str, period: float, n_periods: int, forecast: Sequence[float]) -> None:
        """Initialize a load.

        Args:
            name: Name of the load
            period: Time period in hours
            n_periods: Number of periods
            forecast: Sequence of forecasted power consumption values in kW

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Validate forecast length and store as power consumption
        self.power_consumption: list[LpAffineExpression] = [
            LpAffineExpression(constant=v) for v in broadcast_to_sequence(forecast, n_periods)
        ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the load.

        This includes power balance constraints using connection_power().
        """
        self._constraints[CONSTRAINT_NAME_POWER_BALANCE] = [
            self.connection_power(t) - self.power_consumption[t] == 0 for t in range(self.n_periods)
        ]

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return load output specifications."""

        return {
            OUTPUT_NAME_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_consumption)
            ),
        }
