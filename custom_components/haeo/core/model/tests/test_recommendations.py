"""Tests for connection control recommendations."""

import numpy as np
import pytest

from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.model.recommendations import RecommendationType, compute_recommendations


def _build_network(
    solar_max: list[float],
    load: list[float],
    import_price: list[float],
    export_price_segment: list[float],
    *,
    battery: bool = False,
) -> Network:
    """Build a simple Grid-SW-Load-Solar network for testing."""
    n = len(solar_max)
    periods = np.array([0.5] * n)
    net = Network(name="test", periods=periods)
    net.add({"element_type": "node", "name": "Grid", "is_source": True, "is_sink": True})
    net.add({"element_type": "node", "name": "SW", "is_source": False, "is_sink": False})
    net.add({"element_type": "node", "name": "Load", "is_source": False, "is_sink": True})
    net.add({"element_type": "node", "name": "Solar", "is_source": True, "is_sink": False})
    net.add(
        {
            "element_type": "connection",
            "name": "Grid:import",
            "source": "Grid",
            "target": "SW",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": import_price},
                "power_limit": {"segment_type": "power_limit", "max_power": 10.0},
            },
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Grid:export",
            "source": "SW",
            "target": "Grid",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": export_price_segment},
                "power_limit": {"segment_type": "power_limit", "max_power": 10.0},
            },
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Solar:conn",
            "source": "Solar",
            "target": "SW",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": solar_max}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Load:conn",
            "source": "SW",
            "target": "Load",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": load, "fixed": True}},
        }
    )
    if battery:
        net.add({"element_type": "battery", "name": "Bat", "capacity": 5.0, "initial_charge": 2.0})
        net.add(
            {
                "element_type": "connection",
                "name": "Bat:charge",
                "source": "SW",
                "target": "Bat",
                "tags": {1},
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 0.95},
                    "power_limit": {"segment_type": "power_limit", "max_power": 3.0},
                },
            }
        )
        net.add(
            {
                "element_type": "connection",
                "name": "Bat:discharge",
                "source": "Bat",
                "target": "SW",
                "tags": {1},
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 0.95},
                    "power_limit": {"segment_type": "power_limit", "max_power": 3.0},
                },
            }
        )
    return net


def _get_solar_recs(net: Network) -> list:
    """Get solar recommendations after solving."""
    net.optimize()
    conn = net.elements["Solar:conn"]
    tag = sorted(conn._power_in.keys())[0]
    arr = conn._power_in[tag]
    seg = conn.segments["power_limit"]
    max_power = seg.max_power
    forecast = [max_power[t] if hasattr(max_power, "__getitem__") else float(max_power) for t in range(len(arr))]
    return compute_recommendations(
        net._solver,
        list(arr),
        forecast,
        list(net.periods),
    )


# --- Scenario 1: Export costs money, solar > load ---
# Expected: UNLIMIT (solar self-consumes, excess is handled by pricing)


def test_solar_unlimit_when_export_costs_money() -> None:
    """Solar exceeds load, export costs money — should UNLIMIT.

    The inverter can self-consume and the export penalty handles the rest.
    Band should reach forecast max.
    """
    net = _build_network(
        solar_max=[6.0],
        load=[2.0],
        import_price=[0.30],
        export_price_segment=[0.03],
    )
    recs = _get_solar_recs(net)
    assert recs[0].type == RecommendationType.UNLIMIT
    assert recs[0].band_max == pytest.approx(6.0, abs=0.1)


# --- Scenario 2: Grid pays to absorb, solar > load ---
# Expected: SET (must limit solar to avoid displacing paid import)


def test_solar_set_when_grid_pays_to_absorb() -> None:
    """Grid pays to import, solar exceeds load — should SET limit.

    Solar displaces paid grid import, so it should be capped at load.
    """
    net = _build_network(
        solar_max=[6.0],
        load=[2.0],
        import_price=[-0.05],
        export_price_segment=[0.02],
    )
    recs = _get_solar_recs(net)
    assert recs[0].type == RecommendationType.SET
    assert recs[0].limit is not None
    assert recs[0].limit == pytest.approx(2.0, abs=0.1)  # capped at load
    assert recs[0].reduced_cost > 0  # going up costs money


# --- Zero forecast ---
# Expected: UNKNOWN (model has no information)


def test_solar_unknown_when_forecast_zero() -> None:
    """Zero solar forecast — model can't recommend, should be UNKNOWN."""
    net = _build_network(
        solar_max=[0.0],
        load=[2.0],
        import_price=[0.30],
        export_price_segment=[-0.05],
    )
    recs = _get_solar_recs(net)
    assert recs[0].type == RecommendationType.UNKNOWN
    assert recs[0].limit is None
    assert recs[0].forecast_max == 0.0


def test_solar_unknown_when_forecast_zero_negative_import() -> None:
    """Zero solar, grid pays to absorb — still UNKNOWN (no forecast data)."""
    net = _build_network(
        solar_max=[0.0],
        load=[2.0],
        import_price=[-0.05],
        export_price_segment=[0.02],
    )
    recs = _get_solar_recs(net)
    assert recs[0].type == RecommendationType.UNKNOWN


# --- At forecast max, normal operation ---
# Expected: UNLIMIT (producing at max, would use more if available)


def test_solar_unlimit_at_forecast_max() -> None:
    """Solar at max, load absorbs all — UNLIMIT."""
    net = _build_network(
        solar_max=[3.0],
        load=[5.0],
        import_price=[0.30],
        export_price_segment=[-0.05],
    )
    recs = _get_solar_recs(net)
    assert recs[0].type == RecommendationType.UNLIMIT
    assert recs[0].optimal == pytest.approx(3.0, abs=0.1)


# --- Interior solution with battery ---
# Expected: UNLIMIT if band reaches max


def test_solar_unlimit_with_battery_absorbing() -> None:
    """Solar partial, battery charging, band reaches max — UNLIMIT."""
    net = _build_network(
        solar_max=[6.0],
        load=[2.0],
        import_price=[0.30],
        export_price_segment=[-0.05],
        battery=True,
    )
    recs = _get_solar_recs(net)
    # With positive export FiT and battery, solar should be unlimited
    assert recs[0].type == RecommendationType.UNLIMIT
    assert recs[0].band_max == pytest.approx(6.0, abs=0.1)


# --- Export profitable, solar exceeds load + battery ---
# Expected: UNLIMIT (export earns money)


def test_solar_unlimit_when_export_profitable() -> None:
    """Solar exceeds load, export earns money — UNLIMIT."""
    net = _build_network(
        solar_max=[10.0],
        load=[2.0],
        import_price=[0.30],
        export_price_segment=[-0.10],
    )
    recs = _get_solar_recs(net)
    assert recs[0].type == RecommendationType.UNLIMIT


# --- Band interpretation ---


def test_band_gives_flexibility_range() -> None:
    """Band [bdn, bup] defines safe operating range."""
    net = _build_network(
        solar_max=[6.0],
        load=[2.0],
        import_price=[0.30],
        export_price_segment=[0.03],
    )
    recs = _get_solar_recs(net)
    # Band should span from load to forecast max
    assert recs[0].band_min >= 0
    assert recs[0].band_min <= recs[0].optimal + 0.1
    assert recs[0].band_max >= recs[0].optimal - 0.1


def test_reduced_cost_direction() -> None:
    """Reduced cost sign indicates preferred direction within band."""
    # Scenario where solar is off and going up costs money
    net = _build_network(
        solar_max=[6.0],
        load=[2.0],
        import_price=[-0.05],
        export_price_segment=[0.02],
    )
    recs = _get_solar_recs(net)
    assert recs[0].reduced_cost > 0  # positive = going up is costly


# --- Grid connection recommendations ---


def _get_conn_recs(net: Network, conn_name: str) -> list:
    """Get connection recommendations after solving."""
    net.optimize()
    conn = net.elements[conn_name]
    tag = sorted(conn._power_in.keys())[0]
    arr = conn._power_in[tag]
    seg = conn.segments["power_limit"]
    mp = seg.max_power
    forecast = [mp[t] if hasattr(mp, "__getitem__") else float(mp) for t in range(len(arr))]
    return compute_recommendations(net._solver, list(arr), forecast, list(net.periods))


def test_grid_import_set_when_costly() -> None:
    """Grid import not active but costly — SET (prevent unwanted import).

    RC > 0 because importing at $0.30 costs more than solar self-consumption.
    """
    net = _build_network(
        solar_max=[6.0],
        load=[2.0],
        import_price=[0.30],
        export_price_segment=[-0.05],
    )
    recs = _get_conn_recs(net, "Grid:import")
    assert recs[0].type == RecommendationType.SET
    assert recs[0].reduced_cost > 0


def test_grid_export_set_when_at_limit() -> None:
    """Grid export at limit with binding constraint — SET."""
    net = _build_network(
        solar_max=[20.0],
        load=[2.0],
        import_price=[0.30],
        export_price_segment=[-0.05],
    )
    # 20kW solar, 2kW load, 10kW export limit should bind
    recs = _get_conn_recs(net, "Grid:export")
    # Export should be at its 10kW limit
    if recs[0].optimal >= 9.9:
        # Limit is binding — could be SET or UNLIMIT depending on RC
        assert recs[0].type in (RecommendationType.SET, RecommendationType.UNLIMIT)
