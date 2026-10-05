"""Tests for battery reserve demand pricing."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.battery import BATTERY_RESERVE_SHORTFALL, Battery


def _build_network(
    *,
    initial_charge: float,
    drain: list[float],
    reserve_level: float | None = None,
    reserve_mask: np.ndarray | None = None,
    reserve_price: np.ndarray | float | None = None,
    import_price: list[float] | None = None,
) -> tuple[Network, Battery]:
    """Build a battery that is force-drained, with optional grid and reserve."""
    n = len(drain)
    network = Network(name="test_network", periods=np.array([1.0] * n))

    battery = network.add(
        {
            "element_type": "battery",
            "name": "batt",
            "capacity": 20.0,
            "initial_charge": initial_charge,
            "reserve_level": reserve_level,
            "reserve_mask": reserve_mask,
            "reserve_price": reserve_price,
        }
    )
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "batt_to_sink",
            "source": "batt",
            "target": "sink",
            "tags": {1},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array(drain), "fixed": True},
            },
        }
    )
    if import_price is not None:
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": False})
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "grid_to_batt",
                "source": "grid",
                "target": "batt",
                "tags": {1},
                "segments": {
                    "pricing": {"segment_type": "pricing", "price": np.array(import_price)},
                },
            }
        )
    return network, battery


def test_no_reserve_battery_is_unchanged() -> None:
    """Without reserve config the battery behaves as before with a zero output."""
    network, battery = _build_network(initial_charge=10.0, drain=[0.0, 8.0])

    network.optimize()

    shortfall = battery.outputs()[BATTERY_RESERVE_SHORTFALL].values
    np.testing.assert_allclose(shortfall, [0.0, 0.0, 0.0])


def test_reserve_shortfall_priced_once_at_masked_boundary() -> None:
    """Dropping below the reserve is priced on the lowest level, once."""
    # Drain 8 kWh in period 2: stored 10 → 10 → 2, reserve 5 checked at the end.
    network, battery = _build_network(
        initial_charge=10.0,
        drain=[0.0, 8.0],
        reserve_level=5.0,
        reserve_mask=np.array([0.0, 0.0, 1.0]),
        reserve_price=2.0,
    )

    cost = network.optimize()

    shortfall = battery.outputs()[BATTERY_RESERVE_SHORTFALL].values
    np.testing.assert_allclose(shortfall, [0.0, 0.0, 3.0])
    assert cost == pytest.approx(3.0 * 2.0)


def test_reserve_avoided_by_precharging_when_cheaper() -> None:
    """The optimizer tops up ahead of the drain when energy beats the penalty."""
    network, battery = _build_network(
        initial_charge=10.0,
        drain=[0.0, 8.0],
        reserve_level=5.0,
        reserve_mask=np.array([0.0, 0.0, 1.0]),
        reserve_price=2.0,
        import_price=[0.1, 0.1],
    )

    cost = network.optimize()

    shortfall = battery.outputs()[BATTERY_RESERVE_SHORTFALL].values
    np.testing.assert_allclose(shortfall, [0.0, 0.0, 0.0])
    # 3 kWh topped up at 0.1 beats a 3 kWh shortfall at 2.0.
    assert cost == pytest.approx(3.0 * 0.1)


def test_expensive_energy_leaves_the_shortfall() -> None:
    """When topping up costs more than the penalty, the shortfall stays."""
    network, battery = _build_network(
        initial_charge=10.0,
        drain=[0.0, 8.0],
        reserve_level=5.0,
        reserve_mask=np.array([0.0, 0.0, 1.0]),
        reserve_price=0.2,
        import_price=[0.5, 0.5],
    )

    cost = network.optimize()

    shortfall = battery.outputs()[BATTERY_RESERVE_SHORTFALL].values
    np.testing.assert_allclose(shortfall, [0.0, 0.0, 3.0])
    assert cost == pytest.approx(3.0 * 0.2)


def test_unmasked_boundaries_are_not_priced() -> None:
    """Being below reserve mid-window costs nothing until a masked boundary."""
    # Drain happens in period 1, recovery impossible, but only the final
    # boundary is masked — one charge despite two boundaries below reserve.
    network, battery = _build_network(
        initial_charge=6.0,
        drain=[4.0, 0.0],
        reserve_level=5.0,
        reserve_mask=np.array([0.0, 0.0, 1.0]),
        reserve_price=2.0,
    )

    cost = network.optimize()

    shortfall = battery.outputs()[BATTERY_RESERVE_SHORTFALL].values
    np.testing.assert_allclose(shortfall, [0.0, 0.0, 3.0])
    assert cost == pytest.approx(3.0 * 2.0)


def test_negative_reserve_price_is_rejected() -> None:
    """A negative reserve price would book shortfall that never happens, so it is rejected."""
    network, _battery = _build_network(
        initial_charge=10.0,
        drain=[0.0, 8.0],
        reserve_level=5.0,
        reserve_mask=np.array([0.0, 0.0, 1.0]),
        reserve_price=np.array([1.0, 1.0, -1.0]),
    )

    with pytest.raises(ValueError, match="reserve_price must be non-negative"):
        network.optimize()


def test_negative_reserve_price_update_is_rejected() -> None:
    """Updating the reserve price to a negative value is rejected on the next optimization."""
    network, battery = _build_network(
        initial_charge=10.0,
        drain=[0.0, 8.0],
        reserve_level=5.0,
        reserve_mask=np.array([0.0, 0.0, 1.0]),
        reserve_price=1.0,
    )
    network.optimize()

    battery["reserve_price"] = np.array([1.0, -1.0, 1.0])

    with pytest.raises(ValueError, match="reserve_price must be non-negative"):
        network.optimize()
