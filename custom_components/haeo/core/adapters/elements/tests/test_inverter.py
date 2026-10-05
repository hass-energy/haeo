"""Tests for inverter adapter availability checks and power limits."""

from collections.abc import Mapping

from homeassistant.core import HomeAssistant
import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.battery import (
    BATTERY_DEVICE_BATTERY,
    BATTERY_POWER_CHARGE,
    BATTERY_POWER_DISCHARGE,
    BatteryOutputName,
)
from custom_components.haeo.core.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.core.adapters.elements.inverter import (
    INVERTER_DEVICE_INVERTER,
    INVERTER_POWER_AC_TO_DC,
    INVERTER_POWER_ACTIVE,
    INVERTER_POWER_DC_TO_AC,
    InverterOutputName,
)
from custom_components.haeo.core.adapters.elements.inverter import adapter as inverter_adapter
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType, inverter
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.inverter import InverterConfigData
from custom_components.haeo.core.schema.elements.node import NodeConfigData
from custom_components.haeo.elements.availability import schema_config_available

from .conftest import optimize_participants


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Inverter available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")

    config: inverter.InverterConfigSchema = {
        "element_type": ElementType.INVERTER,
        "name": "test_inverter",
        "connection": as_connection_target("ac_bus"),
        inverter.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.max_dc_to_ac"]),
            "max_power_target_source": as_entity_value(["sensor.max_ac_to_dc"]),
        },
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_false_when_first_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_dc_to_ac sensor is missing."""
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")
    # max_power_dc_to_ac is missing

    config: inverter.InverterConfigSchema = {
        "element_type": ElementType.INVERTER,
        "name": "test_inverter",
        "connection": as_connection_target("ac_bus"),
        inverter.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.missing"]),
            "max_power_target_source": as_entity_value(["sensor.max_ac_to_dc"]),
        },
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_false_when_second_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_ac_to_dc sensor is missing."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    # max_power_ac_to_dc sensor is missing

    config: inverter.InverterConfigSchema = {
        "element_type": ElementType.INVERTER,
        "name": "test_inverter",
        "connection": as_connection_target("ac_bus"),
        inverter.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.max_dc_to_ac"]),
            "max_power_target_source": as_entity_value(["sensor.missing"]),
        },
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_true_when_limits_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return True when limits are omitted."""
    config: inverter.InverterConfigSchema = {
        "element_type": ElementType.INVERTER,
        "name": "test_inverter",
        "connection": as_connection_target("ac_bus"),
        inverter.SECTION_POWER_LIMITS: {},
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


def _optimize_hybrid_system(
    *, efficiency: float, cap: float, salvage_value: float, export_price: float
) -> tuple[Mapping[InverterOutputName, OutputData], Mapping[BatteryOutputName, OutputData]]:
    """Optimize a lossless battery on an inverter's DC bus with a grid on the AC bus.

    Returns the inverter and battery sensor outputs.
    """
    inverter_config = InverterConfigData(
        element_type=ElementType.INVERTER,
        name="inverter",
        connection=as_connection_target("ac_bus"),
        power_limits={"max_power_source_target": np.array([cap]), "max_power_target_source": np.array([cap])},
        efficiency={
            "efficiency_source_target": np.array([efficiency]),
            "efficiency_target_source": np.array([efficiency]),
        },
    )
    battery_config = BatteryConfigData(
        element_type=ElementType.BATTERY,
        name="battery",
        connection=as_connection_target("inverter"),
        storage={"capacity": np.array([20.0, 20.0]), "initial_charge_percentage": 0.5},
        limits={},
        power_limits={},
        pricing={"salvage_value": salvage_value},
        efficiency={},
        partitioning={},
    )
    model_outputs = optimize_participants(
        {
            "ac_bus": NodeConfigData(
                element_type=ElementType.NODE, name="ac_bus", role={"is_source": False, "is_sink": False}
            ),
            "inverter": inverter_config,
            "battery": battery_config,
            "grid": GridConfigData(
                element_type=ElementType.GRID,
                name="grid",
                connection=as_connection_target("ac_bus"),
                pricing={"price_source_target": np.array([1.0]), "price_target_source": np.array([export_price])},
                power_limits={},
            ),
        }
    )
    return (
        inverter_adapter.outputs("inverter", model_outputs)[INVERTER_DEVICE_INVERTER],
        battery_adapter.outputs("battery", model_outputs, config=battery_config)[BATTERY_DEVICE_BATTERY],
    )


def test_dc_to_ac_cap_binds_ac_side() -> None:
    """The DC to AC limit caps AC output and the sensor reports the AC side.

    Exporting is profitable, so the inverter runs at its rating.
    The DC bus supplies rating / efficiency.
    """
    efficiency = 0.9
    cap = 5.0
    inverter_outputs, battery_outputs = _optimize_hybrid_system(
        efficiency=efficiency, cap=cap, salvage_value=0.0, export_price=0.5
    )

    dc_to_ac = inverter_outputs[INVERTER_POWER_DC_TO_AC].values[0]
    ac_to_dc = inverter_outputs[INVERTER_POWER_AC_TO_DC].values[0]
    assert dc_to_ac == pytest.approx(cap)
    assert ac_to_dc == pytest.approx(0.0)
    assert battery_outputs[BATTERY_POWER_DISCHARGE].values[0] == pytest.approx(cap / efficiency)
    assert inverter_outputs[INVERTER_POWER_ACTIVE].values[0] == pytest.approx(dc_to_ac - ac_to_dc)


def test_ac_to_dc_cap_binds_ac_side() -> None:
    """The AC to DC limit caps AC input and the sensor reports the AC side.

    Stored energy is worth more than it costs to import, so the inverter runs at its rating.
    The DC bus receives rating x efficiency.
    """
    efficiency = 0.9
    cap = 5.0
    inverter_outputs, battery_outputs = _optimize_hybrid_system(
        efficiency=efficiency, cap=cap, salvage_value=2.0, export_price=0.0
    )

    dc_to_ac = inverter_outputs[INVERTER_POWER_DC_TO_AC].values[0]
    ac_to_dc = inverter_outputs[INVERTER_POWER_AC_TO_DC].values[0]
    assert ac_to_dc == pytest.approx(cap)
    assert dc_to_ac == pytest.approx(0.0)
    assert battery_outputs[BATTERY_POWER_CHARGE].values[0] == pytest.approx(cap * efficiency)
    assert inverter_outputs[INVERTER_POWER_ACTIVE].values[0] == pytest.approx(dc_to_ac - ac_to_dc)
