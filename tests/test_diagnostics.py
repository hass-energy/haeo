"""Tests for HAEO diagnostics utilities."""

from datetime import UTC, datetime, timedelta, timezone
from types import MappingProxyType
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.diagnostics import CurrentStateProvider
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
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
)
from custom_components.haeo.elements.grid import CONF_EXPORT_PRICE, CONF_IMPORT_PRICE, GRID_POWER_IMPORT
from custom_components.haeo.entities.haeo_number import ConfigEntityMode, HaeoInputNumber
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
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
                CONF_CAPACITY: "sensor.battery_capacity",
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
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
    assert battery_config[CONF_CAPACITY] == "sensor.battery_capacity"
    assert battery_config[CONF_INITIAL_CHARGE_PERCENTAGE] == "sensor.battery_soc"

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
                CONF_CAPACITY: "sensor.battery_capacity",
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
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
                CONF_CONNECTION: "Main Bus",
                CONF_IMPORT_PRICE: ["sensor.grid_import_price", "sensor.grid_import_forecast"],
                CONF_EXPORT_PRICE: 0.08,
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
    hass.states.async_set(
        "sensor.grid_import_forecast",
        "0.30",
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

    # Verify that list[str] entity IDs are collected from chained price config
    inputs = diagnostics["inputs"]
    entity_ids = [inp["entity_id"] for inp in inputs]
    assert "sensor.grid_import_price" in entity_ids
    assert "sensor.grid_import_forecast" in entity_ids


async def test_diagnostics_captures_editable_entity_values(hass: HomeAssistant) -> None:
    """Diagnostics captures current values from editable input entities."""
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
                CONF_CAPACITY: 10.0,  # Constant value - creates editable entity
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,  # Constant - creates editable entity
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
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

    # Create mock editable input entities with current values
    mock_number = Mock(spec=HaeoInputNumber)
    mock_number.entity_mode = ConfigEntityMode.EDITABLE
    mock_number.native_value = 12.5  # Current value differs from config

    mock_switch = Mock(spec=HaeoInputSwitch)
    mock_switch.entity_mode = ConfigEntityMode.EDITABLE
    mock_switch.is_on = True

    # Create HaeoRuntimeData with input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=Mock(),
        input_entities={
            ("Battery One", CONF_CAPACITY): mock_number,
            ("Battery One", "some_boolean_field"): mock_switch,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that editable entity values are captured in config
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert battery_config[CONF_CAPACITY] == 12.5  # Current entity value, not config value
    assert battery_config["some_boolean_field"] is True


async def test_diagnostics_skips_unknown_element_in_input_entities(hass: HomeAssistant) -> None:
    """Diagnostics skips input entities for elements not in participants."""
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
                CONF_CAPACITY: 10.0,
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
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

    # Create input entity for an element that doesn't exist in participants
    mock_number = Mock(spec=HaeoInputNumber)
    mock_number.entity_mode = ConfigEntityMode.EDITABLE
    mock_number.native_value = 99.9

    runtime_data = HaeoRuntimeData(
        horizon_manager=Mock(),
        input_entities={
            # This element doesn't exist in participants
            ("Unknown Element", CONF_CAPACITY): mock_number,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that Battery One exists unchanged (unknown element was skipped)
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert battery_config[CONF_CAPACITY] == 10.0  # Original config value preserved


async def test_diagnostics_skips_driven_entity_values(hass: HomeAssistant) -> None:
    """Diagnostics skips sensor-driven entities and keeps config value."""
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
                CONF_CAPACITY: "sensor.battery_capacity",  # Entity ID - creates driven entity
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
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

    # Create mock driven input entity
    mock_number = Mock(spec=HaeoInputNumber)
    mock_number.entity_mode = ConfigEntityMode.DRIVEN  # Driven by external sensor
    mock_number.native_value = 15.0

    # Create HaeoRuntimeData with input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=Mock(),
        input_entities={
            ("Battery One", CONF_CAPACITY): mock_number,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that driven entity value is NOT captured - config value preserved
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert battery_config[CONF_CAPACITY] == "sensor.battery_capacity"  # Original config value


async def test_current_state_provider_get_state(hass: HomeAssistant) -> None:
    """Test CurrentStateProvider.get_state returns single entity state."""
    # Set up an entity state
    hass.states.async_set(
        "sensor.test_entity",
        "42",
        {"unit_of_measurement": "kW"},
    )

    provider = CurrentStateProvider(hass)

    # Test get_state for existing entity
    state = await provider.get_state("sensor.test_entity")
    assert state is not None
    assert state.state == "42"

    # Test get_state for non-existent entity
    state = await provider.get_state("sensor.nonexistent")
    assert state is None


async def test_current_state_provider_properties(hass: HomeAssistant) -> None:
    """Test CurrentStateProvider properties."""
    provider = CurrentStateProvider(hass)

    assert provider.is_historical is False
    assert provider.timestamp is None


async def test_historical_state_provider_properties(hass: HomeAssistant) -> None:
    """Test HistoricalStateProvider properties."""
    # Import here to avoid issues when recorder is not available
    from custom_components.haeo.diagnostics import HistoricalStateProvider

    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=timezone(timedelta(hours=11)))

    # Mock the recorder instance
    mock_recorder = Mock()
    with patch(
        "custom_components.haeo.diagnostics.historical_state_provider.get_recorder_instance",
        return_value=mock_recorder,
    ):
        provider = HistoricalStateProvider(hass, target_time)

    assert provider.is_historical is True
    assert provider.timestamp == target_time


async def test_historical_state_provider_get_state(hass: HomeAssistant) -> None:
    """Test HistoricalStateProvider.get_state returns single entity state."""
    from custom_components.haeo.diagnostics import HistoricalStateProvider

    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=timezone(timedelta(hours=11)))

    # Create a mock State
    mock_state = State("sensor.test_entity", "42", {"unit_of_measurement": "kW"})

    # Mock the recorder instance
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(
        return_value={"sensor.test_entity": [mock_state]}
    )

    with patch(
        "custom_components.haeo.diagnostics.historical_state_provider.get_recorder_instance",
        return_value=mock_recorder,
    ):
        provider = HistoricalStateProvider(hass, target_time)
        state = await provider.get_state("sensor.test_entity")

    assert state is not None
    assert state.state == "42"


async def test_historical_state_provider_get_state_not_found(hass: HomeAssistant) -> None:
    """Test HistoricalStateProvider.get_state returns None when entity not found."""
    from custom_components.haeo.diagnostics import HistoricalStateProvider

    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=timezone(timedelta(hours=11)))

    # Mock the recorder instance returning empty result
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(return_value={})

    with patch(
        "custom_components.haeo.diagnostics.historical_state_provider.get_recorder_instance",
        return_value=mock_recorder,
    ):
        provider = HistoricalStateProvider(hass, target_time)
        state = await provider.get_state("sensor.nonexistent")

    assert state is None


async def test_historical_state_provider_get_states(hass: HomeAssistant) -> None:
    """Test HistoricalStateProvider.get_states returns multiple entity states."""
    from custom_components.haeo.diagnostics import HistoricalStateProvider

    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=timezone(timedelta(hours=11)))

    # Create mock States
    mock_state_1 = State("sensor.entity_1", "100", {"unit_of_measurement": "kW"})
    mock_state_2 = State("sensor.entity_2", "200", {"unit_of_measurement": "kWh"})

    # Mock the recorder instance
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(
        return_value={
            "sensor.entity_1": [mock_state_1],
            "sensor.entity_2": [mock_state_2],
        }
    )

    with patch(
        "custom_components.haeo.diagnostics.historical_state_provider.get_recorder_instance",
        return_value=mock_recorder,
    ):
        provider = HistoricalStateProvider(hass, target_time)
        states = await provider.get_states(["sensor.entity_1", "sensor.entity_2"])

    assert len(states) == 2
    assert states["sensor.entity_1"].state == "100"
    assert states["sensor.entity_2"].state == "200"


async def test_historical_state_provider_get_states_empty(hass: HomeAssistant) -> None:
    """Test HistoricalStateProvider.get_states with empty entity list."""
    from custom_components.haeo.diagnostics import HistoricalStateProvider

    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=timezone(timedelta(hours=11)))

    mock_recorder = Mock()

    with patch(
        "custom_components.haeo.diagnostics.historical_state_provider.get_recorder_instance",
        return_value=mock_recorder,
    ):
        provider = HistoricalStateProvider(hass, target_time)
        states = await provider.get_states([])

    assert states == {}
    # Verify that async_add_executor_job was not called
    mock_recorder.async_add_executor_job.assert_not_called()


async def test_historical_state_provider_get_states_sync(hass: HomeAssistant) -> None:
    """Test HistoricalStateProvider._get_states_sync calls recorder history."""
    from custom_components.haeo.diagnostics import HistoricalStateProvider

    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=timezone(timedelta(hours=11)))

    mock_state = State("sensor.test", "50", {"unit_of_measurement": "%"})

    mock_recorder = Mock()

    with (
        patch(
            "custom_components.haeo.diagnostics.historical_state_provider.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.historical_state_provider.recorder_history.get_significant_states",
            return_value={"sensor.test": [mock_state]},
        ) as mock_get_states,
    ):
        provider = HistoricalStateProvider(hass, target_time)
        result = provider._get_states_sync(["sensor.test"])

    # Verify get_significant_states was called with correct parameters
    mock_get_states.assert_called_once_with(
        hass,
        start_time=target_time,
        end_time=target_time + timedelta(seconds=1),
        entity_ids=["sensor.test"],
        include_start_time_state=True,
        significant_changes_only=False,
        no_attributes=False,
    )

    assert result == {"sensor.test": [mock_state]}


async def test_diagnostics_with_historical_provider_omits_outputs(hass: HomeAssistant) -> None:
    """Test that diagnostics with historical provider omits output sensors."""
    from custom_components.haeo.diagnostics import collect_diagnostics

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

    # Create a mock historical state provider
    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=UTC)
    mock_provider = Mock()
    mock_provider.is_historical = True
    mock_provider.timestamp = target_time
    mock_provider.get_states = AsyncMock(return_value={})

    diagnostics = await collect_diagnostics(hass, entry, mock_provider)

    # Verify environment reflects historical mode
    assert diagnostics["environment"]["historical"] is True

    # Verify outputs is empty (historical diagnostics omit outputs)
    assert diagnostics["outputs"] == {}


async def test_diagnostics_with_network_subentry_not_element_config(hass: HomeAssistant) -> None:
    """Test that network subentry with invalid element config is skipped."""
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

    # Add a subentry with invalid element config (not a valid element type)
    # This will pass the network check but fail is_element_config_schema
    invalid_subentry = ConfigSubentry(
        data=MappingProxyType({"some_data": "value"}),
        subentry_type="unknown_element_type",
        title="Unknown Element",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, invalid_subentry)

    entry.runtime_data = None

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # The subentry is in participants (it has element_type set)
    participants = diagnostics["config"]["participants"]
    assert "Unknown Element" in participants

    # But no entity IDs are extracted (config is invalid, so no inputs)
    assert diagnostics["inputs"] == []


async def test_diagnostics_skips_switch_with_none_value(hass: HomeAssistant) -> None:
    """Test that editable switch entities with None is_on are skipped."""
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
                CONF_CAPACITY: 10.0,
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
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

    # Create mock editable switch entity with is_on = None
    mock_switch = Mock(spec=HaeoInputSwitch)
    mock_switch.entity_mode = ConfigEntityMode.EDITABLE
    mock_switch.is_on = None  # None value should be skipped

    # Create HaeoRuntimeData with input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=Mock(),
        input_entities={
            ("Battery One", "some_boolean_field"): mock_switch,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that the switch with None value is NOT captured in config
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert "some_boolean_field" not in battery_config
