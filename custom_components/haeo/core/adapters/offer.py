"""Grid offer curves: the grid power a plan would take at each price over a window of time.

A grid's offer curve shifts its import and export prices by the same amount in
every period of a window, as a change in the wholesale price over a market
interval passes through to both, and leaves every other period's prices as
forecast. Each step is given as the window's average import and export prices
it starts at and the average net grid power over the window at prices in it,
positive for import, as the grid's active power sensor reports it.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model import Network, OfferCurve
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments.pricing import PricingSegment


@dataclass(frozen=True, slots=True)
class GridOfferStep:
    """Average net grid power over a window at prices from these up to the next step's.

    Attributes:
        import_price: Average import price over the window in $/kWh at which the step starts.
        export_price: Average export price over the window in $/kWh at which the step starts.
        power: Average net grid power over the window in kW, positive for import.

    """

    import_price: float
    export_price: float
    power: float


@dataclass(frozen=True, slots=True)
class GridOffer:
    """A grid's offer curve over a window of periods.

    Attributes:
        periods: Indices of the periods in the window.
        import_price: Average forecast import price over the window in $/kWh.
        export_price: Average forecast export price over the window in $/kWh.
        power: Average net grid power over the window in kW at the forecast prices, positive for import.
        steps: Steps in rising price order, power falling from each to the next.

    """

    periods: tuple[int, ...]
    import_price: float
    export_price: float
    power: float
    steps: tuple[GridOfferStep, ...]


def _connection(network: Network, name: str) -> Connection[str]:
    connection = network.elements[name]
    if not isinstance(connection, Connection):
        msg = f"{name} is not a connection"
        raise TypeError(msg)
    return connection


def _price(connection: Connection[str], n_periods: int) -> NDArray[np.float64]:
    """Return the price of each kWh through a connection, each period."""
    segment = connection.segments["pricing"]
    if not isinstance(segment, PricingSegment):
        msg = f"{connection.name} has no pricing segment"
        raise TypeError(msg)
    return np.broadcast_to(np.asarray(segment.price, dtype=np.float64), (n_periods,))


def _average(values: NDArray[np.float64], durations: NDArray[np.float64], window: Sequence[int]) -> float:
    """Return the average of per-period values over a window, weighting each period by its duration."""
    periods = np.asarray(window, dtype=np.intp)
    return float(np.average(values[periods], weights=durations[periods]))


def grid_offers(
    network: Network,
    grid: str,
    *,
    windows: Sequence[Sequence[int]],
    min_price: float,
    max_price: float,
) -> list[GridOffer]:
    """Return a grid's offer curve over each of the given windows of a solved network.

    Args:
        network: The network, holding the plan its last optimization found.
        grid: Name of the grid element.
        windows: Indices of the consecutive periods in each window.
        min_price: Lowest average import price in $/kWh to trace each curve from.
        max_price: Highest average import price in $/kWh to trace each curve to.
            The range always takes in the forecast price.

    """
    grid_import = _connection(network, f"{grid}:import")
    grid_export = _connection(network, f"{grid}:export")
    import_price = _price(grid_import, network.n_periods)
    # The export connection prices exported energy as a negative cost
    export_price = -_price(grid_export, network.n_periods)

    window_import = [_average(import_price, network.periods, window) for window in windows]
    window_export = [_average(export_price, network.periods, window) for window in windows]

    curves: list[OfferCurve] = network.offer_curves(
        grid_import.total_power_in - grid_export.total_power_in,
        windows=windows,
        low=[min(min_price - price, 0.0) for price in window_import],
        high=[max(max_price - price, 0.0) for price in window_import],
    )
    return [
        GridOffer(
            periods=curve.periods,
            import_price=imported,
            export_price=exported,
            power=curve.power_at(0.0),
            steps=tuple(
                GridOfferStep(import_price=imported + step.price, export_price=exported + step.price, power=step.power)
                for step in curve.steps
            ),
        )
        for curve, imported, exported in zip(curves, window_import, window_export, strict=True)
    ]


__all__ = ["GridOffer", "GridOfferStep", "grid_offers"]
