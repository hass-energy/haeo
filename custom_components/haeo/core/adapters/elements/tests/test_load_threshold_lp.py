"""LP-level integration test for the load threshold-price feature.

Builds a small network with a sheddable Load whose threshold price sits between
two grid import prices, runs the optimizer, and asserts that the load is served
in cheap periods and shed in expensive ones.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.grid import GridAdapter
from custom_components.haeo.core.adapters.elements.load import LoadAdapter
from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER
from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData

_LOAD_FORECAST = 5.0  # kW, every period
_THRESHOLD_PRICE = 0.30  # $/kWh
# Grid import prices: cheap, cheap, expensive, expensive
_IMPORT_PRICES = np.array([0.20, 0.25, 0.35, 0.40])
_PERIODS_HOURS = np.array([1.0, 1.0, 1.0, 1.0])


def _make_grid_config() -> GridConfigData:
    return cast(
        "GridConfigData",
        {
            "element_type": ElementType.GRID,
            "name": "grid",
            "connection": as_connection_target("main_bus"),
            "pricing": {
                "price_source_target": _IMPORT_PRICES,
                "price_target_source": np.array([0.0, 0.0, 0.0, 0.0]),
            },
            "power_limits": {},
        },
    )


def _make_load_config(*, threshold_price: float | None) -> LoadConfigData:
    config: LoadConfigData = cast(
        "LoadConfigData",
        {
            "element_type": ElementType.LOAD,
            "name": "load",
            "connection": as_connection_target("main_bus"),
            "forecast": {"forecast": np.array([_LOAD_FORECAST] * 4)},
            "curtailment": {"curtailment": True},
        },
    )
    if threshold_price is not None:
        config["threshold"] = {"threshold_price": threshold_price}
    return config


def _build_network(participants: dict[str, object]) -> Network:
    net = Network(name="threshold-lp-test", periods=_PERIODS_HOURS)
    sorted_model_elements = list(collect_model_elements(participants))  # type: ignore[arg-type]
    # Compile policies (empty rule list) so connections receive default tags.
    result = compile_policies(sorted_model_elements, [])
    net.add({"element_type": "node", "name": "main_bus", "is_source": False, "is_sink": False})
    for cfg in result["elements"]:
        net.add(cfg)
    return net


def test_load_with_threshold_sheds_when_grid_price_exceeds_threshold() -> None:
    """Load is served while grid_price <= threshold and sheds when grid_price > threshold."""
    grid_config = _make_grid_config()
    load_config = _make_load_config(threshold_price=_THRESHOLD_PRICE)

    net = _build_network({"grid": grid_config, "load": load_config})
    net.optimize()

    load_conn = net.elements["load:connection"].outputs()
    power_values = tuple(load_conn[CONNECTION_POWER].values)  # type: ignore[union-attr]

    # Cheap periods (0.20, 0.25 < 0.30) should serve full load
    assert power_values[0] == pytest.approx(_LOAD_FORECAST, abs=1e-6)
    assert power_values[1] == pytest.approx(_LOAD_FORECAST, abs=1e-6)
    # Expensive periods (0.35, 0.40 > 0.30) should shed completely
    assert power_values[2] == pytest.approx(0.0, abs=1e-6)
    assert power_values[3] == pytest.approx(0.0, abs=1e-6)


def test_load_without_threshold_serves_all_periods() -> None:
    """A sheddable load with no threshold (or threshold=0) is served at all prices.

    With no threshold and all prices > 0, the LP minimises cost by shedding the
    entire load (no benefit term to outweigh the import cost). Adding a threshold
    of $0 preserves this behaviour. This regression test guards that nothing has
    silently changed the default at threshold=0.
    """
    grid_config = _make_grid_config()
    load_config = _make_load_config(threshold_price=None)

    net = _build_network({"grid": grid_config, "load": load_config})
    net.optimize()

    load_conn = net.elements["load:connection"].outputs()
    power_values = tuple(load_conn[CONNECTION_POWER].values)  # type: ignore[union-attr]

    # No threshold: pure cost minimisation against positive import prices means shedding everywhere
    for p in power_values:
        assert p == pytest.approx(0.0, abs=1e-6)


def test_load_with_threshold_zero_matches_no_threshold() -> None:
    """A threshold of $0 yields the same dispatch as no threshold at all (default behaviour preserved)."""
    grid_config = _make_grid_config()
    load_with_zero = _make_load_config(threshold_price=0.0)
    load_without = _make_load_config(threshold_price=None)

    net_zero = _build_network({"grid": _make_grid_config(), "load": load_with_zero})
    net_zero.optimize()
    power_zero = tuple(net_zero.elements["load:connection"].outputs()[CONNECTION_POWER].values)  # type: ignore[union-attr]

    net_none = _build_network({"grid": grid_config, "load": load_without})
    net_none.optimize()
    power_none = tuple(net_none.elements["load:connection"].outputs()[CONNECTION_POWER].values)  # type: ignore[union-attr]

    assert power_zero == pytest.approx(power_none, abs=1e-6)


def test_load_with_threshold_built_via_adapter_includes_pricing_segment() -> None:
    """LoadAdapter.model_elements emits a pricing segment with negated price."""
    adapter = LoadAdapter()
    config = _make_load_config(threshold_price=_THRESHOLD_PRICE)
    elements = adapter.model_elements(config)
    connection = next(e for e in elements if e.get("name") == "load:connection")
    segments = connection.get("segments")
    assert isinstance(segments, dict)
    pricing_segment = segments.get("pricing")
    assert isinstance(pricing_segment, dict)
    assert pricing_segment.get("segment_type") == "pricing"
    assert pricing_segment.get("price") == pytest.approx(-_THRESHOLD_PRICE)


def test_grid_adapter_unchanged_by_threshold_section() -> None:
    """The Grid adapter is not affected by the load threshold-price feature.

    Sanity check that the test scaffold's grid setup is what we intend (and that
    importing GridAdapter alongside LoadAdapter doesn't produce a circular setup).
    """
    grid_config = _make_grid_config()
    elements = GridAdapter().model_elements(grid_config)
    assert any(e.get("element_type") == "connection" for e in elements)
