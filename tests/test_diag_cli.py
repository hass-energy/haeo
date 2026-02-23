"""Tests for diagnostics CLI loader helpers."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest

from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.core.schema.elements import battery
from tools import diag


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

    loaded = cast(
        "battery.BatteryConfigData",
        diag.load_element_data(
            "Battery",
            config,
            diag.DiagnosticsStateProvider([]),
            (0.0, 1800.0, 3600.0),
        ),
    )

    np.testing.assert_allclose(loaded["storage"]["capacity"], np.array([13.5, 13.5, 13.5]))
    assert loaded["storage"]["initial_charge_percentage"] == pytest.approx(0.5)
    assert loaded["common"].get("connection") == {"type": "connection_target", "value": "Inverter"}


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

    loaded = cast(
        "battery.BatteryConfigData",
        diag.load_element_data(
            "Battery",
            config,
            diag.DiagnosticsStateProvider([]),
            (0.0, 1800.0, 3600.0),
        ),
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

    loaded = cast(
        "battery.BatteryConfigData",
        diag.load_element_data(
            "Battery",
            config,
            diag.DiagnosticsStateProvider([]),
            (0.0, 1800.0, 3600.0),
        ),
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

    loaded = cast(
        "battery.BatteryConfigData",
        diag.load_element_data(
            "Battery",
            config,
            diag.DiagnosticsStateProvider([]),
            (0.0, 1800.0, 3600.0),
        ),
    )

    assert "price_target_source" not in loaded["pricing"]


def test_normalize_participant_config_for_diag_migrates_legacy_flat_config() -> None:
    """Legacy flat participant config is migrated to sectioned format."""
    config: dict[str, Any] = {
        "element_type": "battery",
        "name": "Battery",
        "connection": "Inverter",
        "capacity": 13.5,
        "initial_charge_percentage": 50.0,
    }

    normalized = diag.normalize_participant_config_for_diag(config)

    assert "common" in normalized
    assert normalized["common"]["name"] == "Battery"
    assert normalized["storage"]["capacity"] == as_constant_value(13.5)
    assert normalized["storage"]["initial_charge_percentage"] == as_constant_value(50.0)


def test_normalize_participant_config_for_diag_skips_migration_for_sectioned_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Already sectioned config bypasses migration helper."""
    config = _base_battery_config()

    monkeypatch.setattr(
        diag,
        "migrate_element_config",
        lambda _data: pytest.fail("migration should not run for sectioned config"),
    )

    normalized = diag.normalize_participant_config_for_diag(config)

    assert normalized is config


def test_normalize_participant_config_for_diag_migrates_mixed_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mixed config (sections + legacy fields) routes through migration."""
    config = _base_battery_config()
    config["capacity"] = 13.5

    migrated = {
        "element_type": "battery",
        "common": {"name": "Battery"},
    }
    called: list[Any] = []

    def _fake_migrate(data: Any) -> dict[str, Any]:
        called.append(data)
        return migrated

    monkeypatch.setattr(diag, "migrate_element_config", _fake_migrate)

    normalized = diag.normalize_participant_config_for_diag(config)

    assert normalized is migrated
    assert len(called) == 1


def test_get_forecast_by_fields_supports_legacy_grid_price_aliases() -> None:
    """Diagnostics forecast lookup falls back to legacy grid price field names."""
    outputs = {
        "number.grid_import_price": {
            "attributes": {
                "element_name": "Grid",
                "field_name": "import_price",
                "forecast": [{"time": "2026-01-01T00:00:00+00:00", "value": 0.21}],
            }
        },
        "number.grid_export_price": {
            "attributes": {
                "element_name": "Grid",
                "field_name": "export_price",
                "forecast": [{"time": "2026-01-01T00:00:00+00:00", "value": 0.05}],
            }
        },
    }

    buy = diag.get_forecast_by_fields(outputs, "Grid", ("price_source_target", "import_price"))
    sell = diag.get_forecast_by_fields(outputs, "Grid", ("price_target_source", "export_price"))

    assert buy == {"2026-01-01T00:00:00+00:00": 0.21}
    assert sell == {"2026-01-01T00:00:00+00:00": 0.05}


def test_format_comparison_table_marks_missing_rows_as_na() -> None:
    """Missing timestamps are rendered as N/A instead of numeric zeros."""
    diag_rows = [
        diag.RowData("00:00", 1.0, 0.2, 0.1, 1.0, -2.0, 3.0, 4.0, 50.0, 10.0),
        diag.RowData("00:05", 2.0, 0.3, 0.2, 2.0, -3.0, 4.0, 5.0, 55.0, 20.0),
    ]
    rerun_rows = [
        diag.RowData("00:00", 1.0, 0.2, 0.1, 1.0, -2.0, 3.0, 4.0, 50.0, 10.0),
    ]

    table = diag.format_comparison_table(diag_rows, rerun_rows, "UTC")

    assert "Rows compared: 1 overlap / 2 total" in table
    assert "N/A" in table


def test_format_comparison_table_averages_only_overlap_rows() -> None:
    """Summary diffs exclude non-overlapping timestamps."""
    diag_rows = [
        diag.RowData("00:00", 1.0, 0.2, 0.1, 1.0, -2.0, 3.0, 4.0, 50.0, 10.0),
        diag.RowData("00:05", 2.0, 9.9, 9.9, 9.9, 99.0, 99.0, 99.0, 99.0, 999.0),
    ]
    rerun_rows = [
        diag.RowData("00:00", 1.0, 0.2, 0.1, 1.0, -2.0, 3.0, 4.0, 50.0, 10.0),
    ]

    table = diag.format_comparison_table(diag_rows, rerun_rows, "UTC")

    assert "Battery=0.00kW" in table
    assert "Grid=0.00kW" in table
    assert "SoC=0.00%" in table
    assert "Profit=$0.000" in table


def test_infer_interval_starts_from_outputs_prefers_interval_series() -> None:
    """Interval-start inference uses interval outputs, not boundary-only tails."""
    config = {
        "participants": {
            "Grid": {"element_type": "grid"},
            "Battery": {"element_type": "battery"},
        }
    }
    outputs = {
        "sensor.grid_power_active": {
            "attributes": {
                "element_name": "Grid",
                "output_name": "grid_power_active",
                "forecast": [
                    {"time": "2026-01-01T00:00:00+00:00", "value": 1.0},
                    {"time": "2026-01-01T00:05:00+00:00", "value": 1.0},
                ],
            }
        },
        "sensor.battery_soc": {
            "attributes": {
                "element_name": "Battery",
                "output_name": "battery_state_of_charge",
                "forecast": [
                    {"time": "2026-01-01T00:00:00+00:00", "value": 0.5},
                    {"time": "2026-01-01T00:05:00+00:00", "value": 0.6},
                    {"time": "2026-01-01T00:17:00+00:00", "value": 0.7},
                ],
            }
        },
    }

    starts = diag.infer_interval_starts_from_outputs(outputs, config)

    assert starts == [
        diag.parse_datetime_to_timestamp("2026-01-01T00:00:00+00:00"),
        diag.parse_datetime_to_timestamp("2026-01-01T00:05:00+00:00"),
    ]


def test_infer_interval_starts_from_outputs_supports_legacy_price_fields() -> None:
    """Interval-start inference falls back to legacy import/export price forecasts."""
    config = {"participants": {"Grid": {"element_type": "grid"}}}
    outputs = {
        "number.grid_import_price": {
            "attributes": {
                "element_name": "Grid",
                "field_name": "import_price",
                "forecast": [
                    {"time": "2026-01-01T00:00:00+00:00", "value": 0.2},
                    {"time": "2026-01-01T01:00:00+00:00", "value": 0.3},
                ],
            }
        }
    }

    starts = diag.infer_interval_starts_from_outputs(outputs, config)

    assert starts == [
        diag.parse_datetime_to_timestamp("2026-01-01T00:00:00+00:00"),
        diag.parse_datetime_to_timestamp("2026-01-01T01:00:00+00:00"),
    ]
