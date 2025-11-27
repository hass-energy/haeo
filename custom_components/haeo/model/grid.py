"""Grid entity for electrical system modeling with separate import/export pricing."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from pulp import LpAffineExpression, LpVariable, lpSum

from .const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_PRICE, OUTPUT_TYPE_SHADOW_PRICE, OutputData
from .element import Element
from .util import broadcast_to_sequence, extract_values

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
        period: float,
        n_periods: int,
        *,
        import_limit: float | None = None,
        export_limit: float | None = None,
        import_price: Sequence[float] | None = None,
        export_price: Sequence[float] | None = None,
    ) -> None:
        """Initialize a grid connection entity.

        Args:
            name: Name of the grid connection
            period: Time period in hours
            n_periods: Number of time periods
            import_limit: Maximum import power in kW
            export_limit: Maximum export power in kW
            import_price: Price in $/kWh when importing
            export_price: Price in $/kWh when exporting

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

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
        # Export pricing (revenue when exporting)
        if self.export_price is not None:
            costs.append(
                lpSum(
                    -price * power * self.period
                    for price, power in zip(self.export_price, self.power_export, strict=True)
                )
            )

        # Import pricing (cost when importing)
        if self.import_price is not None:
            costs.append(
                lpSum(
                    price * power * self.period
                    for price, power in zip(self.import_price, self.power_import, strict=True)
                )
            )

        return costs

    def outputs(self) -> Mapping[GridOutputName, OutputData]:
        """Return the outputs for the grid with import/export naming."""

        outputs: dict[GridOutputName, OutputData] = {
            GRID_POWER_EXPORTED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_export), direction="-"
            ),
            GRID_POWER_IMPORTED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_import), direction="+"
            ),
        }

        if self.export_price is not None:
            outputs[GRID_PRICE_EXPORT] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.export_price), direction="-"
            )
        if self.import_price is not None:
            outputs[GRID_PRICE_IMPORT] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.import_price), direction="+"
            )

        # Shadow prices
        if shadow_prices := self._get_shadow_prices(GRID_POWER_BALANCE):
            outputs[GRID_POWER_BALANCE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        if shadow_prices := self._get_shadow_prices(GRID_MAX_IMPORT_POWER):
            outputs[GRID_MAX_IMPORT_POWER] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        if shadow_prices := self._get_shadow_prices(GRID_MAX_EXPORT_POWER):
            outputs[GRID_MAX_EXPORT_POWER] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        return outputs
