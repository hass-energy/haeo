"""Tests for shadow_price_utils module."""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.core.adapters.shadow_price_utils import shadow_price_per_energy, shadow_price_per_power
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.output_data import OutputData


def _shadow(values: tuple[float, ...], unit: str = "$/kW", **kwargs: Any) -> OutputData:
    return OutputData(type=OutputType.SHADOW_PRICE, unit=unit, values=values, **kwargs)


def test_per_energy_uniform_one_hour_periods_is_identity_in_value() -> None:
    """1-hour periods give a value-identity conversion (only the unit changes)."""
    shadow = _shadow((0.10, 0.20, 0.30))
    periods = np.array([1.0, 1.0, 1.0])
    result = shadow_price_per_energy(shadow, periods)
    assert result is not None
    assert result.unit == "$/kWh"
    assert result.values == (0.10, 0.20, 0.30)


def test_per_energy_non_uniform_periods() -> None:
    """Variable-width periods produce per-element scaled values."""
    # 5-min, 5-min, 30-min, 1-hour periods
    shadow = _shadow((0.10, 0.20, 0.30, 0.40))
    periods = np.array([1.0 / 12.0, 1.0 / 12.0, 0.5, 1.0])
    result = shadow_price_per_energy(shadow, periods)
    assert result is not None
    assert result.unit == "$/kWh"
    assert result.values[0] == pytest.approx(0.10 * 12.0)
    assert result.values[1] == pytest.approx(0.20 * 12.0)
    assert result.values[2] == pytest.approx(0.60)
    assert result.values[3] == pytest.approx(0.40)


def test_per_energy_zero_period_yields_zero_no_division_error() -> None:
    """A zero-length period maps to 0.0 instead of raising ZeroDivisionError."""
    shadow = _shadow((0.10, 0.20))
    periods = np.array([0.0, 0.5])
    result = shadow_price_per_energy(shadow, periods)
    assert result is not None
    assert result.values[0] == 0.0
    assert result.values[1] == pytest.approx(0.40)


def test_per_energy_preserves_attributes() -> None:
    """Direction, advanced, state_last and type carry through the conversion."""
    shadow = _shadow(
        (0.10,),
        direction=None,
        advanced=True,
        state_last=True,
    )
    periods = np.array([0.5])
    result = shadow_price_per_energy(shadow, periods)
    assert result is not None
    assert result.advanced is True
    assert result.state_last is True
    assert result.direction is None
    assert result.type == OutputType.SHADOW_PRICE


def test_round_trip_per_energy_then_per_power() -> None:
    """per_energy followed by per_power recovers the original $/kW values."""
    shadow = _shadow((0.10, 0.25, 0.50))
    periods = np.array([1.0 / 12.0, 0.5, 1.0])
    energy = shadow_price_per_energy(shadow, periods)
    assert energy is not None
    back = shadow_price_per_power(energy, periods)
    assert back is not None
    assert back.unit == "$/kW"
    for original, recovered in zip(shadow.values, back.values, strict=True):
        assert recovered == pytest.approx(original)


def test_per_energy_tagged_shadow_is_chunked_per_period() -> None:
    """Tagged shadows (n_tags * n_periods values) divide each block by the period vector."""
    # 2 tags, 3 periods: tag-A=[0.1, 0.2, 0.3], tag-B=[0.4, 0.5, 0.6]
    shadow = _shadow((0.1, 0.2, 0.3, 0.4, 0.5, 0.6))
    periods = np.array([0.5, 1.0, 2.0])
    result = shadow_price_per_energy(shadow, periods)
    assert result is not None
    assert result.unit == "$/kWh"
    assert result.values[0] == pytest.approx(0.2)
    assert result.values[1] == pytest.approx(0.2)
    assert result.values[2] == pytest.approx(0.15)
    assert result.values[3] == pytest.approx(0.8)
    assert result.values[4] == pytest.approx(0.5)
    assert result.values[5] == pytest.approx(0.3)


def test_per_energy_misaligned_shape_returns_none() -> None:
    """If the shadow has a length that is not a multiple of n_periods, return None."""
    shadow = _shadow((0.1, 0.2, 0.3, 0.4, 0.5))
    periods = np.array([1.0, 1.0, 1.0])
    assert shadow_price_per_energy(shadow, periods) is None


def test_per_energy_empty_periods_returns_none() -> None:
    """An empty periods array cannot align to any shadow shape."""
    shadow = _shadow((0.1,))
    periods = np.array([])
    assert shadow_price_per_energy(shadow, periods) is None


def test_per_energy_wrong_unit_raises() -> None:
    """Calling per_energy on something that is already $/kWh is a programmer error."""
    shadow = _shadow((0.10,), unit="$/kWh")
    with pytest.raises(ValueError, match=r"\$/kW"):
        shadow_price_per_energy(shadow, np.array([1.0]))


def test_per_power_wrong_unit_raises() -> None:
    """Calling per_power on something that is already $/kW is a programmer error."""
    shadow = _shadow((0.10,), unit="$/kW")
    with pytest.raises(ValueError, match=r"\$/kWh"):
        shadow_price_per_power(shadow, np.array([1.0]))


def test_per_power_basic_conversion() -> None:
    """A $/kWh shadow is multiplied by period length to recover $/kW."""
    shadow = _shadow((0.10, 0.20), unit="$/kWh")
    periods = np.array([0.5, 2.0])
    result = shadow_price_per_power(shadow, periods)
    assert result is not None
    assert result.unit == "$/kW"
    assert result.values[0] == pytest.approx(0.05)
    assert result.values[1] == pytest.approx(0.40)
