"""Tests for battery adapter config handling and model elements."""

from collections.abc import Sequence

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.battery import (
    BATTERY_DEVICE_BATTERY,
    BATTERY_ENERGY_STORED,
    BATTERY_POWER_ACTIVE,
    BATTERY_POWER_CHARGE,
    BATTERY_POWER_DISCHARGE,
)
from custom_components.haeo.core.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    ModelElementConfig,
)
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.elements.segments import is_efficiency_spec
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import battery

from .conftest import bus_node, grid_at, optimize_participants


def _get_connection(elements: Sequence[ModelElementConfig], name: str) -> ConnectionElementConfig:
    """Extract connection element by name from model elements list."""
    connection = next(
        (e for e in elements if e.get("element_type") == MODEL_ELEMENT_TYPE_CONNECTION and e.get("name") == name),
        None,
    )
    if connection is None:
        msg = f"Connection '{name}' not found in elements"
        raise ValueError(msg)
    return connection  # type: ignore[return-value]


def _wrap_data(flat: dict[str, object]) -> battery.BatteryConfigData:
    """Wrap flat battery config data values into sectioned config data."""
    common: dict[str, object] = {}
    storage: dict[str, object] = {}
    limits: dict[str, object] = {}
    power_limits: dict[str, object] = {}
    pricing: dict[str, object] = {}
    efficiency: dict[str, object] = {}
    advanced: dict[str, object] = {}

    for key, value in flat.items():
        if key in (
            "name",
            "connection",
        ):
            if key == "connection" and isinstance(value, str):
                common[key] = as_connection_target(value)
            else:
                common[key] = value
        elif key in (
            "capacity",
            "initial_charge_percentage",
        ):
            storage[key] = value
        elif key in (
            "min_charge_percentage",
            "max_charge_percentage",
        ):
            limits[key] = value
        elif key in ("efficiency_source_target", "efficiency_target_source"):
            efficiency[key] = value
        elif key in (
            "max_power_source_target",
            "max_power_target_source",
        ):
            power_limits[key] = value
        elif key in ("salvage_value",):
            pricing[key] = value
        elif key == battery.CONF_CHARGE_LIMIT_COST:
            advanced[key] = value

    pricing.setdefault(battery.CONF_SALVAGE_VALUE, 0.0)
    advanced.setdefault(battery.CONF_CHARGE_LIMIT_COST, 100.0)

    config: dict[str, object] = {
        "element_type": "battery",
        **common,
        battery.SECTION_STORAGE: storage,
        battery.SECTION_LIMITS: limits,
        battery.SECTION_POWER_LIMITS: power_limits,
        battery.SECTION_PRICING: pricing,
        battery.SECTION_EFFICIENCY: efficiency,
        battery.SECTION_ADVANCED: advanced,
    }
    return config  # type: ignore[return-value]


def test_model_elements_omits_efficiency_when_missing() -> None:
    """model_elements() should leave efficiency to model defaults when missing."""
    config_data: battery.BatteryConfigData = _wrap_data(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": 0.5,
        }
    )

    elements = battery_adapter.model_elements(config_data)

    battery_element = next(
        element
        for element in elements
        if element["element_type"] == MODEL_ELEMENT_TYPE_BATTERY and element["name"] == "test_battery"
    )
    np.testing.assert_array_equal(battery_element["capacity"], [10.0, 10.0, 10.0])

    connection = _get_connection(elements, "test_battery:discharge")
    segments = connection.get("segments")
    assert segments is not None
    efficiency_segment = segments.get("efficiency")
    assert efficiency_segment is not None
    assert is_efficiency_spec(efficiency_segment)
    assert efficiency_segment.get("efficiency") is None


def test_model_elements_defaults_salvage_value_when_missing() -> None:
    """model_elements() defaults salvage_value to 0.0 when omitted."""
    config_data: battery.BatteryConfigData = {
        "element_type": battery.ELEMENT_TYPE,
        "name": "test_battery",
        "connection": as_connection_target("main_bus"),
        battery.SECTION_STORAGE: {
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": 0.5,
        },
        battery.SECTION_LIMITS: {},
        battery.SECTION_POWER_LIMITS: {},
        battery.SECTION_PRICING: {},
        battery.SECTION_EFFICIENCY: {},
        battery.SECTION_ADVANCED: {battery.CONF_CHARGE_LIMIT_COST: 100.0},
    }

    elements = battery_adapter.model_elements(config_data)
    battery_element = next(
        element
        for element in elements
        if element["element_type"] == MODEL_ELEMENT_TYPE_BATTERY and element["name"] == "test_battery"
    )

    assert battery_element.get("salvage_value") == 0.0


def test_model_elements_passes_efficiency_when_present() -> None:
    """model_elements() should pass through provided efficiency values."""
    config_data: battery.BatteryConfigData = _wrap_data(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": 0.5,
            "efficiency_source_target": np.array([0.95, 0.95]),
            "efficiency_target_source": np.array([0.95, 0.95]),
        }
    )

    elements = battery_adapter.model_elements(config_data)

    connection = _get_connection(elements, "test_battery:discharge")
    segments = connection.get("segments")
    assert segments is not None
    efficiency_segment = segments.get("efficiency")
    assert efficiency_segment is not None
    assert is_efficiency_spec(efficiency_segment)
    efficiency_source_target = efficiency_segment.get("efficiency")
    assert efficiency_source_target is not None
    np.testing.assert_array_equal(efficiency_source_target, [0.95, 0.95])
    efficiency_target_source = efficiency_segment.get("efficiency")
    assert efficiency_target_source is not None
    np.testing.assert_array_equal(efficiency_target_source, [0.95, 0.95])


@pytest.mark.parametrize(
    ("limits", "initial", "expected_min", "expected_max", "expected_initial"),
    [
        pytest.param({}, 0.5, None, None, 5.0, id="unset_limits"),
        pytest.param(
            {"min_charge_percentage": np.array([0.1, 0.2, 0.2]), "max_charge_percentage": np.array([0.9, 0.8, 0.8])},
            0.5,
            [1.0, 2.0, 2.0],
            [9.0, 8.0, 8.0],
            5.0,
            id="limits_scale_by_capacity",
        ),
        pytest.param(
            {"min_charge_percentage": 0.2, "max_charge_percentage": 0.8},
            0.05,
            [2.0, 2.0, 2.0],
            [8.0, 8.0, 8.0],
            0.5,
            id="initial_below_min_kept_absolute",
        ),
        pytest.param({}, -0.1, None, None, 0.0, id="initial_clamped_to_empty"),
        pytest.param({}, 1.2, None, None, 10.0, id="initial_clamped_to_capacity"),
    ],
)
def test_model_elements_battery_charge_bounds(
    limits: dict[str, object],
    initial: float,
    expected_min: list[float] | None,
    expected_max: list[float] | None,
    expected_initial: float,
) -> None:
    """The model battery spans the full capacity, with min and max charge in kWh only when set, and the limit cost."""
    config_data = _wrap_data(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": initial,
            "charge_limit_cost": np.array([50.0, 60.0]),
            **limits,
        }
    )

    elements = battery_adapter.model_elements(config_data)
    battery_element = next(e for e in elements if e["element_type"] == MODEL_ELEMENT_TYPE_BATTERY)

    np.testing.assert_allclose(battery_element["capacity"], [10.0, 10.0, 10.0])
    assert "charge_limit_cost" in battery_element
    np.testing.assert_allclose(battery_element["charge_limit_cost"], [50.0, 60.0])
    for key, expected in (("min_charge", expected_min), ("max_charge", expected_max)):
        if expected is None:
            assert key not in battery_element
        else:
            np.testing.assert_allclose(battery_element[key], expected)
    assert battery_element["initial_charge"] == pytest.approx(expected_initial)


def _battery_at_bus(*, efficiency: float, cap: float, salvage_value: float) -> battery.BatteryConfigData:
    """Return a 20 kWh battery at half charge on the bus with equal limits and efficiency both ways."""
    return _wrap_data(
        {
            "name": "battery",
            "connection": "bus",
            "capacity": np.array([20.0, 20.0]),
            "initial_charge_percentage": 0.5,
            "max_power_source_target": np.array([cap]),
            "max_power_target_source": np.array([cap]),
            "efficiency_source_target": np.array([efficiency]),
            "efficiency_target_source": np.array([efficiency]),
            "salvage_value": salvage_value,
        }
    )


def test_adapter_discharge_cap_binds_bus_side() -> None:
    """The discharge limit caps power at the battery terminals and the sensor reports it there.

    Exporting is profitable, so the optimizer discharges at the limit.
    The bus receives exactly the limit while the cells give up limit / efficiency.
    """
    efficiency = 0.9
    cap = 5.0
    config = _battery_at_bus(efficiency=efficiency, cap=cap, salvage_value=0.0)
    model_outputs = optimize_participants(
        {"bus": bus_node("bus"), "battery": config, "grid": grid_at("grid", "bus", import_price=1.0, export_price=0.5)}
    )

    outputs = battery_adapter.outputs("battery", model_outputs, config=config)[BATTERY_DEVICE_BATTERY]

    discharge = outputs[BATTERY_POWER_DISCHARGE].values[0]
    charge = outputs[BATTERY_POWER_CHARGE].values[0]
    stored = outputs[BATTERY_ENERGY_STORED].values
    assert discharge == pytest.approx(cap)
    assert charge == pytest.approx(0.0)
    assert stored[0] - stored[1] == pytest.approx(cap / efficiency)
    assert outputs[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(discharge - charge)


def test_adapter_charge_cap_binds_bus_side() -> None:
    """The charge limit caps power at the battery terminals and the sensor reports it there.

    Stored energy is worth more than it costs to import, so the optimizer charges at the limit.
    The bus supplies exactly the limit while the cells take in limit x efficiency.
    """
    efficiency = 0.9
    cap = 5.0
    config = _battery_at_bus(efficiency=efficiency, cap=cap, salvage_value=1.0)
    model_outputs = optimize_participants(
        {"bus": bus_node("bus"), "battery": config, "grid": grid_at("grid", "bus", import_price=0.1, export_price=0.0)}
    )

    outputs = battery_adapter.outputs("battery", model_outputs, config=config)[BATTERY_DEVICE_BATTERY]

    discharge = outputs[BATTERY_POWER_DISCHARGE].values[0]
    charge = outputs[BATTERY_POWER_CHARGE].values[0]
    stored = outputs[BATTERY_ENERGY_STORED].values
    assert charge == pytest.approx(cap)
    assert discharge == pytest.approx(0.0)
    assert stored[1] - stored[0] == pytest.approx(cap * efficiency)
    assert outputs[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(discharge - charge)
