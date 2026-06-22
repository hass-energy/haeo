"""Tests for battery adapter config handling and model elements."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant
import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.battery import BATTERY_DEVICE_BATTERY, BATTERY_POWER_ACTIVE
from custom_components.haeo.core.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    ModelElementConfig,
)
from custom_components.haeo.core.model.elements.battery import BATTERY_POWER_CHARGE, BATTERY_POWER_DISCHARGE
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.elements.segments import is_efficiency_spec
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import battery
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
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
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
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
            "tags": {1},
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
            "tags": {1},
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
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
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
            "tags": {1},
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
            "tags": {1},
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


# ---------------------------------------------------------------------------
# Sensor-output side selection (electrochemical vs bus)
# ---------------------------------------------------------------------------
#
# The battery adapter exposes three power sensors with intentionally
# different sides of the post-efficiency boundary:
#
#   * ``BATTERY_POWER_DISCHARGE`` — electrochemical (battery-cell) draw rate
#   * ``BATTERY_POWER_CHARGE``    — electrochemical (battery-cell) refill rate
#   * ``BATTERY_POWER_ACTIVE``    — bus-side net flow, signed
#                                   (positive = battery exporting to bus)
#
# This split matches the OEM hybrid-inverter sensor convention
# (Sungrow, SigEnergy, Victron) and is the follow-on to upstream PR #297,
# which placed ``power_limit`` on the post-efficiency side of the chain.
# Energy/SOC reconciliation needs the electrochemical figures; downstream
# integrations binding to ``max_active_power`` need the bus figure.
#
# The two helpers below build a network with the production adapter's
# segment order (``efficiency`` then ``power_limit``), so the LP exhibits
# the post-efficiency cap behaviour the sensors are designed to surface.


def _make_battery_config_for_adapter() -> BatteryConfigData:
    """Return a minimal BatteryConfigData accepted by ``BatteryAdapter.outputs``.

    Only the storage/efficiency/power_limits sections are exercised here;
    the rest are filled with no-op defaults so the outputs path does not
    raise on missing keys.
    """
    return BatteryConfigData(
        element_type="battery",
        name="battery",
        connection=as_connection_target("bus"),
        storage={
            "capacity": np.array([100.0, 100.0]),
            "initial_charge_percentage": as_constant_value(0.5),
        },
        limits={
            "min_charge_percentage": np.array([0.0]),
            "max_charge_percentage": np.array([1.0]),
        },
        power_limits={
            "max_power_source_target": np.array([10.0]),
            "max_power_target_source": np.array([10.0]),
        },
        pricing={"salvage_value": as_constant_value(0.0)},
        efficiency={
            "efficiency_source_target": np.array([0.9]),
            "efficiency_target_source": np.array([0.9]),
        },
        partitioning={},
        undercharge={},
        overcharge={},
    )


def _build_battery_bus_network(
    *,
    efficiency: float,
    discharge_cap_kw: float,
    charge_cap_kw: float,
    discharge_price: float,
    charge_price: float,
) -> Network:
    """Build a single-period battery↔bus network using the production segment order.

    Discharge connection: battery → bus, segments = [efficiency, power_limit, pricing]
        ⇒ power_limit caps the bus-side (post-efficiency) flow.
    Charge connection:    bus → battery, segments = [power_limit, efficiency, pricing]
        ⇒ power_limit caps the bus-side (pre-efficiency, source-end) flow.

    Both directions cap on the bus side, matching how OEM hybrid-inverter
    control surfaces (SigEnergy ``max_charging_limit``, Sungrow charging
    power limit, etc.) are specified, and aligned with PR #297's intent.

    Battery is sized large (100 kWh, 50% SOC) so the binding constraint in
    the resulting LP is the connection power_limit, not the stored-energy
    headroom.
    """
    network = Network(name="test_efficiency_sensors", periods=np.array([1.0]))
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": np.array([100.0, 100.0]),
            "initial_charge": 50.0,
        }
    )
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "bus", "is_source": True, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery:discharge",
            "source": "battery",
            "target": "bus",
            "tags": {1},
            "segments": {
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([efficiency])},
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([discharge_cap_kw])},
                "pricing": {"segment_type": "pricing", "price": np.array([discharge_price])},
            },
        }
    )
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery:charge",
            "source": "bus",
            "target": "battery",
            "tags": {1},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([charge_cap_kw])},
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([efficiency])},
                "pricing": {"segment_type": "pricing", "price": np.array([charge_price])},
            },
        }
    )
    return network


def _collect_model_outputs(network: Network) -> dict[str, dict[str, object]]:
    """Snapshot per-element outputs after ``network.optimize`` has run."""
    return {name: dict(element.outputs()) for name, element in network.elements.items()}


def test_sensors_report_correct_sides_on_discharge() -> None:
    """During pure discharge the three sensors should each report their declared side.

    With η=0.9 and a 10 kW post-efficiency cap on the discharge connection:

    * ``BATTERY_POWER_DISCHARGE`` reads the electrochemical-side flow
      (source-end of the discharge connection, pre-efficiency).
    * ``BATTERY_POWER_CHARGE`` is zero (no charge happening).
    * ``BATTERY_POWER_ACTIVE`` reads the bus-side net flow (post-efficiency)
      and is positive (discharging).
    """
    efficiency = 0.9
    cap_kw = 10.0

    network = _build_battery_bus_network(
        efficiency=efficiency,
        discharge_cap_kw=cap_kw,
        charge_cap_kw=cap_kw,
        discharge_price=-1.0,  # exporting to bus is profitable
        charge_price=100.0,  # charging is heavily penalised
    )
    network.optimize()

    sensors = battery_adapter.outputs(
        "battery", _collect_model_outputs(network), config=_make_battery_config_for_adapter()
    )[BATTERY_DEVICE_BATTERY]

    discharge_conn = network.elements["battery:discharge"]
    source_end_electro = discharge_conn.extract_values(discharge_conn.total_power_in)[0]
    target_end_bus = discharge_conn.extract_values(discharge_conn.total_power_out)[0]

    # Electrochemical-side draw matches the connection's source-end (pre-efficiency)
    assert sensors[BATTERY_POWER_DISCHARGE].values[0] == pytest.approx(source_end_electro)
    # No charging happening
    assert sensors[BATTERY_POWER_CHARGE].values[0] == pytest.approx(0.0)
    # Bus-side active matches the connection's target-end (post-efficiency)
    assert sensors[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(target_end_bus)
    # And bus-side is strictly less than electrochemical-side because of η=0.9 loss
    assert sensors[BATTERY_POWER_ACTIVE].values[0] < sensors[BATTERY_POWER_DISCHARGE].values[0]
    assert sensors[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(
        sensors[BATTERY_POWER_DISCHARGE].values[0] * efficiency
    )


def test_sensors_report_correct_sides_on_charge() -> None:
    """During pure charge the three sensors should each report their declared side.

    With η=0.9 on the charge connection:

    * ``BATTERY_POWER_DISCHARGE`` is zero (no discharge happening).
    * ``BATTERY_POWER_CHARGE`` reads the electrochemical-side flow
      (target-end of the charge connection, post-efficiency = battery cells).
    * ``BATTERY_POWER_ACTIVE`` reads the bus-side net flow (source-end of
      the charge connection, pre-efficiency) and is negative (charging).
    """
    efficiency = 0.9
    cap_kw = 10.0

    network = _build_battery_bus_network(
        efficiency=efficiency,
        discharge_cap_kw=cap_kw,
        charge_cap_kw=cap_kw,
        discharge_price=100.0,  # discharging is heavily penalised
        charge_price=-1.0,  # importing from bus is profitable
    )
    network.optimize()

    sensors = battery_adapter.outputs(
        "battery", _collect_model_outputs(network), config=_make_battery_config_for_adapter()
    )[BATTERY_DEVICE_BATTERY]

    charge_conn = network.elements["battery:charge"]
    source_end_bus = charge_conn.extract_values(charge_conn.total_power_in)[0]
    target_end_electro = charge_conn.extract_values(charge_conn.total_power_out)[0]

    assert sensors[BATTERY_POWER_DISCHARGE].values[0] == pytest.approx(0.0)
    # Electrochemical-side refill matches the charge connection's target-end (post-efficiency)
    assert sensors[BATTERY_POWER_CHARGE].values[0] == pytest.approx(target_end_electro)
    # Active is bus-side and negative (charging) — equals -source-end of charge connection
    assert sensors[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(-source_end_bus)
    assert sensors[BATTERY_POWER_ACTIVE].values[0] < 0.0
    # Bus-side magnitude is strictly greater than electrochemical-side because of η=0.9 loss
    assert abs(sensors[BATTERY_POWER_ACTIVE].values[0]) > sensors[BATTERY_POWER_CHARGE].values[0]
    assert abs(sensors[BATTERY_POWER_ACTIVE].values[0]) == pytest.approx(
        sensors[BATTERY_POWER_CHARGE].values[0] / efficiency
    )


def test_sensor_sides_with_no_efficiency_loss() -> None:
    """With η=1.0, electrochemical and bus sides coincide.

    All three sensors agree on magnitude regardless of direction.
    """
    efficiency = 1.0
    cap_kw = 10.0

    # Discharge case
    network = _build_battery_bus_network(
        efficiency=efficiency,
        discharge_cap_kw=cap_kw,
        charge_cap_kw=cap_kw,
        discharge_price=-1.0,
        charge_price=100.0,
    )
    network.optimize()
    sensors = battery_adapter.outputs(
        "battery", _collect_model_outputs(network), config=_make_battery_config_for_adapter()
    )[BATTERY_DEVICE_BATTERY]
    assert sensors[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(sensors[BATTERY_POWER_DISCHARGE].values[0])

    # Charge case
    network = _build_battery_bus_network(
        efficiency=efficiency,
        discharge_cap_kw=cap_kw,
        charge_cap_kw=cap_kw,
        discharge_price=100.0,
        charge_price=-1.0,
    )
    network.optimize()
    sensors = battery_adapter.outputs(
        "battery", _collect_model_outputs(network), config=_make_battery_config_for_adapter()
    )[BATTERY_DEVICE_BATTERY]
    assert sensors[BATTERY_POWER_ACTIVE].values[0] == pytest.approx(-sensors[BATTERY_POWER_CHARGE].values[0])


# ---------------------------------------------------------------------------
# Adapter-level cap-side regression (issue #478 follow-on)
# ---------------------------------------------------------------------------
#
# Prior to the segment-order fix, the charge connection used
# [efficiency, power_limit] which placed ``max_power_target_source`` on
# the electrochemical (cell, target-end) side. With η<1 this caused the
# bus-side draw to exceed the OEM-declared charging-power limit by a
# factor of 1/η — e.g. a 21 kW cap on a 90%-efficient battery produced
# ~23.3 kW of AC draw, contradicting the OEM ``max_charging_limit``
# semantics on SigEnergy, Sungrow, and Victron hybrid inverters.
#
# The adapter now emits charge segments as [power_limit, efficiency] so
# the cap binds the bus (source-end) flow, mirroring the discharge
# connection where [efficiency, power_limit] also binds the bus
# (target-end) per PR #297. Both directions are now bus-side-capped.


def test_adapter_charge_cap_binds_bus_side() -> None:
    """Charge cap from the adapter binds the bus (source-end), not cells.

    Builds the production adapter for a battery with η=0.9 and a 10 kW
    charge cap, then optimises a network where charging is heavily
    profitable. Expects bus draw at exactly the cap, cells at cap x η.
    """
    efficiency = 0.9
    charge_cap_kw = 10.0

    config = BatteryConfigData(
        element_type="battery",
        name="battery",
        connection=as_connection_target("bus"),
        storage={
            "capacity": np.array([100.0, 100.0]),
            "initial_charge_percentage": 0.5,
        },
        limits={
            "min_charge_percentage": np.array([0.0]),
            "max_charge_percentage": np.array([1.0]),
        },
        power_limits={
            "max_power_source_target": np.array([charge_cap_kw]),
            "max_power_target_source": np.array([charge_cap_kw]),
        },
        pricing={"salvage_value": 0.0},
        efficiency={
            "efficiency_source_target": np.array([efficiency]),
            "efficiency_target_source": np.array([efficiency]),
        },
        partitioning={},
        undercharge={},
        overcharge={},
    )

    elements = battery_adapter.model_elements(config)

    # The production pipeline normally tags connections in a separate policy
    # compilation step (see ``adapters/policy_compilation.py``). For this
    # adapter-only unit test, assign a single shared tag and inject a
    # pricing segment into the charge connection BEFORE it's added to the
    # network, so charging is heavily profitable and the LP drives the
    # charge connection all the way to its cap. Preserves the adapter's
    # production segment order (power_limit before efficiency).
    for element in elements:
        if element.get("element_type") == MODEL_ELEMENT_TYPE_CONNECTION:
            element["tags"] = {1}
        if element.get("name") == "battery:charge":
            element["segments"]["pricing"] = {
                "segment_type": "pricing",
                "price": np.array([-1.0]),
            }
        if element.get("name") == "battery:discharge":
            # Heavily penalise discharging so the LP doesn't cycle.
            element["segments"]["pricing"] = {
                "segment_type": "pricing",
                "price": np.array([100.0]),
            }

    network = Network(name="test_charge_cap_bus_side", periods=np.array([1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "bus", "is_source": True, "is_sink": True})
    for element in elements:
        network.add(element)

    network.optimize()

    sensors = battery_adapter.outputs("battery", _collect_model_outputs(network), config=config)[BATTERY_DEVICE_BATTERY]

    bus_draw = abs(sensors[BATTERY_POWER_ACTIVE].values[0])
    cell_intake = sensors[BATTERY_POWER_CHARGE].values[0]

    # Bus-side AC draw is capped at the OEM-declared limit.
    assert bus_draw == pytest.approx(charge_cap_kw, abs=1e-3), (
        f"Bus draw {bus_draw:.3f} kW should equal cap {charge_cap_kw} kW (was the bug)"
    )
    # Cell-side intake is cap x efficiency, not cap.
    assert cell_intake == pytest.approx(charge_cap_kw * efficiency, abs=1e-3), (
        f"Cell intake {cell_intake:.3f} kW should equal cap x η = {charge_cap_kw * efficiency} kW"
    )
