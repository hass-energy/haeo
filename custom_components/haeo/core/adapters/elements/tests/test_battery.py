"""Tests for battery adapter config handling and model elements."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.core.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_ENERGY_STORAGE,
    MODEL_ELEMENT_TYPE_NODE,
    ModelElementConfig,
)
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.elements.energy_storage import BATTERY_POWER_CHARGE, BATTERY_POWER_DISCHARGE
from custom_components.haeo.core.model.elements.segments import is_efficiency_spec
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import battery
from custom_components.haeo.elements.availability import schema_config_available


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
    power_limits: dict[str, object] = {}
    pricing: dict[str, object] = {}
    efficiency: dict[str, object] = {}

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
        elif key in ("efficiency_source_target", "efficiency_target_source"):
            efficiency[key] = to_schema_value(value)
        elif key in (
            "max_power_source_target",
            "max_power_target_source",
        ):
            power_limits[key] = to_schema_value(value)
        elif key in ("salvage_value",):
            pricing[key] = to_schema_value(value)

    pricing.setdefault("salvage_value", as_constant_value(0.0))

    config: dict[str, object] = {
        "element_type": "battery",
        **common,
        battery.SECTION_STORAGE: storage,
        battery.SECTION_POWER_LIMITS: power_limits,
        battery.SECTION_PRICING: pricing,
        battery.SECTION_EFFICIENCY: efficiency,
    }
    return config  # type: ignore[return-value]


def _wrap_data(flat: dict[str, object]) -> battery.BatteryConfigData:
    """Wrap flat battery config data values into sectioned config data."""
    common: dict[str, object] = {}
    storage: dict[str, object] = {}
    power_limits: dict[str, object] = {}
    pricing: dict[str, object] = {}
    efficiency: dict[str, object] = {}

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
        elif key in ("efficiency_source_target", "efficiency_target_source"):
            efficiency[key] = value
        elif key in (
            "max_power_source_target",
            "max_power_target_source",
        ):
            power_limits[key] = value
        elif key in ("salvage_value",):
            pricing[key] = value

    pricing.setdefault(battery.CONF_SALVAGE_VALUE, 0.0)

    config: dict[str, object] = {
        "element_type": "battery",
        **common,
        battery.SECTION_STORAGE: storage,
        battery.SECTION_POWER_LIMITS: power_limits,
        battery.SECTION_PRICING: pricing,
        battery.SECTION_EFFICIENCY: efficiency,
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
        if element["element_type"] == MODEL_ELEMENT_TYPE_ENERGY_STORAGE and element["name"] == "test_battery"
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
        battery.SECTION_POWER_LIMITS: {},
        battery.SECTION_PRICING: {},
        battery.SECTION_EFFICIENCY: {},
    }

    elements = battery_adapter.model_elements(config_data)
    battery_element = next(
        element
        for element in elements
        if element["element_type"] == MODEL_ELEMENT_TYPE_ENERGY_STORAGE and element["name"] == "test_battery"
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


def test_discharge_respects_power_limit_with_efficiency() -> None:
    """Battery discharge respects power limit even with efficiency in segment chain.

    With 5kW discharge limit and 90% efficiency configured:
    - Battery discharge must never exceed 5kW
    - Efficiency reduces power delivered to grid

    Verifies power_limit and efficiency segments interact correctly - power limit
    is enforced regardless of efficiency losses in the chain.
    """
    max_discharge_kw = 5.0
    efficiency = 0.9

    network = Network(name="test", periods=np.array([1.0]))

    # Battery with plenty of capacity to discharge at max for one period
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_ENERGY_STORAGE,
            "name": "battery",
            "capacity": np.array([20.0, 20.0]),
            "initial_charge": 15.0,  # Plenty to discharge at 5kW for 1 hour
        }
    )

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})

    # Discharge connection: battery -> grid
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid:discharge",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([max_discharge_kw])},
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([efficiency])},
                "pricing": {"segment_type": "pricing", "price": np.array([-0.50])},
            },
        }
    )
    # Charge connection: grid -> battery
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid:charge",
            "source": "grid",
            "target": "battery",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([5.0])},
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([efficiency])},
                "pricing": {"segment_type": "pricing", "price": np.array([0.10])},
            },
        }
    )

    network.optimize()

    # Verify battery discharge respects power limit
    battery_discharge = network.elements["battery"].outputs()[BATTERY_POWER_DISCHARGE].values[0]
    assert battery_discharge <= max_discharge_kw + 0.001, (
        f"Battery discharge {battery_discharge:.3f}kW exceeds {max_discharge_kw}kW limit"
    )
    # Should discharge at max since it's profitable
    assert battery_discharge >= max_discharge_kw - 0.001, (
        f"Expected max discharge {max_discharge_kw}kW, got {battery_discharge:.3f}kW"
    )


def test_charge_respects_power_limit_with_efficiency() -> None:
    """Battery charge respects power limit even with efficiency in segment chain.

    With 3kW charge limit and 90% efficiency configured:
    - Battery charge must never exceed 3kW
    - Efficiency means grid provides more power than battery stores

    Verifies power_limit and efficiency segments interact correctly.
    """
    max_charge_kw = 3.0
    efficiency = 0.9

    network = Network(name="test", periods=np.array([1.0]))

    # Battery with plenty of headroom to charge at max
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_ENERGY_STORAGE,
            "name": "battery",
            "capacity": np.array([20.0, 20.0]),
            "initial_charge": 2.0,  # Low charge, plenty of room to accept 3kW for 1 hour
        }
    )

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})

    # Discharge connection: battery -> grid
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid:discharge",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([5.0])},
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([efficiency])},
                "pricing": {"segment_type": "pricing", "price": np.array([0.50])},
            },
        }
    )
    # Charge connection: grid -> battery
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid:charge",
            "source": "grid",
            "target": "battery",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([max_charge_kw])},
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([efficiency])},
                "pricing": {"segment_type": "pricing", "price": np.array([-0.10])},
            },
        }
    )

    network.optimize()

    # Verify battery charge respects power limit
    battery_charge = network.elements["battery"].outputs()[BATTERY_POWER_CHARGE].values[0]
    assert battery_charge <= max_charge_kw + 0.001, (
        f"Battery charge {battery_charge:.3f}kW exceeds {max_charge_kw}kW limit"
    )
    # Should charge since it's profitable (exact amount depends on efficiency interaction)
    assert battery_charge > 0, "Expected battery to charge since it's profitable"
