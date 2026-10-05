"""Tests for the diagnostics CLI analysis modules."""

import json
from pathlib import Path
from typing import Any

import pytest

from tools.diag.analysis import ANALYSES, describe_analyses, run_analysis
from tools.diag.analysis.series import column_labels, forecast_series

SCENARIO = Path(__file__).parent / "scenarios" / "scenario3"


@pytest.fixture
def outputs() -> dict[str, Any]:
    """Return a real diagnostics outputs mapping."""
    return json.loads((SCENARIO / "outputs.json").read_text())


@pytest.fixture
def config() -> dict[str, Any]:
    """Return the matching scenario config."""
    return json.loads((SCENARIO / "config.json").read_text())


def entity(points: list[tuple[str, float]]) -> dict[str, Any]:
    """Build a minimal output entity with a forecast series."""
    return {
        "state": str(points[0][1]) if points else "unknown",
        "attributes": {"forecast": [{"time": f"2025-11-06T{t}:00+00:00", "value": v} for t, v in points]},
    }


def test_every_registered_analysis_runs(outputs: dict[str, Any], config: dict[str, Any]) -> None:
    """Each registered analysis produces output for a real export."""
    for name in ANALYSES:
        result = run_analysis(name, outputs, config)
        assert result.strip(), f"{name} produced no output"


def test_describe_lists_every_analysis() -> None:
    """The listing names every registered analysis."""
    listing = describe_analyses()
    for name in ANALYSES:
        assert name in listing


def test_unknown_analysis_names_the_alternatives(outputs: dict[str, Any], config: dict[str, Any]) -> None:
    """An unknown analysis reports what is available rather than failing opaquely."""
    with pytest.raises(KeyError, match="unknown analysis 'nope'"):
        run_analysis("nope", outputs, config)


def test_binding_separates_capacity_from_forecast_limits(outputs: dict[str, Any], config: dict[str, Any]) -> None:
    """Forecast limits bind by construction and must not be reported as forced."""
    result = run_analysis("binding", outputs, config)

    assert "CAPACITY LIMITS REACHED" in result
    assert "FORECAST LIMITS" in result
    # solar_forecast_limit binds constantly; it belongs under forecast, not capacity.
    forecast_section = result.split("FORECAST LIMITS")[1]
    assert "solar_forecast_limit" in forecast_section


def test_binding_reports_no_capacity_limits_when_all_slack(config: dict[str, Any]) -> None:
    """With every dual at zero the analysis says the plan was economic, not forced."""
    outputs = {"sensor.grid_max_export_power_shadow_price": entity([("09:00", 0.0), ("09:05", 0.0)])}

    result = run_analysis("binding", outputs, config)

    assert "CAPACITY LIMITS REACHED — none" in result
    assert "SLACK THROUGHOUT" in result


def test_binding_tolerance_argument_filters_noise(config: dict[str, Any]) -> None:
    """A tolerance argument suppresses duals below the given magnitude."""
    outputs = {"sensor.grid_max_export_power_shadow_price": entity([("09:00", 0.001)])}

    assert "CAPACITY LIMITS REACHED — none" not in run_analysis("binding", outputs, config)
    assert "CAPACITY LIMITS REACHED — none" in run_analysis("binding:0.01", outputs, config)


def test_binding_rejects_a_non_numeric_tolerance(config: dict[str, Any]) -> None:
    """A bad tolerance is reported rather than raising."""
    assert "tolerance must be a number" in run_analysis("binding:abc", {"x_shadow_price": entity([])}, config)


def test_binding_rejects_a_negative_tolerance(config: dict[str, Any]) -> None:
    """A negative tolerance would report every slack constraint as forced."""
    outputs = {"sensor.grid_max_export_power_shadow_price": entity([("09:00", 0.0)])}

    result = run_analysis("binding:-1", outputs, config)

    assert "must not be negative" in result
    assert "CAPACITY LIMITS REACHED — the optimizer was forced here" not in result


def test_series_filters_by_regex(outputs: dict[str, Any], config: dict[str, Any]) -> None:
    """The regex argument selects which entities appear as columns."""
    result = run_analysis("series:battery_state_of_charge", outputs, config)

    assert "sensor.battery_state_of_charge" in result
    assert "sensor.grid_import_power" not in result


def test_series_reports_when_nothing_matches(outputs: dict[str, Any], config: dict[str, Any]) -> None:
    """A regex matching nothing explains itself instead of printing an empty table."""
    assert "no entity ids match" in run_analysis("series:zzzznope", outputs, config)


def test_series_reports_an_invalid_regex(outputs: dict[str, Any], config: dict[str, Any]) -> None:
    """A malformed regex produces a readable message rather than a traceback."""
    result = run_analysis("series:[", outputs, config)

    assert "not a valid regex" in result
    assert "unterminated character set" in result


def test_series_reports_entities_without_a_forecast(config: dict[str, Any]) -> None:
    """Entities carrying only a state are called out rather than silently dropped."""
    outputs = {"sensor.optimizer_status": {"state": "success", "attributes": {}}}

    assert "no forecast series" in run_analysis("series", outputs, config)


def test_forecast_series_ignores_booleans() -> None:
    """Boolean attributes are not numeric series and must not become table values."""
    assert forecast_series(entity([("09:00", 1.5)])) == {"09:00": 1.5}
    assert forecast_series({"attributes": {"forecast": [{"time": "2025-11-06T09:00:00+00:00", "value": True}]}}) == {}


@pytest.mark.parametrize(
    ("entity_ids", "expected"),
    [
        pytest.param(["sensor.battery_state_of_charge"], ["battery_state_of_charge"], id="single-keeps-full-name"),
        pytest.param(
            ["sensor.grid_max_import_power_shadow_price", "sensor.grid_max_export_power_shadow_price"],
            ["import", "export"],
            id="strips-shared-head-and-tail",
        ),
    ],
)
def test_column_labels(entity_ids: list[str], expected: list[str]) -> None:
    """Labels drop the segments every column shares so they stay distinguishable."""
    assert list(column_labels(entity_ids).values()) == expected


def test_column_labels_stay_unique_when_truncation_would_collide() -> None:
    """Columns that cannot be told apart short are numbered rather than duplicated."""
    labels = column_labels(
        ["sensor.battery_energy_in_flow_shadow_price", "sensor.battery_energy_out_flow_shadow_price"]
    )

    assert len(set(labels.values())) == 2
