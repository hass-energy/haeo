"""Photovoltaics entity for electrical system modeling."""

from collections.abc import Mapping
from typing import Final, Literal

from pulp import LpVariable

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from .output_data import OutputData
from .source_sink import SOURCE_SINK_POWER_BALANCE, SourceSink

PHOTOVOLTAICS_POWER_PRODUCED: Final = "photovoltaics_power_produced"

PHOTOVOLTAICS_POWER_BALANCE: Final = "photovoltaics_power_balance"

type PhotovoltaicsConstraintName = Literal[
    "photovoltaics_power_balance",
]

type PhotovoltaicsOutputName = (
    Literal[
        "photovoltaics_power_produced",
    ]
    | PhotovoltaicsConstraintName
)

PHOTOVOLTAICS_OUTPUT_NAMES: Final[frozenset[PhotovoltaicsOutputName]] = frozenset(
    (
        PHOTOVOLTAICS_POWER_PRODUCED,
        PHOTOVOLTAICS_POWER_BALANCE,
    )
)


class Photovoltaics(SourceSink[PhotovoltaicsOutputName, PhotovoltaicsConstraintName]):
    """Photovoltaics (solar) entity for electrical system modeling.
    
    Photovoltaics acts as an infinite power source. Power limits (forecast), curtailment,
    and pricing are configured on the Connection from the photovoltaics.
    
    Inherits from SourceSink but provides photovoltaics-specific output names for translations.
    """

    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
    ) -> None:
        """Initialize a photovoltaics entity.

        Args:
            name: Name of the photovoltaics system
            period: Time period in hours
            n_periods: Number of time periods

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # power_produced: positive when producing power (PV generates to network)
        self.power_produced = [LpVariable(name=f"{name}_produced_{i}", lowBound=0) for i in range(n_periods)]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the photovoltaics.

        This includes power balance constraints using connection_power().
        Power limits (forecast/curtailment) and pricing are handled by the Connection from the photovoltaics.
        """
        # Use photovoltaics-specific constraint name for translations
        self._constraints[PHOTOVOLTAICS_POWER_BALANCE] = [
            self.connection_power(t) + self.power_produced[t] == 0 for t in range(self.n_periods)
        ]

    def outputs(self) -> Mapping[PhotovoltaicsOutputName, OutputData]:
        """Return photovoltaics output specifications."""

        outputs: dict[PhotovoltaicsOutputName, OutputData] = {
            PHOTOVOLTAICS_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_produced, direction="+"
            ),
        }

        # Shadow prices
        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
