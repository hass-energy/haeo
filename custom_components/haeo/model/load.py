"""Load entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from pulp import LpAffineExpression

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence

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


class Load(Element[LoadOutputName, LoadConstraintName]):
    """Load entity for electrical system modeling."""

    def __init__(self, name: str, period: float, n_periods: int, forecast: Sequence[float] | float) -> None:
        """Initialize a load.

        Args:
            name: Name of the load
            period: Time period in hours
            n_periods: Number of periods
            forecast: Sequence of forecasted power consumption values in kW

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Validate forecast length strictly before broadcasting
        # Since input does not accept float, we require exactly n_periods
        if isinstance(forecast, Sequence) and len(forecast) != n_periods:
            msg = f"Sequence length {len(forecast)} must match n_periods {n_periods}"
            raise ValueError(msg)

        # Validate forecast length and store as power consumption
        self.power_consumption: list[LpAffineExpression] = [
            LpAffineExpression(constant=v) for v in broadcast_to_sequence(forecast, n_periods)
        ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the load.

        This includes power balance constraints using connection_power().
        """
        self._constraints[LOAD_POWER_BALANCE] = [
            self.connection_power(t) - self.power_consumption[t] == 0 for t in range(self.n_periods)
        ]

    def outputs(self) -> Mapping[LoadOutputName, OutputData]:
        """Return load output specifications."""

        outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_consumption, direction="-"
            ),
        }

        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
