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
GRID_PRICE_IMPORT: Final = "grid_price_import"
GRID_PRICE_EXPORT: Final = "grid_price_export"

GRID_POWER_BALANCE: Final = "grid_power_balance"
GRID_MAX_IMPORT_POWER: Final = "grid_max_import_power"
GRID_MAX_EXPORT_POWER: Final = "grid_max_export_power"

type GridConstraintName = Literal[
    "grid_power_balance",
    "grid_max_import_power",
    "grid_max_export_power",
]

type GridOutputName = (
    Literal[
        "grid_power_imported",
        "grid_power_exported",
        "grid_price_import",
        "grid_price_export",
    ]
    | GridConstraintName
)

GRID_OUTPUT_NAMES: Final[frozenset[GridOutputName]] = frozenset(
    (
        GRID_POWER_IMPORTED,
        GRID_POWER_EXPORTED,
        GRID_PRICE_IMPORT,
        GRID_PRICE_EXPORT,
        GRID_POWER_BALANCE,
        GRID_MAX_IMPORT_POWER,
        GRID_MAX_EXPORT_POWER,
    )
)


class Grid(Element[GridOutputName, GridConstraintName]):
    """Unified Grid entity for electrical system modeling with separate import/export pricing."""

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        import_limit: float | None = None,
        export_limit: float | None = None,
        import_price: Sequence[float] | None = None,
        export_price: Sequence[float] | None = None,
    ) -> None:
        """Initialize a grid connection entity.

        Args:
            name: Name of the grid connection
            periods: Sequence of time period durations in hours (one per optimization interval)
            import_limit: Maximum import power in kW
            export_limit: Maximum export power in kW
            import_price: Price in $/kWh when importing
            export_price: Price in $/kWh when exporting

        """
        super().__init__(name=name, periods=periods)
        n_periods = self.n_periods

        # Validate import_price length strictly
        if isinstance(import_price, Sequence) and len(import_price) != n_periods:
            msg = f"Sequence length {len(import_price)} must match n_periods {n_periods}"
            raise ValueError(msg)

        # Validate export_price length strictly
        if isinstance(export_price, Sequence) and len(export_price) != n_periods:
            msg = f"Sequence length {len(export_price)} must match n_periods {n_periods}"
            raise ValueError(msg)

        # Validate and store prices
        self.import_price = broadcast_to_sequence(import_price, n_periods)
        self.export_price = broadcast_to_sequence(export_price, n_periods)

        # power_export: positive when exporting to grid (grid consuming our power)
        self.power_export = [LpVariable(name=f"{name}_export_{i}", lowBound=0) for i in range(n_periods)]
        # power_import: positive when importing from grid (grid producing power for us)
        self.power_import = [LpVariable(name=f"{name}_import_{i}", lowBound=0) for i in range(n_periods)]

        # Add explicit constraints for limits to capture shadow prices
        if export_limit is not None:
            self._constraints[GRID_MAX_EXPORT_POWER] = [self.power_export[t] <= export_limit for t in range(n_periods)]
        if import_limit is not None:
            self._constraints[GRID_MAX_IMPORT_POWER] = [self.power_import[t] <= import_limit for t in range(n_periods)]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the grid.

        This includes power balance constraints using connection_power().
        """
        self._constraints[GRID_POWER_BALANCE] = [
            self.connection_power(t) - self.power_export[t] + self.power_import[t] == 0 for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the grid connection."""
        costs: list[LpAffineExpression] = []
        # Export pricing (revenue when exporting) - using variable period durations
        if self.export_price is not None:
            costs.append(
                lpSum(
                    -price * power * period
                    for price, power, period in zip(self.export_price, self.power_export, self.periods, strict=True)
                )
            )

        # Import pricing (cost when importing) - using variable period durations
        if self.import_price is not None:
            costs.append(
                lpSum(
                    price * power * period
                    for price, power, period in zip(self.import_price, self.power_import, self.periods, strict=True)
                )
            )

        return costs

    def outputs(self) -> Mapping[GridOutputName, OutputData]:
        """Return the outputs for the grid with import/export naming."""

        outputs: dict[GridOutputName, OutputData] = {
            GRID_POWER_EXPORTED: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_export, direction="-"),
            GRID_POWER_IMPORTED: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_import, direction="+"),
        }

        if self.export_price is not None:
            outputs[GRID_PRICE_EXPORT] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=self.export_price, direction="-"
            )
        if self.import_price is not None:
            outputs[GRID_PRICE_IMPORT] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=self.import_price, direction="+"
            )

        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._constraints[constraint_name],
            )

        return outputs
