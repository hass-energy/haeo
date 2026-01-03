"""Tests for HAEO diagnostics utilities."""

from datetime import UTC, datetime
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.coordinator import CoordinatorOutput, ForecastPoint, HaeoDataUpdateCoordinator
from custom_components.haeo.diagnostics import async_get_config_entry_diagnostics
from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
)
from custom_components.haeo.elements.grid import CONF_IMPORT_PRICE, GRID_POWER_IMPORT
from custom_components.haeo.elements.solar import CONF_CURTAILMENT, CONF_FORECAST
from custom_components.haeo.entities.haeo_number import ConfigEntityMode, HaeoInputNumber
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.model import OutputType


async def test_diagnostics_basic_structure(hass: HomeAssistant) -> None:
    """Diagnostics returns correct structure with four main keys in the right order."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = None

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify the four main keys
    assert "config" in diagnostics
    assert "inputs" in diagnostics
    assert "outputs" in diagnostics
    assert "environment" in diagnostics

    # Note: Python dicts maintain insertion order, but JSON serialization
    # can use sort_keys=True for alphabetical ordering (config, environment, inputs, outputs)

    # Verify config structure
    assert diagnostics["config"][CONF_TIER_1_COUNT] == DEFAULT_TIER_1_COUNT
    assert diagnostics["config"][CONF_TIER_1_DURATION] == DEFAULT_TIER_1_DURATION
    assert "participants" in diagnostics["config"]

    # Verify environment
    assert "ha_version" in diagnostics["environment"]
    assert "haeo_version" in diagnostics["environment"]
    assert "timestamp" in diagnostics["environment"]
    assert "timezone" in diagnostics["environment"]


async def test_diagnostics_with_participants(hass: HomeAssistant) -> None:
    """Diagnostics includes participant configs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_NAME: "Battery One",
                CONF_CAPACITY: ["sensor.battery_capacity"],
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
                CONF_MIN_CHARGE_PERCENTAGE: 10.0,
                CONF_MAX_CHARGE_PERCENTAGE: 90.0,
                CONF_EFFICIENCY: 95.0,
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery One",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Set up sensor states that should be captured
    hass.states.async_set(
        "sensor.battery_capacity",
        "5000",
        {
            "unit_of_measurement": "Wh",
            "device_class": "energy",
        },
    )
    hass.states.async_set(
        "sensor.battery_soc",
        "75",
        {
            "unit_of_measurement": "%",
            "device_class": "battery",
        },
    )

    entry.runtime_data = None

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify config has participants
    participants = diagnostics["config"]["participants"]
    assert "Battery One" in participants
    battery_config = participants["Battery One"]
    assert battery_config[CONF_ELEMENT_TYPE] == ELEMENT_TYPE_BATTERY
    assert battery_config[CONF_NAME] == "Battery One"
    assert battery_config[CONF_CAPACITY] == ["sensor.battery_capacity"]
    assert battery_config[CONF_INITIAL_CHARGE_PERCENTAGE] == ["sensor.battery_soc"]

    # Verify input states are collected using State.as_dict()
    # Both sensor.battery_capacity and sensor.battery_soc should be collected
    inputs = diagnostics["inputs"]
    assert len(inputs) == 2
    entity_ids = [inp["entity_id"] for inp in inputs]
    assert "sensor.battery_capacity" in entity_ids
    assert "sensor.battery_soc" in entity_ids
    # Verify structure of input states
    for inp in inputs:
        assert "attributes" in inp
        assert "last_updated" in inp

    # Verify outputs is empty dict when no coordinator
    assert diagnostics["outputs"] == {}


async def test_diagnostics_skips_network_subentry(hass: HomeAssistant) -> None:
    """Diagnostics skips network subentries when collecting participants and inputs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a network subentry (should be skipped)
    network_subentry = ConfigSubentry(
        data=MappingProxyType({"some_network_config": "value"}),
        subentry_type="network",
        title="Network Config",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, network_subentry)

    # Add a battery subentry (should be included)
    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_NAME: "Battery",
                CONF_CAPACITY: ["sensor.battery_capacity"],
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
                CONF_MIN_CHARGE_PERCENTAGE: 10.0,
                CONF_MAX_CHARGE_PERCENTAGE: 90.0,
                CONF_EFFICIENCY: 95.0,
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Set up sensor states
    hass.states.async_set("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})
    hass.states.async_set("sensor.battery_soc", "75", {"unit_of_measurement": "%"})

    entry.runtime_data = None

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify network subentry is NOT in participants
    participants = diagnostics["config"]["participants"]
    assert "Network Config" not in participants
    assert "Battery" in participants

    # Verify inputs only include battery sensors (network subentry didn't add any)
    inputs = diagnostics["inputs"]
    entity_ids = [inp["entity_id"] for inp in inputs]
    assert "sensor.battery_capacity" in entity_ids
    assert "sensor.battery_soc" in entity_ids


async def test_diagnostics_with_outputs(hass: HomeAssistant) -> None:
    """Diagnostics includes output sensor states when coordinator available."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    grid_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: "grid",
                CONF_NAME: "Grid",
                CONF_IMPORT_PRICE: ["sensor.grid_import_price"],
            }
        ),
        subentry_type="grid",
        title="Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, grid_subentry)

    # Set up input sensor states
    hass.states.async_set(
        "sensor.grid_import_price",
        "0.25",
        {
            "unit_of_measurement": "$/kWh",
        },
    )

    # Create a mock coordinator with outputs
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = {
        "grid": {
            GRID_POWER_IMPORT: CoordinatorOutput(
                type=OutputType.POWER,
                unit="kW",
                state=5.5,
                forecast=[ForecastPoint(time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC), value=5.5)],
            )
        }
    }

    # Register output sensor in entity registry (required for get_output_sensors)
    entity_registry = er.async_get(hass)
    output_entity_id = f"sensor.{DOMAIN}_hub_entry_{grid_subentry.subentry_id}_{GRID_POWER_IMPORT}"
    entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"hub_entry_{grid_subentry.subentry_id}_{GRID_POWER_IMPORT}",
        config_entry=entry,
    )

    # Set up output sensor state
    hass.states.async_set(
        output_entity_id,
        "5.5",
        {
            "unit_of_measurement": "kW",
            "element_name": "Grid",
        },
    )

    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify outputs are collected as dict
    outputs = diagnostics["outputs"]
    assert len(outputs) >= 1
    # Find the entity by checking entity_id in values
    output_entity = next(
        (s for s in outputs.values() if GRID_POWER_IMPORT in s["entity_id"]),
        None,
    )
    assert output_entity is not None
    assert output_entity["state"] == "5.5"


async def test_diagnostics_captures_editable_input_number_values(hass: HomeAssistant) -> None:
    """Diagnostics captures current values from editable input number entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a battery subentry with configurable values
    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_NAME: "Battery",
                CONF_CAPACITY: 10.0,  # Constant value (editable)
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,  # Constant value (editable)
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Create mock input entities
    mock_capacity_entity = Mock(spec=HaeoInputNumber)
    mock_capacity_entity.entity_mode = ConfigEntityMode.EDITABLE
    mock_capacity_entity.native_value = 15.0  # Updated value

    mock_soc_entity = Mock(spec=HaeoInputNumber)
    mock_soc_entity.entity_mode = ConfigEntityMode.EDITABLE
    mock_soc_entity.native_value = 75.0  # Updated value

    # Create mock horizon manager
    mock_horizon_manager = Mock(spec=HorizonManager)

    # Create real HaeoRuntimeData with mock input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=mock_horizon_manager,
        input_entities={
            ("Battery", CONF_CAPACITY): mock_capacity_entity,
            ("Battery", CONF_INITIAL_CHARGE_PERCENTAGE): mock_soc_entity,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify the captured values are in the participant config
    participants = diagnostics["config"]["participants"]
    battery_config = participants["Battery"]
    assert battery_config[CONF_CAPACITY] == 15.0
    assert battery_config[CONF_INITIAL_CHARGE_PERCENTAGE] == 75.0


async def test_diagnostics_captures_editable_input_switch_values(hass: HomeAssistant) -> None:
    """Diagnostics captures current values from editable input switch entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a solar subentry with curtailment switch
    solar_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: "solar",
                CONF_NAME: "Solar",
                CONF_FORECAST: ["sensor.solar_forecast"],
                CONF_CONNECTION: "AC Bus",
                CONF_CURTAILMENT: True,  # Default value
            }
        ),
        subentry_type="solar",
        title="Solar",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, solar_subentry)

    # Create mock input switch entity
    mock_switch_entity = Mock(spec=HaeoInputSwitch)
    mock_switch_entity.entity_mode = ConfigEntityMode.EDITABLE
    mock_switch_entity.is_on = False  # Updated value

    # Create mock horizon manager
    mock_horizon_manager = Mock(spec=HorizonManager)

    # Create real HaeoRuntimeData with mock input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=mock_horizon_manager,
        input_entities={
            ("Solar", CONF_CURTAILMENT): mock_switch_entity,
        },
    )
    entry.runtime_data = runtime_data

    # Set up sensor state for forecast
    hass.states.async_set("sensor.solar_forecast", "5.0", {"unit_of_measurement": "kW"})

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify the captured switch value is in the participant config
    participants = diagnostics["config"]["participants"]
    solar_config = participants["Solar"]
    assert solar_config[CONF_CURTAILMENT] is False


async def test_diagnostics_skips_non_editable_entities(hass: HomeAssistant) -> None:
    """Diagnostics skips entities that are not in EDITABLE mode."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a battery subentry with sensor-driven values
    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_NAME: "Battery",
                CONF_CAPACITY: ["sensor.battery_capacity"],  # Sensor-driven
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],  # Sensor-driven
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Create mock input entity in DRIVEN mode
    mock_capacity_entity = Mock(spec=HaeoInputNumber)
    mock_capacity_entity.entity_mode = ConfigEntityMode.DRIVEN
    mock_capacity_entity.native_value = 15.0

    # Create mock horizon manager
    mock_horizon_manager = Mock(spec=HorizonManager)

    # Create real HaeoRuntimeData with mock input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=mock_horizon_manager,
        input_entities={
            ("Battery", CONF_CAPACITY): mock_capacity_entity,
        },
    )
    entry.runtime_data = runtime_data

    # Set up sensor states
    hass.states.async_set("sensor.battery_capacity", "10.0", {"unit_of_measurement": "kWh"})
    hass.states.async_set("sensor.battery_soc", "50", {"unit_of_measurement": "%"})

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify the original sensor-driven config is preserved (not overwritten)
    participants = diagnostics["config"]["participants"]
    battery_config = participants["Battery"]
    assert battery_config[CONF_CAPACITY] == ["sensor.battery_capacity"]
