"""Grid entity for electrical system modeling with separate import/export pricing."""

from collections.abc import Mapping, Sequence

import numpy as np
from pulp import LpVariable

from .const import (
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_NAME_POWER_EXPORTED,
    OUTPUT_NAME_POWER_IMPORTED,
    OUTPUT_NAME_POWER_PRODUCED,
    OUTPUT_NAME_PRICE_CONSUMPTION,
    OUTPUT_NAME_PRICE_EXPORT,
    OUTPUT_NAME_PRICE_IMPORT,
    OUTPUT_NAME_PRICE_PRODUCTION,
    OUTPUT_NAME_SHADOW_PRICE_POWER_CONSUMPTION_MAX,
    OUTPUT_NAME_SHADOW_PRICE_POWER_EXPORT_MAX,
    OUTPUT_NAME_SHADOW_PRICE_POWER_IMPORT_MAX,
    OUTPUT_NAME_SHADOW_PRICE_POWER_PRODUCTION_MAX,
    OutputData,
    OutputName,
)
from .element import Element


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
        import_price: Sequence[float] | float | None = None,
        export_price: Sequence[float] | float | None = None,
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

        # power_consumption: positive when exporting to grid (grid consuming our power)
        power_consumption = [
            LpVariable(name=f"{name}_export_{i}", lowBound=0, upBound=export_limit) for i in range(n_periods)
        ]
        # power_production: positive when importing from grid (grid producing power for us)
        power_production = [
            LpVariable(name=f"{name}_import_{i}", lowBound=0, upBound=import_limit) for i in range(n_periods)
        ]

        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_consumption=power_consumption,  # Consuming = exporting (grid consuming our power)
            power_production=power_production,  # Producing = importing (grid producing power for us)
            price_consumption=None
            if export_price is None
            else (np.ones(n_periods) * export_price).tolist(),  # Revenue when exporting (grid pays us)
            price_production=None
            if import_price is None
            else (np.ones(n_periods) * import_price).tolist(),  # Cost when importing (we pay grid)
        )

    def get_outputs(self) -> Mapping[OutputName, OutputData]:
        """Return the outputs for the grid with import/export naming."""

        mapping: dict[OutputName, OutputName] = {
            OUTPUT_NAME_POWER_CONSUMED: OUTPUT_NAME_POWER_EXPORTED,
            OUTPUT_NAME_POWER_PRODUCED: OUTPUT_NAME_POWER_IMPORTED,
            OUTPUT_NAME_PRICE_CONSUMPTION: OUTPUT_NAME_PRICE_EXPORT,
            OUTPUT_NAME_PRICE_PRODUCTION: OUTPUT_NAME_PRICE_IMPORT,
            OUTPUT_NAME_SHADOW_PRICE_POWER_CONSUMPTION_MAX: OUTPUT_NAME_SHADOW_PRICE_POWER_EXPORT_MAX,
            OUTPUT_NAME_SHADOW_PRICE_POWER_PRODUCTION_MAX: OUTPUT_NAME_SHADOW_PRICE_POWER_IMPORT_MAX,
        }

        # Remap the output names accordingly
        return {mapping.get(key, key): value for key, value in super().get_outputs().items()}
