"""Tests for battery adapter config handling and model elements."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant
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
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import ElementType, battery
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.node import NodeConfigData
from custom_components.haeo.elements.availability import schema_config_available

from .conftest import optimize_participants


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


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


def _wrap_config(flat: dict[str, object]) -> battery.BatteryConfigSchema:
    """Wrap flat battery config values into sectioned config."""

    def to_schema_value(value: object) -> object:
        if value is None:
            return as_none_value()
        if isinstance(value, bool):
            return as_constant_value(value)
        if isinstance(value, (int, float)):
            return as_constant_value(float(value))
        if isinstance(value, str):
            return as_entity_value([value])
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            if not value:
                return as_none_value()
            return as_entity_value(value)
        return value

    common: dict[str, object] = {}
    storage: dict[str, object] = {}
    limits: dict[str, object] = {}
    power_limits: dict[str, object] = {}
    pricing: dict[str, object] = {}
    efficiency: dict[str, object] = {}
    partitioning: dict[str, object] = {}
    undercharge: dict[str, object] = {}
    overcharge: dict[str, object] = {}

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
            storage[key] = to_schema_value(value)
        elif key in (
            "min_charge_percentage",
            "max_charge_percentage",
        ):
            limits[key] = to_schema_value(value)
        elif key in ("efficiency_source_target", "efficiency_target_source"):
            efficiency[key] = to_schema_value(value)
        elif key == "configure_partitions":
            partitioning[key] = value
        elif key in (
            "max_power_source_target",
            "max_power_target_source",
        ):
            power_limits[key] = to_schema_value(value)
        elif key in ("salvage_value",):
            pricing[key] = to_schema_value(value)
        elif key == "undercharge" and isinstance(value, dict):
            undercharge.update({subkey: to_schema_value(subvalue) for subkey, subvalue in value.items()})
        elif key == "overcharge" and isinstance(value, dict):
            overcharge.update({subkey: to_schema_value(subvalue) for subkey, subvalue in value.items()})

    pricing.setdefault("salvage_value", as_constant_value(0.0))

    config: dict[str, object] = {
        "element_type": "battery",
        **common,
        battery.SECTION_STORAGE: storage,
        battery.SECTION_LIMITS: limits,
        battery.SECTION_POWER_LIMITS: power_limits,
        battery.SECTION_PRICING: pricing,
        battery.SECTION_EFFICIENCY: efficiency,
        battery.SECTION_PARTITIONING: partitioning,
        battery.SECTION_UNDERCHARGE: undercharge,
        battery.SECTION_OVERCHARGE: overcharge,
    }
    return config  # type: ignore[return-value]


def _wrap_data(flat: dict[str, object]) -> battery.BatteryConfigData:
    """Wrap flat battery config data values into sectioned config data."""
    common: dict[str, object] = {}
    storage: dict[str, object] = {}
    limits: dict[str, object] = {}
    power_limits: dict[str, object] = {}
    pricing: dict[str, object] = {}
    efficiency: dict[str, object] = {}
    partitioning: dict[str, object] = {}
    undercharge: dict[str, object] = {}
    overcharge: dict[str, object] = {}

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
        elif key == "configure_partitions":
            partitioning[key] = value
        elif key in (
            "max_power_source_target",
            "max_power_target_source",
        ):
            power_limits[key] = value
        elif key in ("salvage_value",):
            pricing[key] = value
        elif key == "undercharge" and isinstance(value, dict):
            undercharge.update(value)
        elif key == "overcharge" and isinstance(value, dict):
            overcharge.update(value)

    pricing.setdefault(battery.CONF_SALVAGE_VALUE, 0.0)

    config: dict[str, object] = {
        "element_type": "battery",
        **common,
        battery.SECTION_STORAGE: storage,
        battery.SECTION_LIMITS: limits,
        battery.SECTION_POWER_LIMITS: power_limits,
        battery.SECTION_PRICING: pricing,
        battery.SECTION_EFFICIENCY: efficiency,
        battery.SECTION_PARTITIONING: partitioning,
        battery.SECTION_UNDERCHARGE: undercharge,
        battery.SECTION_OVERCHARGE: overcharge,
    }
    return config  # type: ignore[return-value]


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Battery available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "max_power_target_source": "sensor.max_charge",
            "max_power_source_target": "sensor.max_discharge",
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_false_when_required_power_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required power sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    # max_power_source_target sensor is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "max_power_target_source": "sensor.max_charge",
            "max_power_source_target": "sensor.missing",
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_false_when_capacity_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when capacity sensor is missing."""
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    # capacity sensor is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.missing_capacity",
            "initial_charge_percentage": "sensor.initial",
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_false_when_required_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")
    # initial_charge_percentage sensor is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.missing",
            "max_power_target_source": "sensor.max_charge",
            "max_power_source_target": "sensor.max_discharge",
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_with_list_entity_ids_all_exist(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] entity IDs all exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_discharge_1", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge_2", "4.0", "kW")

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "max_power_source_target": ["sensor.max_discharge_1", "sensor.max_discharge_2"],
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_with_list_entity_ids_one_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when list[str] entity ID has one missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_discharge_1", "5.0", "kW")
    # sensor.max_discharge_missing is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "max_power_source_target": ["sensor.max_discharge_1", "sensor.max_discharge_missing"],
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_with_empty_list_returns_true(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] is empty."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "max_power_source_target": [],
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_true_with_constant_values(hass: HomeAssistant) -> None:
    """Battery available() returns True when values are constants."""
    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": 10.0,
            "initial_charge_percentage": 0.5,
            "max_power_target_source": 5.0,
            "max_power_source_target": 4.0,
            "salvage_value": 0.01,
            "efficiency_source_target": 0.95,
            "efficiency_target_source": 0.94,
            "undercharge": {"partition_percentage": 0.1, "partition_cost": 0.2},
            "overcharge": {"partition_percentage": 0.05, "partition_cost": 0.15},
        }
    )

    result = schema_config_available(config, sm=hass.states)
    assert result is True


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
        battery.SECTION_PARTITIONING: {},
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


def test_model_elements_overcharge_only_adds_soc_pricing() -> None:
    """SOC pricing is added when only overcharge inputs are configured."""
    config_data: battery.BatteryConfigData = _wrap_data(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": 0.5,
            "min_charge_percentage": np.array([0.1, 0.1, 0.1]),
            "max_charge_percentage": np.array([0.9, 0.9, 0.9]),
            "overcharge": {
                "percentage": np.array([0.95, 0.95, 0.95]),
                "cost": np.array([0.2, 0.2]),
            },
        }
    )

    elements = battery_adapter.model_elements(config_data)
    connection = _get_connection(elements, "test_battery:discharge")
    segments = connection.get("segments")
    assert segments is not None
    soc_pricing = segments.get("soc_pricing")
    assert soc_pricing is not None
    assert soc_pricing.get("discharge_energy_threshold") is None
    assert soc_pricing.get("charge_capacity_threshold") is not None


def _grid(name: str, *, import_price: float, export_price: float) -> GridConfigData:
    """Return an unconstrained grid connected to the bus."""
    return GridConfigData(
        element_type=ElementType.GRID,
        name=name,
        connection=as_connection_target("bus"),
        pricing={"price_source_target": np.array([import_price]), "price_target_source": np.array([export_price])},
        power_limits={},
    )


def _bus() -> NodeConfigData:
    """Return a passive bus node."""
    return NodeConfigData(element_type=ElementType.NODE, name="bus", role={"is_source": False, "is_sink": False})


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
        {"bus": _bus(), "battery": config, "grid": _grid("grid", import_price=1.0, export_price=0.5)}
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
        {"bus": _bus(), "battery": config, "grid": _grid("grid", import_price=0.1, export_price=0.0)}
    )

    outputs = battery_adapter.outputs("battery", model_outputs, config=config)[BATTERY_DEVICE_BATTERY]

    discharge = outputs[BATTERY_POWER_DISCHARGE].values[0]
    charge = outputs[BATTERY_POWER_CHARGE].values[0]
    stored = outputs[BATTERY_ENERGY_STORED].values
    assert charge == pytest.approx(cap)
    assert discharge == pytest.approx(0.0)
    assert stored[1] - stored[0] == pytest.approx(cap * efficiency)
    assert outputs[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(discharge - charge)
