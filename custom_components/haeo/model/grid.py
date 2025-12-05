"""Grid entity for electrical system modeling with separate import/export pricing."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from pulp import LpAffineExpression, LpVariable, lpSum

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_PRICE, OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence

GRID_POWER_IMPORTED: Final = "grid_power_imported"
GRID_POWER_EXPORTED: Final = "grid_power_exported"

GRID_POWER_BALANCE: Final = "grid_power_balance"

type GridConstraintName = Literal[
    "grid_power_balance",
]

type GridOutputName = (
    Literal[
        "grid_power_imported",
        "grid_power_exported",
    ]
    | GridConstraintName
)

GRID_OUTPUT_NAMES: Final[frozenset[GridOutputName]] = frozenset(
    (
        GRID_POWER_IMPORTED,
        GRID_POWER_EXPORTED,
        GRID_POWER_BALANCE,
    )
)


class Grid(Element[GridOutputName, GridConstraintName]):
    """Unified Grid entity for electrical system modeling.
    
    Grid acts as an infinite source/sink. Power limits and pricing are configured
    on the Connection to the grid.
    """

    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
    ) -> None:
        """Initialize a grid connection entity.

        Args:
            name: Name of the grid connection
            period: Time period in hours
            n_periods: Number of time periods

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # power_export: positive when exporting to grid (grid consuming our power)
        self.power_export = [LpVariable(name=f"{name}_export_{i}", lowBound=0) for i in range(n_periods)]
        # power_import: positive when importing from grid (grid producing power for us)
        self.power_import = [LpVariable(name=f"{name}_import_{i}", lowBound=0) for i in range(n_periods)]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the grid.

        This includes power balance constraints using connection_power().
        Power limits and pricing are handled by the Connection to the grid.
        """
        self._constraints[GRID_POWER_BALANCE] = [
            self.connection_power(t) - self.power_export[t] + self.power_import[t] == 0 for t in range(self.n_periods)
        ]

    def outputs(self) -> Mapping[GridOutputName, OutputData]:
        """Return the outputs for the grid with import/export naming."""

        outputs: dict[GridOutputName, OutputData] = {
            GRID_POWER_EXPORTED: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_export, direction="-"),
            GRID_POWER_IMPORTED: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_import, direction="+"),
        }

        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
