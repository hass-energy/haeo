"""Tests for the core config loader."""

from collections.abc import Mapping, Sequence
from typing import Any, cast

import numpy as np
import pytest

from conftest import FakeStateMachine
from custom_components.haeo.core.data.loader import config_loader as cl
from custom_components.haeo.core.data.loader.config_loader import load_element_config, load_element_configs
from custom_components.haeo.core.schema.elements import ElementConfigSchema

FORECAST_TIMES = (0.0, 3600.0, 7200.0, 10800.0)

_DEFAULT_IMPORT_PRICE: Any = {"type": "constant", "value": 0.30}
_DEFAULT_EXPORT_PRICE: Any = {"type": "constant", "value": 0.05}
_DEFAULT_CAPACITY: Any = {"type": "constant", "value": 10.0}
_DEFAULT_INITIAL_SOC: Any = {"type": "constant", "value": 50.0}


def _grid_config(
    *,
    import_price: Any = None,
    export_price: Any = None,
) -> dict[str, Any]:
    return {
        "element_type": "grid",
        "name": "Grid",
        "common": {"connection": "node_a"},
        "pricing": {
            "price_source_target": import_price if import_price is not None else _DEFAULT_IMPORT_PRICE,
            "price_target_source": export_price if export_price is not None else _DEFAULT_EXPORT_PRICE,
        },
        "power_limits": {
            "max_power_source_target": {"type": "constant", "value": 10.0},
            "max_power_target_source": {"type": "constant", "value": 10.0},
        },
    }


def _battery_config(
    *,
    capacity: Any = None,
    initial_soc: Any = None,
) -> dict[str, Any]:
    return {
        "element_type": "battery",
        "name": "Battery",
        "common": {"connection": "node_a"},
        "storage": {
            "capacity": capacity if capacity is not None else _DEFAULT_CAPACITY,
            "initial_charge_percentage": initial_soc if initial_soc is not None else _DEFAULT_INITIAL_SOC,
        },
    }


def _as_schema(config: dict[str, Any]) -> ElementConfigSchema:
    """Cast a test config dict to ElementConfigSchema at the type boundary."""
    return cast("ElementConfigSchema", config)


def _load_grid(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load a grid config and return as plain dict for easy assertion."""
    result = load_element_config("Grid", _as_schema(config or _grid_config()), FakeStateMachine({}), FORECAST_TIMES)
    return cast("dict[str, Any]", result)


def _load_battery(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load a battery config and return as plain dict for easy assertion."""
    result = load_element_config(
        "Battery", _as_schema(config or _battery_config()), FakeStateMachine({}), FORECAST_TIMES
    )
    return cast("dict[str, Any]", result)


class TestLoadElementConfig:
    """Tests for load_element_config."""

    def test_constant_values_resolve_to_time_series(self) -> None:
        """Constant pricing values expand to arrays matching forecast intervals."""
        result = _load_grid()

        pricing = result["pricing"]
        assert isinstance(pricing["price_source_target"], np.ndarray)
        assert len(pricing["price_source_target"]) == 3
        np.testing.assert_array_equal(pricing["price_source_target"], [0.30, 0.30, 0.30])

        assert isinstance(pricing["price_target_source"], np.ndarray)
        np.testing.assert_array_equal(pricing["price_target_source"], [0.05, 0.05, 0.05])

    def test_constant_scalar_stays_scalar(self) -> None:
        """Non-time-series constant values resolve to plain floats."""
        result = _load_battery(_battery_config(initial_soc={"type": "constant", "value": 80.0}))

        # initial_charge_percentage is STATE_OF_CHARGE + not time_series → scalar
        # Also a percent type, so 80.0 → 0.8
        assert result["storage"]["initial_charge_percentage"] == pytest.approx(0.8)

    def test_constant_boundary_field_has_n_plus_1_values(self) -> None:
        """Boundary fields expand constants to n+1 values (one per boundary)."""
        result = _load_battery(_battery_config(capacity={"type": "constant", "value": 10.0}))

        capacity = result["storage"]["capacity"]
        assert isinstance(capacity, np.ndarray)
        assert len(capacity) == 4  # n+1 boundaries
        np.testing.assert_array_equal(capacity, [10.0, 10.0, 10.0, 10.0])

    def test_percent_conversion_for_soc(self) -> None:
        """STATE_OF_CHARGE fields are divided by 100."""
        result = _load_battery(_battery_config(initial_soc={"type": "constant", "value": 100.0}))

        assert result["storage"]["initial_charge_percentage"] == pytest.approx(1.0)

    def test_none_value_removes_field(self) -> None:
        """None-typed values remove the field from loaded config."""
        result = _load_grid(_grid_config(export_price={"type": "none"}))

        assert "price_target_source" not in result["pricing"]

    def test_entity_value_loads_from_state_machine(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Entity values resolve through sensor loading pipeline."""

        def fake_load_sensors(_sm: Any, entity_ids: Sequence[str]) -> dict[str, float]:
            return {"sensor.import_price": 0.25}

        monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

        config = _grid_config(import_price={"type": "entity", "value": ["sensor.import_price"]})
        result = cast(
            "dict[str, Any]",
            load_element_config("Grid", _as_schema(config), FakeStateMachine({}), FORECAST_TIMES),
        )

        pricing = result["pricing"]
        assert isinstance(pricing["price_source_target"], np.ndarray)
        assert len(pricing["price_source_target"]) == 3

    def test_entity_value_with_forecast_series(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Entity values with forecast data fuse to interval arrays."""

        def fake_load_sensors(_sm: Any, entity_ids: Sequence[str]) -> dict[str, object]:
            return {
                "sensor.price": [
                    (0.0, 0.20),
                    (3600.0, 0.30),
                    (7200.0, 0.40),
                    (10800.0, 0.50),
                ],
            }

        monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

        config = _grid_config(import_price={"type": "entity", "value": ["sensor.price"]})
        result = cast(
            "dict[str, Any]",
            load_element_config("Grid", _as_schema(config), FakeStateMachine({}), FORECAST_TIMES),
        )

        pricing = result["pricing"]
        assert isinstance(pricing["price_source_target"], np.ndarray)
        assert len(pricing["price_source_target"]) == 3

    def test_unavailable_entity_leaves_field_as_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When sensors return no data, the field resolves to None."""

        def fake_load_sensors(_sm: Any, entity_ids: Sequence[str]) -> dict[str, float]:
            return {}

        monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

        config = _grid_config(import_price={"type": "entity", "value": ["sensor.missing"]})
        result = cast(
            "dict[str, Any]",
            load_element_config("Grid", _as_schema(config), FakeStateMachine({}), FORECAST_TIMES),
        )

        assert result["pricing"]["price_source_target"] is None

    def test_element_name_set_on_result(self) -> None:
        """The element name is set on the loaded config."""
        loaded = load_element_config("MyGrid", _as_schema(_grid_config()), FakeStateMachine({}), FORECAST_TIMES)
        result = cast("dict[str, Any]", loaded)

        assert result["name"] == "MyGrid"

    def test_unknown_element_type_raises(self) -> None:
        """Unknown element types raise ValueError."""
        config: dict[str, Any] = {"element_type": "unknown_type", "name": "X"}
        with pytest.raises(ValueError, match="Unknown element type"):
            load_element_config("X", _as_schema(config), FakeStateMachine({}), FORECAST_TIMES)

    def test_entity_percent_scalar_converts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Entity-backed SOC scalar values are divided by 100."""

        def fake_load_sensors(_sm: Any, entity_ids: Sequence[str]) -> dict[str, float]:
            return {"sensor.soc": 80.0}

        monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

        config = _battery_config(initial_soc={"type": "entity", "value": ["sensor.soc"]})
        result = _load_battery(config)

        assert result["storage"]["initial_charge_percentage"] == pytest.approx(0.8)

    def test_entity_percent_time_series_converts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Entity-backed SOC boundary values are divided by 100."""

        def fake_load_sensors(_sm: Any, entity_ids: Sequence[str]) -> dict[str, float]:
            return {"sensor.cap": 10.0}

        monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)
        monkeypatch.setattr(cl, "fuse_to_boundaries", lambda *_a, **_kw: [50.0, 60.0, 70.0, 80.0])

        config = _battery_config()
        config["storage"]["capacity"] = {"type": "constant", "value": 10.0}
        config["limits"] = {"min_charge_percentage": {"type": "entity", "value": ["sensor.cap"]}}
        result = _load_battery(config)

        np.testing.assert_allclose(result["limits"]["min_charge_percentage"], [0.5, 0.6, 0.7, 0.8])

    def test_boolean_field_passes_through(self) -> None:
        """Boolean fields (like node is_source) pass through unchanged."""
        config: dict[str, Any] = {
            "element_type": "node",
            "name": "Hub",
            "role": {"is_source": True, "is_sink": False},
        }
        result = cast(
            "dict[str, Any]",
            load_element_config("Hub", _as_schema(config), FakeStateMachine({}), FORECAST_TIMES),
        )

        assert result["role"]["is_source"] is True
        assert result["role"]["is_sink"] is False

    def test_entity_non_percent_scalar_resolves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-percent scalar entity values resolve without division."""

        def fake_load_sensors(_sm: Any, entity_ids: Sequence[str]) -> dict[str, float]:
            return {"sensor.salvage": 0.05}

        monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

        config = _battery_config()
        config["pricing"] = {"salvage_value": {"type": "entity", "value": ["sensor.salvage"]}}
        result = _load_battery(config)

        assert result["pricing"]["salvage_value"] == pytest.approx(0.05)

    def test_section_not_dict_is_skipped(self) -> None:
        """Non-dict section values are skipped during field resolution."""
        config = _grid_config()
        config["pricing"] = "not_a_dict"
        result = _load_grid(config)

        assert result["pricing"] == "not_a_dict"

    def test_original_config_not_mutated(self) -> None:
        """Loading creates a copy and does not mutate the original config."""
        config = _grid_config()
        original_pricing = dict(config["pricing"])

        load_element_config("Grid", _as_schema(config), FakeStateMachine({}), FORECAST_TIMES)

        assert config["pricing"] == original_pricing
        assert isinstance(config["pricing"]["price_source_target"], dict)


class TestLoadElementConfigs:
    """Tests for load_element_configs (multi-element)."""

    def test_loads_all_participants(self) -> None:
        """All participants are loaded and returned."""
        participants: dict[str, Any] = {
            "Grid": _grid_config(),
            "Battery": _battery_config(),
        }
        result = load_element_configs(cast("Mapping[str, ElementConfigSchema]", participants), FakeStateMachine({}), FORECAST_TIMES)

        assert set(result.keys()) == {"Grid", "Battery"}
        assert result["Grid"]["element_type"] == "grid"
        assert result["Battery"]["element_type"] == "battery"

    def test_element_names_match_keys(self) -> None:
        """Element names in loaded configs match the participant keys."""
        participants: dict[str, Any] = {
            "MyGrid": _grid_config(),
            "MyBattery": _battery_config(),
        }
        result = load_element_configs(cast("Mapping[str, ElementConfigSchema]", participants), FakeStateMachine({}), FORECAST_TIMES)

        assert result["MyGrid"]["name"] == "MyGrid"
        assert result["MyBattery"]["name"] == "MyBattery"

    def test_empty_participants_returns_empty(self) -> None:
        """Empty participants dict returns empty result."""
        result = load_element_configs({}, FakeStateMachine({}), FORECAST_TIMES)

        assert result == {}
