"""Tests for battery adapter config handling and model elements."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.elements import battery
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_CONNECTION, ModelElementConfig
from custom_components.haeo.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.model.elements.segments import is_efficiency_spec


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


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Battery available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        "max_charge_power": "sensor.max_charge",
        "max_discharge_power": "sensor.max_discharge",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_required_power_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required power sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    # max_discharge_power sensor is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        "max_charge_power": "sensor.max_charge",
        "max_discharge_power": "sensor.missing",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_capacity_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when capacity sensor is missing."""
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    # capacity sensor is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.missing_capacity",
        "initial_charge_percentage": "sensor.initial",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_required_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")
    # initial_charge_percentage sensor is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.missing",
        "max_charge_power": "sensor.max_charge",
        "max_discharge_power": "sensor.max_discharge",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_with_list_entity_ids_all_exist(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] entity IDs all exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.discharge_cost_1", "0.05", "$/kWh")
    _set_sensor(hass, "sensor.discharge_cost_2", "0.06", "$/kWh")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        # List of entity IDs for chained forecasts
        "discharge_cost": ["sensor.discharge_cost_1", "sensor.discharge_cost_2"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is True


async def test_available_with_list_entity_ids_one_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when list[str] entity ID has one missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.discharge_cost_1", "0.05", "$/kWh")
    # sensor.discharge_cost_2 is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        # List of entity IDs where one is missing
        "discharge_cost": ["sensor.discharge_cost_1", "sensor.missing"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_with_empty_list_returns_true(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] is empty."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    # This tests the `if value else True` branch for empty lists
    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        "discharge_cost": [],  # Empty list
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is True


def test_model_elements_omits_efficiency_when_missing() -> None:
    """model_elements() should leave efficiency to model defaults when missing."""
    config_data: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([0.5, 0.5]),
    }

    elements = battery.adapter.model_elements(config_data)

    battery_element = next(element for element in elements if element["element_type"] == MODEL_ELEMENT_TYPE_BATTERY and element["name"] == "test_battery")
    np.testing.assert_array_equal(battery_element["capacity"], [10.0, 10.0, 10.0])

    connection = _get_connection(elements, "test_battery:connection")
    segments = connection.get("segments")
    assert segments is not None
    efficiency_segment = segments.get("efficiency")
    assert efficiency_segment is not None
    assert is_efficiency_spec(efficiency_segment)
    assert efficiency_segment.get("efficiency_source_target") is None
    assert efficiency_segment.get("efficiency_target_source") is None


def test_model_elements_passes_efficiency_when_present() -> None:
    """model_elements() should pass through provided efficiency values."""
    config_data: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([0.5, 0.5]),
        "efficiency": np.array([0.95, 0.95]),
    }

    elements = battery.adapter.model_elements(config_data)

    connection = _get_connection(elements, "test_battery:connection")
    segments = connection.get("segments")
    assert segments is not None
    efficiency_segment = segments.get("efficiency")
    assert efficiency_segment is not None
    assert is_efficiency_spec(efficiency_segment)
    efficiency_source_target = efficiency_segment.get("efficiency_source_target")
    assert efficiency_source_target is not None
    np.testing.assert_array_equal(efficiency_source_target, [0.95, 0.95])
    efficiency_target_source = efficiency_segment.get("efficiency_target_source")
    assert efficiency_target_source is not None
    np.testing.assert_array_equal(efficiency_target_source, [0.95, 0.95])


def test_model_elements_overcharge_only_adds_soc_pricing() -> None:
    """SOC pricing is added when only overcharge inputs are configured."""
    config_data: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([0.5, 0.5]),
        "min_charge_percentage": np.array([0.1, 0.1, 0.1]),
        "max_charge_percentage": np.array([0.9, 0.9, 0.9]),
        "overcharge_percentage": np.array([0.95, 0.95, 0.95]),
        "overcharge_cost": np.array([0.2, 0.2]),
    }

    elements = battery.adapter.model_elements(config_data)
    connection = _get_connection(elements, "test_battery:connection")
    segments = connection.get("segments")
    assert segments is not None
    soc_pricing = segments.get("soc_pricing")
    assert soc_pricing is not None
    assert soc_pricing.get("discharge_energy_threshold") is None
    assert soc_pricing.get("charge_capacity_threshold") is not None


def test_discharge_respects_power_limit_with_efficiency() -> None:
    """Battery discharge respects power limit even with efficiency in segment chain.

    With 5kW discharge limit and 90% efficiency configured:
    - Battery discharge must never exceed 5kW
    - Efficiency reduces power delivered to grid

    Verifies power_limit and efficiency segments interact correctly - power limit
    is enforced regardless of efficiency losses in the chain.
    """
    from custom_components.haeo.model import Network
    from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_NODE
    from custom_components.haeo.model.elements.battery import BATTERY_POWER_DISCHARGE

    max_discharge_kw = 5.0
    efficiency = 0.9

    network = Network(name="test", periods=np.array([1.0]))

    # Battery with plenty of capacity to discharge at max for one period
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": np.array([20.0, 20.0]),
            "initial_charge": 15.0,  # Plenty to discharge at 5kW for 1 hour
        }
    )

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})

    # Connection with power limit, efficiency, and pricing
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([max_discharge_kw]),
                    "max_power_target_source": np.array([5.0]),
                },
                "efficiency": {
                    "segment_type": "efficiency",
                    "efficiency_source_target": np.array([efficiency]),
                    "efficiency_target_source": np.array([efficiency]),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([-0.50]),  # Discharge pays
                    "price_target_source": np.array([0.10]),
                },
            },
        }
    )

    network.optimize()

    # Verify battery discharge respects power limit
    battery_discharge = network.elements["battery"].outputs()[BATTERY_POWER_DISCHARGE].values[0]
    assert battery_discharge <= max_discharge_kw + 0.001, f"Battery discharge {battery_discharge:.3f}kW exceeds {max_discharge_kw}kW limit"
    # Should discharge at max since it's profitable
    assert battery_discharge >= max_discharge_kw - 0.001, f"Expected max discharge {max_discharge_kw}kW, got {battery_discharge:.3f}kW"


def test_charge_respects_power_limit_with_efficiency() -> None:
    """Battery charge respects power limit even with efficiency in segment chain.

    With 3kW charge limit and 90% efficiency configured:
    - Battery charge must never exceed 3kW
    - Efficiency means grid provides more power than battery stores

    Verifies power_limit and efficiency segments interact correctly.
    """
    from custom_components.haeo.model import Network
    from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_NODE
    from custom_components.haeo.model.elements.battery import BATTERY_POWER_CHARGE

    max_charge_kw = 3.0
    efficiency = 0.9

    network = Network(name="test", periods=np.array([1.0]))

    # Battery with plenty of headroom to charge at max
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": np.array([20.0, 20.0]),
            "initial_charge": 2.0,  # Low charge, plenty of room to accept 3kW for 1 hour
        }
    )

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})

    # Connection with power limit, efficiency, and pricing
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([5.0]),
                    "max_power_target_source": np.array([max_charge_kw]),
                },
                "efficiency": {
                    "segment_type": "efficiency",
                    "efficiency_source_target": np.array([efficiency]),
                    "efficiency_target_source": np.array([efficiency]),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.50]),  # Discharge costs
                    "price_target_source": np.array([-0.10]),  # Charging pays
                },
            },
        }
    )

    network.optimize()

    # Verify battery charge respects power limit
    battery_charge = network.elements["battery"].outputs()[BATTERY_POWER_CHARGE].values[0]
    assert battery_charge <= max_charge_kw + 0.001, f"Battery charge {battery_charge:.3f}kW exceeds {max_charge_kw}kW limit"
    # Should charge since it's profitable (exact amount depends on efficiency interaction)
    assert battery_charge > 0, "Expected battery to charge since it's profitable"
