"""Grid entity for electrical system modeling with separate import/export pricing."""

from collections.abc import Mapping, Sequence

from pulp import LpAffineExpression, LpVariable, lpSum

from .const import (
    CONSTRAINT_NAME_POWER_BALANCE,
    OUTPUT_NAME_POWER_EXPORTED,
    OUTPUT_NAME_POWER_IMPORTED,
    OUTPUT_NAME_PRICE_EXPORT,
    OUTPUT_NAME_PRICE_IMPORT,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OutputData,
    OutputName,
)
from .element import Element
from .util import broadcast_to_sequence, extract_values


class Grid(Element):
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

        # power_consumption: positive when exporting to grid (grid consuming our power)
        self.power_consumption = [
            LpVariable(name=f"{name}_export_{i}", lowBound=0, upBound=export_limit) for i in range(n_periods)
        ]
        # power_production: positive when importing from grid (grid producing power for us)
        self.power_production = [
            LpVariable(name=f"{name}_import_{i}", lowBound=0, upBound=import_limit) for i in range(n_periods)
        ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the grid.

        This includes power balance constraints using connection_power().
        """
        self._constraints[CONSTRAINT_NAME_POWER_BALANCE] = [
            self.connection_power(t) - self.power_consumption[t] + self.power_production[t] == 0
            for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the grid connection."""
        costs: list[LpAffineExpression] = []
        # Export pricing (revenue when exporting)
        if self.export_price is not None:
            costs.append(
                lpSum(
                    -price * power * self.period
                    for price, power in zip(self.export_price, self.power_consumption, strict=True)
                )
            )

        # Import pricing (cost when importing)
        if self.import_price is not None:
            costs.append(
                lpSum(
                    price * power * self.period
                    for price, power in zip(self.import_price, self.power_production, strict=True)
                )
            )

        return costs

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return the outputs for the grid with import/export naming."""

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_EXPORTED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_consumption)
            ),
            OUTPUT_NAME_POWER_IMPORTED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_production)
            ),
        }

        if self.export_price is not None:
            outputs[OUTPUT_NAME_PRICE_EXPORT] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.export_price)
            )
        if self.import_price is not None:
            outputs[OUTPUT_NAME_PRICE_IMPORT] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.import_price)
            )

        return outputs
