"""Tests for grid offer curves."""

import numpy as np
import pytest

from custom_components.haeo.core.adapters.network_builder import build_network
from custom_components.haeo.core.adapters.offer import GridOfferStep, grid_offers
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE

GRID = "Grid"


def _participants(
    import_price: tuple[float, float] = (0.20, 0.20), export_price: tuple[float, float] = (0.10, 0.10)
) -> dict[str, ElementConfigData]:
    """Return a home with a 2.5 kW load, a 5 kW generator that costs 0.15 $/kWh to run, and a grid.

    The grid charges 0.20 $/kWh for import and pays 0.10 $/kWh for export unless told otherwise.
    """
    grid: GridConfigData = {
        "element_type": ElementType.GRID,
        "name": GRID,
        "connection": as_connection_target("Home"),
        "pricing": {"price_source_target": np.array(import_price), "price_target_source": np.array(export_price)},
        "power_limits": {"max_power_source_target": np.array([10.0]), "max_power_target_source": np.array([10.0])},
    }
    load: LoadConfigData = {
        "element_type": ElementType.LOAD,
        "name": "Load",
        "connection": as_connection_target("Home"),
        "forecast": {"forecast": np.array([2.5, 2.5])},
        "curtailment": {},
    }
    return {
        "Home": {
            "element_type": ElementType.NODE,
            "name": "Home",
            "role": {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
        },
        "Generator": {
            "element_type": ElementType.NODE,
            "name": "Generator",
            "role": {CONF_IS_SOURCE: True, CONF_IS_SINK: False},
        },
        "Generator line": {
            "element_type": ElementType.CONNECTION,
            "name": "Generator line",
            "endpoints": {"source": as_connection_target("Generator"), "target": as_connection_target("Home")},
            "power_limits": {"max_power_source_target": 5.0},
            "pricing": {"price_source_target": 0.15},
            "efficiency": {},
        },
        GRID: grid,
        "Load": load,
    }


def _flat(steps: tuple[GridOfferStep, ...]) -> list[float]:
    """Return each step's import price, export price and power in turn."""
    return [value for step in steps for value in (step.import_price, step.export_price, step.power)]


def test_grid_offer_moves_import_and_export_prices_together() -> None:
    """Each step names the import and export prices it starts at, both shifted by the same amount.

    Below an import price of 0.15 the load imports, above it the generator runs
    for the load, and once export pays more than 0.15 it runs flat out to export.
    """
    network = build_network("offer", _participants(), [1800, 1800])
    network.optimize()

    (offer,) = grid_offers(network, GRID, windows=[[1]], min_price=-1.0, max_price=1.0)

    assert offer.periods == (1,)
    assert (offer.import_price, offer.export_price, offer.power) == pytest.approx((0.20, 0.10, 0.0))
    assert _flat(offer.steps) == pytest.approx([-1.0, -1.1, 2.5, 0.15, 0.05, 0.0, 0.25, 0.15, -2.5])


def test_grid_offer_range_takes_in_the_forecast_price() -> None:
    """A price range that misses the forecast is widened to reach it."""
    network = build_network("offer", _participants(), [1800, 1800])
    network.optimize()

    (offer,) = grid_offers(network, GRID, windows=[[0, 1]], min_price=0.5, max_price=1.0)

    assert [step.import_price for step in offer.steps] == pytest.approx([0.20, 0.25])


def test_grid_offer_window_prices_are_averaged_over_time() -> None:
    """A window's forecast prices are its periods' prices weighted by how long each lasts."""
    network = build_network("offer", _participants((0.20, 0.26), (0.10, 0.04)), [1800, 3600])
    network.optimize()

    (offer,) = grid_offers(network, GRID, windows=[[0, 1]], min_price=-1.0, max_price=1.0)

    assert (offer.import_price, offer.export_price) == pytest.approx((0.24, 0.06))
    assert offer.steps[0].import_price == pytest.approx(-1.0)
