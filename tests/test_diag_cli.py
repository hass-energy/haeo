"""Tests for diagnostics CLI loader helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

import tools.diag as diag


def _base_battery_config() -> dict[str, Any]:
    """Build a minimal battery config in diagnostics schema format."""
    return {
        "element_type": "battery",
        "common": {
            "connection": {"type": "connection_target", "value": "Inverter"},
        },
        "storage": {},
        "limits": {},
        "power_limits": {},
        "pricing": {},
        "efficiency": {},
        "partitioning": {},
        "undercharge": {},
        "overcharge": {},
    }


def test_load_element_data_unwraps_constant_wrappers() -> None:
    """Constant wrappers convert to loaded scalar/series values."""
    config = _base_battery_config()
    config["storage"] = {
        "capacity": {"type": "constant", "value": 13.5},
        "initial_charge_percentage": {"type": "constant", "value": 50.0},
    }

    loaded = diag.load_element_data(
        "Battery",
        config,
        diag.DiagnosticsStateProvider([]),
        (0.0, 1800.0, 3600.0),
    )

    np.testing.assert_allclose(loaded["storage"]["capacity"], np.array([13.5, 13.5, 13.5]))
    assert loaded["storage"]["initial_charge_percentage"] == pytest.approx(0.5)
    assert loaded["common"]["connection"] == {"type": "connection_target", "value": "Inverter"}


def test_load_element_data_uses_present_value_for_scalar_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entity-backed scalar fields use present value, not fused horizons."""
    config = _base_battery_config()
    config["storage"] = {
        "capacity": {"type": "constant", "value": 13.5},
        "initial_charge_percentage": {"type": "entity", "value": ["sensor.battery_soc"]},
    }

    monkeypatch.setattr(
        diag,
        "load_sensors",
        lambda _provider, entity_ids: {entity_ids[0]: 75.0},
    )
    monkeypatch.setattr(
        diag,
        "combine_sensor_payloads",
        lambda _payloads: (75.0, ((0.0, 74.0),)),
    )
    monkeypatch.setattr(
        diag,
        "fuse_to_boundaries",
        lambda *_args, **_kwargs: pytest.fail("fuse_to_boundaries should not run for scalar fields"),
    )
    monkeypatch.setattr(
        diag,
        "fuse_to_intervals",
        lambda *_args, **_kwargs: pytest.fail("fuse_to_intervals should not run for scalar fields"),
    )

    loaded = diag.load_element_data(
        "Battery",
        config,
        diag.DiagnosticsStateProvider([]),
        (0.0, 1800.0, 3600.0),
    )

    assert loaded["storage"]["initial_charge_percentage"] == pytest.approx(0.75)


def test_load_element_data_unwraps_entity_wrappers_for_time_series(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entity wrappers for time-series fields are loaded into numpy arrays."""
    config = _base_battery_config()
    config["storage"] = {
        "capacity": {"type": "entity", "value": ["sensor.battery_capacity"]},
        "initial_charge_percentage": {"type": "constant", "value": 50.0},
    }

    monkeypatch.setattr(
        diag,
        "load_sensors",
        lambda _provider, entity_ids: {entity_ids[0]: 13.5},
    )
    monkeypatch.setattr(
        diag,
        "combine_sensor_payloads",
        lambda _payloads: (13.5, ((0.0, 13.5),)),
    )
    monkeypatch.setattr(
        diag,
        "fuse_to_boundaries",
        lambda *_args, **_kwargs: [13.5, 13.4, 13.3],
    )

    loaded = diag.load_element_data(
        "Battery",
        config,
        diag.DiagnosticsStateProvider([]),
        (0.0, 1800.0, 3600.0),
    )

    np.testing.assert_allclose(loaded["storage"]["capacity"], np.array([13.5, 13.4, 13.3]))


def test_load_element_data_drops_none_wrappers() -> None:
    """Disabled schema values are removed from loaded config."""
    config = _base_battery_config()
    config["storage"] = {
        "capacity": {"type": "constant", "value": 13.5},
        "initial_charge_percentage": {"type": "constant", "value": 50.0},
    }
    config["pricing"] = {
        "price_target_source": {"type": "none"},
    }

    loaded = diag.load_element_data(
        "Battery",
        config,
        diag.DiagnosticsStateProvider([]),
        (0.0, 1800.0, 3600.0),
    )

    assert "price_target_source" not in loaded["pricing"]
