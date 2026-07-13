"""Tests for the core config loader."""

from collections.abc import Sequence

import numpy as np
import pytest

from conftest import FakeStateMachine
from custom_components.haeo.core.data.loader import config_loader as cl
from custom_components.haeo.core.data.loader.config_loader import (
    _resolve_list_items,
    load_element_config,
    load_element_config_from_values,
    load_element_configs,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConstantValue, EntityValue, as_connection_target
from custom_components.haeo.core.schema.elements.battery import CONF_CAPACITY, SECTION_STORAGE
from custom_components.haeo.core.schema.elements.policy import CONF_PRICE, CONF_RULES
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints
from custom_components.haeo.core.schema.sections import CONF_EFFICIENCY_SOURCE_TARGET, SECTION_EFFICIENCY
from custom_components.haeo.core.state import StateMachine

FORECAST_TIMES = (0.0, 3600.0, 7200.0, 10800.0)

_DEFAULT_IMPORT_PRICE: ConstantValue = {"type": "constant", "value": 0.30}
_DEFAULT_EXPORT_PRICE: ConstantValue = {"type": "constant", "value": 0.05}
_DEFAULT_CAPACITY: ConstantValue = {"type": "constant", "value": 10.0}
_DEFAULT_INITIAL_SOC: ConstantValue = {"type": "constant", "value": 50.0}


def _dict(value: object) -> dict[str, object]:
    """Narrow a loaded config value to a dict for nested assertions."""
    assert isinstance(value, dict)
    return value


def _list(value: object) -> list[object]:
    """Narrow a loaded config value to a list for nested assertions."""
    assert isinstance(value, list)
    return value


def _ndarray(value: object) -> np.ndarray:
    """Narrow a loaded field value to an ndarray for array assertions."""
    assert isinstance(value, np.ndarray)
    return value


def _numeric(value: object) -> np.ndarray | float:
    """Narrow a loaded field value to array-or-scalar for numeric assertions."""
    assert isinstance(value, np.ndarray | float)
    return value


def _grid_config(
    *,
    import_price: object = None,
    export_price: object = None,
) -> dict[str, object]:
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
    capacity: object = None,
    initial_soc: object = None,
) -> dict[str, object]:
    return {
        "element_type": "battery",
        "name": "Battery",
        "common": {"connection": "node_a"},
        "storage": {
            "capacity": capacity if capacity is not None else _DEFAULT_CAPACITY,
            "initial_charge_percentage": initial_soc if initial_soc is not None else _DEFAULT_INITIAL_SOC,
        },
    }


def _inverter_config(
    *, efficiency_source_target: object = None, efficiency_target_source: object = None
) -> dict[str, object]:
    return {
        "element_type": "inverter",
        "name": "Inverter",
        "connection": as_connection_target("node_a"),
        "power_limits": {
            "max_power_source_target": {"type": "constant", "value": 10.0},
            "max_power_target_source": {"type": "constant", "value": 10.0},
        },
        "efficiency": {
            **({"efficiency_source_target": efficiency_source_target} if efficiency_source_target is not None else {}),
            **({"efficiency_target_source": efficiency_target_source} if efficiency_target_source is not None else {}),
        },
    }


def _connection_config(
    *, efficiency_source_target: object = None, efficiency_target_source: object = None
) -> dict[str, object]:
    return {
        "element_type": "connection",
        "name": "Connection",
        "endpoints": {"source": as_connection_target("node_a"), "target": as_connection_target("node_b")},
        "pricing": {},
        "power_limits": {},
        "efficiency": {
            **({"efficiency_source_target": efficiency_source_target} if efficiency_source_target is not None else {}),
            **({"efficiency_target_source": efficiency_target_source} if efficiency_target_source is not None else {}),
        },
    }


def _load_config(name: str, config: dict[str, object]) -> dict[str, object]:
    """Load an element config and return as plain dict for assertion."""
    return _dict(
        load_element_config(
            name,
            config,  # type: ignore[arg-type]  # fixtures use loose dicts; loader validates at runtime
            FakeStateMachine({}),
            FORECAST_TIMES,
        )
    )


def _load_grid(config: dict[str, object] | None = None) -> dict[str, object]:
    """Load a grid config and return as plain dict for easy assertion."""
    return _load_config("Grid", config or _grid_config())


def _load_battery(config: dict[str, object] | None = None) -> dict[str, object]:
    """Load a battery config and return as plain dict for easy assertion."""
    return _load_config("Battery", config or _battery_config())


def _grid_config_without_export() -> dict[str, object]:
    """Grid config with the export price field removed entirely."""
    config = _grid_config()
    _dict(config["pricing"]).pop("price_target_source")
    return config


# -- load_element_config tests --


def test_constant_values_resolve_to_time_series() -> None:
    """Constant pricing values expand to arrays matching forecast intervals."""
    result = _load_grid()

    pricing = _dict(result["pricing"])
    price_source_target = _ndarray(pricing["price_source_target"])
    assert len(price_source_target) == 3
    np.testing.assert_array_equal(price_source_target, [0.30, 0.30, 0.30])

    price_target_source = _ndarray(pricing["price_target_source"])
    np.testing.assert_array_equal(price_target_source, [0.05, 0.05, 0.05])


@pytest.mark.parametrize(
    ("input_percent", "expected"),
    [(80.0, 0.8), (100.0, 1.0), (50.0, 0.5), (0.0, 0.0)],
    ids=["80%", "100%", "50%", "0%"],
)
def test_constant_soc_percent_conversion(input_percent: float, expected: float) -> None:
    """Constant SOC percentage values are divided by 100."""
    result = _load_battery(_battery_config(initial_soc={"type": "constant", "value": input_percent}))

    storage = _dict(result["storage"])
    assert storage["initial_charge_percentage"] == pytest.approx(expected)


def test_constant_boundary_field_has_n_plus_1_values() -> None:
    """Boundary fields expand constants to n+1 values (one per boundary)."""
    result = _load_battery(_battery_config(capacity={"type": "constant", "value": 10.0}))

    capacity = _ndarray(_dict(result["storage"])["capacity"])
    assert len(capacity) == 4  # n+1 boundaries
    np.testing.assert_array_equal(capacity, [10.0, 10.0, 10.0, 10.0])


@pytest.mark.parametrize(
    "config",
    [
        pytest.param(_grid_config(export_price={"type": "none"}), id="none_type"),
        pytest.param(_grid_config_without_export(), id="field_missing"),
    ],
)
def test_optional_pricing_field_is_absent(config: dict[str, object]) -> None:
    """Optional pricing fields are absent when set to none or not provided."""
    result = _load_grid(config)

    assert "price_target_source" not in _dict(result["pricing"])


@pytest.mark.parametrize(
    ("element_name", "config"),
    [
        ("Inverter", _inverter_config()),
        ("Battery", {**_battery_config(), "efficiency": {}}),
        ("Connection", _connection_config()),
        (
            "Inverter",
            _inverter_config(
                efficiency_source_target={"type": "none"},
                efficiency_target_source={"type": "none"},
            ),
        ),
        (
            "Connection",
            _connection_config(
                efficiency_source_target={"type": "none"},
                efficiency_target_source={"type": "none"},
            ),
        ),
    ],
    ids=(
        "inverter_missing",
        "battery_missing",
        "connection_missing",
        "inverter_none",
        "connection_none",
    ),
)
def test_efficiency_defaults_to_unity(
    element_name: str,
    config: dict[str, object],
) -> None:
    """Missing or none-typed efficiency fields default to 100%."""
    result = _load_config(element_name, config)
    efficiency = _dict(result["efficiency"])
    np.testing.assert_allclose(_numeric(efficiency["efficiency_source_target"]), [1.0, 1.0, 1.0])
    np.testing.assert_allclose(_numeric(efficiency["efficiency_target_source"]), [1.0, 1.0, 1.0])


def test_unavailable_efficiency_entity_defaults_to_unity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unavailable efficiency entity data falls back to 100% defaults."""

    def fake_load_sensors(_sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, float]:
        return {}

    monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

    config = _inverter_config(
        efficiency_source_target={"type": "entity", "value": ["sensor.missing_eff_st"]},
        efficiency_target_source={"type": "entity", "value": ["sensor.missing_eff_ts"]},
    )
    result = _load_config("Inverter", config)
    efficiency = _dict(result["efficiency"])
    np.testing.assert_allclose(_numeric(efficiency["efficiency_source_target"]), [1.0, 1.0, 1.0])
    np.testing.assert_allclose(_numeric(efficiency["efficiency_target_source"]), [1.0, 1.0, 1.0])


@pytest.mark.parametrize(
    ("sensor_data", "import_price_config"),
    [
        (
            {"sensor.import_price": 0.25},
            {"type": "entity", "value": ["sensor.import_price"]},
        ),
        (
            {
                "sensor.price": [
                    (0.0, 0.20),
                    (3600.0, 0.30),
                    (7200.0, 0.40),
                    (10800.0, 0.50),
                ],
            },
            {"type": "entity", "value": ["sensor.price"]},
        ),
    ],
    ids=["scalar_sensor", "forecast_series"],
)
def test_entity_value_resolves_to_time_series(
    monkeypatch: pytest.MonkeyPatch,
    sensor_data: dict[str, object],
    import_price_config: EntityValue,
) -> None:
    """Entity values resolve to time series arrays regardless of sensor data shape."""

    def fake_load_sensors(_sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, object]:
        return sensor_data

    monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

    config = _grid_config(import_price=import_price_config)
    result = _load_grid(config)

    pricing = _dict(result["pricing"])
    price_source_target = _ndarray(pricing["price_source_target"])
    assert len(price_source_target) == 3


@pytest.mark.parametrize(
    "import_price",
    [
        pytest.param({"type": "entity", "value": ["sensor.missing"]}, id="unavailable_entity"),
        pytest.param({"type": "entity", "value": []}, id="empty_entity_ids"),
        pytest.param(42, id="unrecognized_value_type"),
    ],
)
def test_price_field_resolves_to_none(
    monkeypatch: pytest.MonkeyPatch,
    import_price: object,
) -> None:
    """Price field resolves to None for unavailable, empty, or unrecognized values."""

    def fake_load_sensors(_sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, float]:
        return {}

    monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

    config = _grid_config(import_price=import_price)
    result = _load_grid(config)

    assert _dict(result["pricing"])["price_source_target"] is None


def test_element_name_set_on_result() -> None:
    """The element name is set on the loaded config."""
    result = _load_config("MyGrid", _grid_config())

    assert result["name"] == "MyGrid"


def test_unknown_element_type_raises() -> None:
    """Unknown element types raise ValueError."""
    config: dict[str, object] = {"element_type": "unknown_type", "name": "X"}
    with pytest.raises(ValueError, match="Unknown element type"):
        load_element_config(
            "X",
            config,  # type: ignore[arg-type]  # deliberately invalid input
            FakeStateMachine({}),
            FORECAST_TIMES,
        )


def test_entity_percent_scalar_converts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entity-backed SOC scalar values are divided by 100."""

    def fake_load_sensors(_sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, float]:
        return {"sensor.soc": 80.0}

    monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

    config = _battery_config(initial_soc={"type": "entity", "value": ["sensor.soc"]})
    result = _load_battery(config)

    storage = _dict(result["storage"])
    assert storage["initial_charge_percentage"] == pytest.approx(0.8)


def test_entity_percent_time_series_converts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entity-backed SOC boundary values are divided by 100."""

    def fake_load_sensors(_sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, float]:
        return {"sensor.cap": 10.0}

    monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)
    monkeypatch.setattr(cl, "fuse_to_boundaries", lambda *_a, **_kw: [50.0, 60.0, 70.0, 80.0])

    config = _battery_config()
    _dict(config["storage"])["capacity"] = {"type": "constant", "value": 10.0}
    config["limits"] = {"min_charge_percentage": {"type": "entity", "value": ["sensor.cap"]}}
    result = _load_battery(config)

    limits = _dict(result["limits"])
    np.testing.assert_allclose(_numeric(limits["min_charge_percentage"]), [0.5, 0.6, 0.7, 0.8])


@pytest.mark.parametrize(
    "role_input",
    [
        pytest.param({"is_source": True, "is_sink": False}, id="raw_booleans"),
        pytest.param(
            {
                "is_source": {"type": "constant", "value": True},
                "is_sink": {"type": "constant", "value": False},
            },
            id="constant_wrapped",
        ),
    ],
)
def test_boolean_values_pass_through(role_input: dict[str, object]) -> None:
    """Boolean fields pass through unchanged whether raw or constant-wrapped."""
    config: dict[str, object] = {
        "element_type": "node",
        "name": "Hub",
        "role": role_input,
    }
    result = _load_config("Hub", config)

    role = _dict(result["role"])
    assert role["is_source"] is True
    assert role["is_sink"] is False


def test_entity_non_percent_scalar_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-percent scalar entity values resolve without division."""

    def fake_load_sensors(_sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, float]:
        return {"sensor.salvage": 0.05}

    monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

    config = _battery_config()
    config["pricing"] = {"salvage_value": {"type": "entity", "value": ["sensor.salvage"]}}
    result = _load_battery(config)

    pricing = _dict(result["pricing"])
    assert pricing["salvage_value"] == pytest.approx(0.05)


def test_section_not_dict_is_skipped() -> None:
    """Non-dict section values are skipped during field resolution."""
    config = _grid_config()
    config["pricing"] = "not_a_dict"
    result = _load_grid(config)

    assert result["pricing"] == "not_a_dict"


def test_original_config_not_mutated() -> None:
    """Loading creates a copy and does not mutate the original config."""
    config = _grid_config()
    original_pricing = dict(_dict(config["pricing"]))

    load_element_config(
        "Grid",
        config,  # type: ignore[arg-type]  # fixtures use loose dicts; loader validates at runtime
        FakeStateMachine({}),
        FORECAST_TIMES,
    )

    assert config["pricing"] == original_pricing
    assert isinstance(_dict(config["pricing"])["price_source_target"], dict)


# -- load_element_configs tests --


def test_load_element_configs_loads_all_participants() -> None:
    """All participants are loaded and returned."""
    participants: dict[str, object] = {
        "Grid": _grid_config(),
        "Battery": _battery_config(),
    }
    result = load_element_configs(
        participants,  # type: ignore[arg-type]  # fixtures use loose dicts; loader validates at runtime
        FakeStateMachine({}),
        FORECAST_TIMES,
    )

    assert set(result.keys()) == {"Grid", "Battery"}
    assert result["Grid"]["element_type"] == "grid"
    assert result["Battery"]["element_type"] == "battery"


def test_load_element_configs_element_names_match_keys() -> None:
    """Element names in loaded configs match the participant keys."""
    participants: dict[str, object] = {
        "MyGrid": _grid_config(),
        "MyBattery": _battery_config(),
    }
    result = load_element_configs(
        participants,  # type: ignore[arg-type]  # fixtures use loose dicts; loader validates at runtime
        FakeStateMachine({}),
        FORECAST_TIMES,
    )

    assert result["MyGrid"]["name"] == "MyGrid"
    assert result["MyBattery"]["name"] == "MyBattery"


def test_load_element_configs_empty_participants_returns_empty() -> None:
    """Empty participants dict returns empty result."""
    result = load_element_configs({}, FakeStateMachine({}), FORECAST_TIMES)

    assert result == {}


# -- _resolve_list_items tests --


def test_resolve_list_items_constant_values() -> None:
    """Constant values in list items are resolved to their unwrapped form."""
    hints = ListFieldHints(
        fields={"price": FieldHint(output_type=OutputType.PRICE, time_series=True)},
    )
    items: list[dict[str, object]] = [
        {"name": "rule1", "price": {"type": "constant", "value": 0.05}},
    ]

    result = _resolve_list_items(items, hints, FakeStateMachine({}), FORECAST_TIMES)

    assert len(result) == 1
    item0 = _dict(result[0])
    assert item0["name"] == "rule1"
    price = _ndarray(item0["price"])
    np.testing.assert_array_equal(price, [0.05, 0.05, 0.05])


@pytest.mark.parametrize(
    "items",
    [
        pytest.param(
            [{"name": "rule1", "enabled": True, "price": {"type": "constant", "value": 0.0}}], id="zero_price"
        ),
    ],
)
def test_resolve_list_items_zero_price_loads(items: list[dict[str, object]]) -> None:
    """Zero-value constant price is loaded as array of zeros."""
    hints = ListFieldHints(
        fields={"price": FieldHint(output_type=OutputType.PRICE, time_series=True)},
    )

    result = _resolve_list_items(items, hints, FakeStateMachine({}), FORECAST_TIMES)

    item0 = _dict(result[0])
    assert "price" in item0
    assert item0["name"] == "rule1"


def test_resolve_list_items_unavailable_entity_sets_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """When entity resolution returns None, the field is set to None."""

    def fake_load_sensors(_sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, float]:
        return {}

    monkeypatch.setattr(cl, "load_sensors", fake_load_sensors)

    hints = ListFieldHints(
        fields={"price": FieldHint(output_type=OutputType.PRICE, time_series=True)},
    )
    items: list[dict[str, object]] = [
        {"name": "rule1", "price": {"type": "entity", "value": ["sensor.missing"]}},
    ]

    result = _resolve_list_items(items, hints, FakeStateMachine({}), FORECAST_TIMES)

    assert _dict(result[0])["price"] is None


def test_resolve_list_items_non_mapping_pass_through() -> None:
    """Non-mapping items are appended unchanged."""
    hints = ListFieldHints(
        fields={"price": FieldHint(output_type=OutputType.PRICE)},
    )
    items: list[object] = ["not_a_dict", 42]

    result = _resolve_list_items(items, hints, FakeStateMachine({}), FORECAST_TIMES)

    assert result == ["not_a_dict", 42]


def test_load_element_config_resolves_list_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """List fields in element config are resolved through the list pipeline."""
    hints = ListFieldHints(
        fields={"price": FieldHint(output_type=OutputType.PRICE, time_series=True)},
    )

    monkeypatch.setattr(cl, "extract_list_field_hints", lambda _cls: {"rules": hints})

    config: dict[str, object] = {
        "element_type": "grid",
        "name": "Grid",
        "common": {"connection": "node_a"},
        "pricing": {
            "price_source_target": {"type": "constant", "value": 0.30},
            "price_target_source": {"type": "constant", "value": 0.05},
        },
        "power_limits": {
            "max_power_source_target": {"type": "constant", "value": 10.0},
            "max_power_target_source": {"type": "constant", "value": 10.0},
        },
        "rules": [{"name": "solar", "price": {"type": "constant", "value": 0.02}}],
    }

    result = _load_config("Grid", config)

    assert "rules" in result
    rules = _list(result["rules"])
    assert len(rules) == 1
    price = _ndarray(_dict(rules[0])["price"])
    np.testing.assert_array_equal(price, [0.02, 0.02, 0.02])


# -- load_element_config_from_values tests --


def _load_config_from_values(
    name: str,
    config: dict[str, object],
    field_values: dict[tuple[str, ...], bool | float | np.ndarray | None],
) -> dict[str, object]:
    """Load an element config from store values and return as a plain dict."""
    return _dict(
        load_element_config_from_values(
            name,
            config,  # type: ignore[arg-type]  # fixtures use loose dicts; loader validates at runtime
            field_values,
            FORECAST_TIMES,
        )
    )


def test_load_element_config_from_values_substitutes_store_values() -> None:
    """Pre-resolved store values are written into the loaded element config."""
    config = _battery_config()
    prices = np.array([10.0, 10.0, 10.0, 10.0])

    result = _load_config_from_values(
        "Battery",
        config,
        {(SECTION_STORAGE, CONF_CAPACITY): prices},
    )

    np.testing.assert_array_equal(_dict(result["storage"])["capacity"], prices)


def test_load_element_config_from_values_none_uses_default() -> None:
    """A None store value falls back to the field hint default when one exists."""
    config = _inverter_config(efficiency_source_target={"type": "constant", "value": 90.0})

    result = _load_config_from_values(
        "Inverter",
        config,
        {(SECTION_EFFICIENCY, CONF_EFFICIENCY_SOURCE_TARGET): None},
    )

    efficiency = _dict(result["efficiency"])
    np.testing.assert_allclose(_numeric(efficiency["efficiency_source_target"]), [1.0, 1.0, 1.0])


def test_load_element_config_from_values_missing_optional_field_is_removed() -> None:
    """Fields without a store entry and no default are removed from the loaded config."""
    config = _grid_config_without_export()

    result = _load_config_from_values("Grid", config, {})

    assert "price_target_source" not in _dict(result["pricing"])


def test_load_element_config_from_values_missing_field_uses_default() -> None:
    """Fields without a store entry receive schema defaults when configured."""
    config = _inverter_config()

    result = _load_config_from_values("Inverter", config, {})

    efficiency = _dict(result["efficiency"])
    np.testing.assert_allclose(_numeric(efficiency["efficiency_source_target"]), [1.0, 1.0, 1.0])


def test_load_element_config_from_values_applies_list_field_values() -> None:
    """List-backed fields (e.g. policy rules) accept pre-resolved store values."""
    config: dict[str, object] = {
        "element_type": "policy",
        "name": "Policies",
        "rules": [{"name": "solar", "enabled": True, "price": {"type": "constant", "value": 0.02}}],
    }
    resolved_price = np.array([0.02, 0.02, 0.02])

    result = _load_config_from_values(
        "Policies",
        config,
        {(CONF_RULES, "0", CONF_PRICE): resolved_price},
    )

    rules = _list(result["rules"])
    np.testing.assert_array_equal(_dict(rules[0])["price"], resolved_price)


def test_load_element_config_from_values_skips_non_mapping_list_items() -> None:
    """Non-mapping list entries pass through unchanged."""
    config: dict[str, object] = {
        "element_type": "policy",
        "name": "Policies",
        "rules": ["literal-entry", {"name": "priced", "enabled": True, "price": {"type": "constant", "value": 0.01}}],
    }

    result = _load_config_from_values("Policies", config, {})

    assert _list(result["rules"])[0] == "literal-entry"


def test_load_element_config_from_values_skips_invalid_list_container() -> None:
    """List field assembly is skipped when the config value is not a sequence."""
    config: dict[str, object] = {
        "element_type": "policy",
        "name": "Policies",
        "rules": "not-a-list",
    }

    result = _dict(
        load_element_config_from_values(
            "Policies",
            config,  # type: ignore[arg-type]  # rules is not a list; is_element_config_schema rejects this fixture
            {},
            FORECAST_TIMES,
        )
    )

    assert result["rules"] == "not-a-list"


def test_load_element_config_from_values_unknown_element_type_raises() -> None:
    """Invalid element types are rejected before assembly."""
    with pytest.raises(ValueError, match="Unknown element type"):
        load_element_config_from_values(
            "Bad",
            {"element_type": "not_real", "name": "Bad"},  # type: ignore[typeddict-item]  # invalid element_type must reach runtime validation
            {},
            FORECAST_TIMES,
        )
