"""Tests for HAEO diagnostics utilities."""

from datetime import UTC, datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
import pytest
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
from custom_components.haeo.coordinator import (
    CoordinatorData,
    CoordinatorOutput,
    ForecastPoint,
    HaeoDataUpdateCoordinator,
    OptimizationContext,
)
from custom_components.haeo.diagnostics import (
    CurrentStateProvider,
    HistoricalStateProvider,
    async_get_config_entry_diagnostics,
    collect_diagnostics,
)
from custom_components.haeo.diagnostics.collector import _extract_entity_ids_from_config
from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY, ElementConfigSchema
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    SECTION_LIMITS,
    SECTION_PARTITIONING,
    SECTION_STORAGE,
)
from custom_components.haeo.elements.grid import CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE, GRID_POWER_IMPORT
from custom_components.haeo.entities.haeo_number import ConfigEntityMode, HaeoInputNumber
from custom_components.haeo.flows import HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.model import OutputType
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.sections import SECTION_COMMON, SECTION_EFFICIENCY, SECTION_POWER_LIMITS, SECTION_PRICING


def _battery_config(
    *,
    name: str,
    connection: str,
    capacity: str | float,
    initial_charge_percentage: str | float,
    max_power_source_target: float | None = None,
    max_power_target_source: float | None = None,
    min_charge_percentage: float | None = None,
    max_charge_percentage: float | None = None,
    efficiency_source_target: float | None = None,
    efficiency_target_source: float | None = None,
    salvage_value: float = 0.0,
) -> dict[str, Any]:
    """Build a sectioned battery config dict for diagnostics tests."""
    limits: dict[str, Any] = {}
    power_limits: dict[str, Any] = {}
    efficiency_section: dict[str, Any] = {}
    pricing: dict[str, Any] = {CONF_SALVAGE_VALUE: as_constant_value(salvage_value)}
    if max_power_source_target is not None:
        power_limits[CONF_MAX_POWER_SOURCE_TARGET] = as_constant_value(max_power_source_target)
    if max_power_target_source is not None:
        power_limits[CONF_MAX_POWER_TARGET_SOURCE] = as_constant_value(max_power_target_source)
    if min_charge_percentage is not None:
        limits[CONF_MIN_CHARGE_PERCENTAGE] = as_constant_value(min_charge_percentage)
    if max_charge_percentage is not None:
        limits[CONF_MAX_CHARGE_PERCENTAGE] = as_constant_value(max_charge_percentage)
    if efficiency_source_target is not None:
        efficiency_section[CONF_EFFICIENCY_SOURCE_TARGET] = as_constant_value(efficiency_source_target)
    if efficiency_target_source is not None:
        efficiency_section[CONF_EFFICIENCY_TARGET_SOURCE] = as_constant_value(efficiency_target_source)

    storage = {
        CONF_CAPACITY: as_entity_value([capacity]) if isinstance(capacity, str) else as_constant_value(capacity),
        CONF_INITIAL_CHARGE_PERCENTAGE: (
            as_entity_value([initial_charge_percentage])
            if isinstance(initial_charge_percentage, str)
            else as_constant_value(initial_charge_percentage)
        ),
    }

    return {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
        SECTION_COMMON: {
            CONF_NAME: name,
            CONF_CONNECTION: as_connection_target(connection),
        },
        SECTION_STORAGE: storage,
        SECTION_LIMITS: limits,
        SECTION_POWER_LIMITS: power_limits,
        SECTION_PRICING: pricing,
        SECTION_EFFICIENCY: efficiency_section,
        SECTION_PARTITIONING: {},
    }


def _grid_config(
    *,
    name: str,
    connection: str,
    price_source_target: list[str] | str | float,
    price_target_source: list[str] | str | float,
) -> dict[str, Any]:
    """Build a sectioned grid config dict for diagnostics tests."""
    return {
        CONF_ELEMENT_TYPE: "grid",
        SECTION_COMMON: {
            CONF_NAME: name,
            CONF_CONNECTION: as_connection_target(connection),
        },
        SECTION_PRICING: {
            CONF_PRICE_SOURCE_TARGET: (
                as_entity_value(price_source_target)
                if isinstance(price_source_target, list)
                else as_entity_value([price_source_target])
                if isinstance(price_source_target, str)
                else as_constant_value(price_source_target)
            ),
            CONF_PRICE_TARGET_SOURCE: (
                as_entity_value(price_target_source)
                if isinstance(price_target_source, list)
                else as_entity_value([price_target_source])
                if isinstance(price_target_source, str)
                else as_constant_value(price_target_source)
            ),
        },
        SECTION_POWER_LIMITS: {},
    }


def _hub_entry_data(name: str = "Test Hub") -> dict[str, Any]:
    """Build hub entry data using the sectioned schema."""
    return {
        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
        HUB_SECTION_COMMON: {CONF_NAME: name},
        HUB_SECTION_TIERS: {
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
    }


def test_extract_entity_ids_from_config_collects_nested_entities() -> None:
    """_extract_entity_ids_from_config collects valid entity IDs from nested config."""
    config = {
        CONF_ELEMENT_TYPE: "grid",
        SECTION_COMMON: {CONF_NAME: "Grid", CONF_CONNECTION: as_connection_target("bus")},
        SECTION_PRICING: {
            CONF_PRICE_SOURCE_TARGET: as_entity_value(["sensor.import", "invalid"]),
            CONF_PRICE_TARGET_SOURCE: as_constant_value(0.1),
        },
        "nested": {"inner": as_entity_value(["sensor.export"])},
        "ignored": {"type": "constant", "value": 2.0},
    }

    entity_ids = _extract_entity_ids_from_config(cast("ElementConfigSchema", config))

    assert entity_ids == {"sensor.import", "sensor.export"}


async def test_collect_diagnostics_historical_skips_outputs(hass: HomeAssistant) -> None:
    """collect_diagnostics omits outputs and marks historical data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data("Historical Hub"),
        entry_id="hist_entry",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = None

    state_provider = Mock()
    state_provider.is_historical = True
    state_provider.timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    state_provider.get_states = AsyncMock(return_value={})

    result = await collect_diagnostics(hass, entry, state_provider)

    assert result.data["outputs"] == {}
    assert result.data["environment"]["historical"] is True
    assert result.missing_entity_ids == []


async def test_diagnostics_basic_structure(hass: HomeAssistant) -> None:
    """Diagnostics returns correct structure with four main keys in the right order."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data("Test Hub"),
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
    assert diagnostics["config"][HUB_SECTION_TIERS][CONF_TIER_1_COUNT] == DEFAULT_TIER_1_COUNT
    assert diagnostics["config"][HUB_SECTION_TIERS][CONF_TIER_1_DURATION] == DEFAULT_TIER_1_DURATION
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
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery One",
                connection="DC Bus",
                capacity="sensor.battery_capacity",
                initial_charge_percentage="sensor.battery_soc",
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
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
    assert battery_config[SECTION_COMMON][CONF_NAME] == "Battery One"
    assert battery_config[SECTION_STORAGE][CONF_CAPACITY] == as_entity_value(["sensor.battery_capacity"])
    assert battery_config[SECTION_STORAGE][CONF_INITIAL_CHARGE_PERCENTAGE] == as_entity_value(["sensor.battery_soc"])

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
        data=_hub_entry_data("Test Hub"),
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
            _battery_config(
                name="Battery",
                connection="DC Bus",
                capacity="sensor.battery_capacity",
                initial_charge_percentage="sensor.battery_soc",
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
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
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    grid_subentry = ConfigSubentry(
        data=MappingProxyType(
            _grid_config(
                name="Grid",
                connection="Main Bus",
                price_source_target=["sensor.grid_import_price", "sensor.grid_import_forecast"],
                price_target_source=0.08,
            )
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
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery One",
                connection="DC Bus",
                capacity=10.0,  # Constant value - creates editable entity
                initial_charge_percentage=50.0,  # Constant - creates editable entity
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
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

    # Create HaeoRuntimeData with input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=Mock(),
        input_entities={
            ("Battery One", (SECTION_STORAGE, CONF_CAPACITY)): mock_number,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that editable entity values are captured in config
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert battery_config[SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(12.5)


async def test_diagnostics_skips_unknown_element_in_input_entities(hass: HomeAssistant) -> None:
    """Diagnostics skips input entities for elements not in participants."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery One",
                connection="DC Bus",
                capacity=10.0,
                initial_charge_percentage=50.0,
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
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
            ("Unknown Element", (SECTION_STORAGE, CONF_CAPACITY)): mock_number,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that Battery One exists unchanged (unknown element was skipped)
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert battery_config[SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(10.0)


async def test_diagnostics_skips_driven_entity_values(hass: HomeAssistant) -> None:
    """Diagnostics skips sensor-driven entities and keeps config value."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery One",
                connection="DC Bus",
                capacity="sensor.battery_capacity",  # Entity ID - creates driven entity
                initial_charge_percentage=50.0,
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
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
            ("Battery One", (SECTION_STORAGE, CONF_CAPACITY)): mock_number,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that driven entity value is NOT captured - config value preserved
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert battery_config[SECTION_STORAGE][CONF_CAPACITY] == as_entity_value(["sensor.battery_capacity"])


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
    target_time = datetime(2026, 1, 20, 14, 32, 3, tzinfo=timezone(timedelta(hours=11)))

    # Create a mock State
    mock_state = State("sensor.test_entity", "42", {"unit_of_measurement": "kW"})

    # Mock the recorder instance
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(return_value={"sensor.test_entity": [mock_state]})

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


async def test_diagnostics_with_network_subentry_not_element_config(hass: HomeAssistant) -> None:
    """Test that network subentry with invalid element config is skipped."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
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
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery One",
                connection="DC Bus",
                capacity=10.0,
                initial_charge_percentage=50.0,
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery One",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Create mock editable number entity with native_value = None
    mock_number = Mock(spec=HaeoInputNumber)
    mock_number.entity_mode = ConfigEntityMode.EDITABLE
    mock_number.native_value = None  # None value should be skipped

    # Create HaeoRuntimeData with input entities
    runtime_data = HaeoRuntimeData(
        horizon_manager=Mock(),
        input_entities={
            ("Battery One", (SECTION_STORAGE, CONF_CAPACITY)): mock_number,
        },
    )
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify that the None value is NOT captured in config
    battery_config = diagnostics["config"]["participants"]["Battery One"]
    assert battery_config[SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(10.0)


@pytest.mark.parametrize("missing_state", [True, False], ids=["missing_soc", "all_found"])
async def test_collect_diagnostics_missing_entity_ids(
    hass: HomeAssistant,
    missing_state: bool,
) -> None:
    """collect_diagnostics reports missing entity IDs when states are absent."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery",
                connection="DC Bus",
                capacity="sensor.battery_capacity",
                initial_charge_percentage="sensor.battery_soc",
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    hass.states.async_set("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})
    if not missing_state:
        hass.states.async_set("sensor.battery_soc", "50", {"unit_of_measurement": "%"})

    entry.runtime_data = None

    result = await collect_diagnostics(hass, entry, CurrentStateProvider(hass))

    if missing_state:
        assert "sensor.battery_soc" in result.missing_entity_ids
        assert "sensor.battery_capacity" not in result.missing_entity_ids
        assert len(result.data["inputs"]) == 1
        assert result.data["inputs"][0]["entity_id"] == "sensor.battery_capacity"
    else:
        assert result.missing_entity_ids == []
        entity_ids = {item["entity_id"] for item in result.data["inputs"]}
        assert entity_ids == {"sensor.battery_capacity", "sensor.battery_soc"}


# --- OptimizationContext-based diagnostics tests ---


def _make_coordinator_data(
    participants: dict[str, Any],
    source_states: dict[str, State] | None = None,
    hub_config: dict[str, Any] | None = None,
) -> CoordinatorData:
    """Build a CoordinatorData with an OptimizationContext for testing."""
    context = OptimizationContext(
        hub_config=hub_config or _hub_entry_data(),
        horizon_start=datetime(2024, 1, 1, tzinfo=UTC),
        participants=participants,
        source_states=source_states or {},
    )
    now = datetime(2024, 1, 1, 0, 5, tzinfo=UTC)
    return CoordinatorData(
        context=context,
        outputs={},
        started_at=now,
        completed_at=now,
    )


async def test_diagnostics_uses_context_when_coordinator_data_available(hass: HomeAssistant) -> None:
    """Diagnostics pulls config and inputs from OptimizationContext when available."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Set up a battery subentry (should NOT be used — context takes precedence)
    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery One",
                connection="DC Bus",
                capacity="sensor.battery_capacity",
                initial_charge_percentage="sensor.battery_soc",
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery One",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Build context with different participants than the subentry
    context_participants = {
        "Context Battery": cast(
            "ElementConfigSchema",
            _battery_config(
                name="Context Battery",
                connection="DC Bus",
                capacity=20.0,
                initial_charge_percentage=80.0,
                max_power_source_target=10.0,
                max_power_target_source=10.0,
                min_charge_percentage=5.0,
                max_charge_percentage=95.0,
                efficiency_source_target=90.0,
                efficiency_target_source=90.0,
            ),
        )
    }
    context_source_states = {
        "sensor.power": State("sensor.power", "100", {"unit_of_measurement": "W"}),
    }

    coordinator_data = _make_coordinator_data(context_participants, context_source_states)

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = coordinator_data

    runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)
    entry.runtime_data = runtime_data

    state_provider = Mock()
    state_provider.is_historical = False
    state_provider.timestamp = None
    state_provider.get_states = AsyncMock(return_value={})

    result = await collect_diagnostics(hass, entry, state_provider)

    # Config should come from context, NOT from subentries
    participants = result.data["config"]["participants"]
    assert "Context Battery" in participants
    assert "Battery One" not in participants
    assert participants["Context Battery"][SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(20.0)

    # Inputs should come from context source_states
    inputs = result.data["inputs"]
    assert len(inputs) == 1
    assert inputs[0]["entity_id"] == "sensor.power"
    assert inputs[0]["state"] == "100"

    # StateProvider should NOT have been called
    state_provider.get_states.assert_not_called()

    # No missing entity IDs on the context path
    assert result.missing_entity_ids == []

    # Environment timestamp should come from the coordinator's started_at, not state_provider
    # The exact string depends on timezone conversion, so just verify it's a valid ISO timestamp
    env_timestamp = datetime.fromisoformat(result.data["environment"]["timestamp"])
    assert env_timestamp == coordinator_data.started_at.astimezone()


async def test_diagnostics_falls_back_when_no_coordinator_data(hass: HomeAssistant) -> None:
    """Diagnostics falls back to StateProvider when coordinator has no data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            _battery_config(
                name="Battery",
                connection="DC Bus",
                capacity="sensor.battery_capacity",
                initial_charge_percentage=50.0,
                max_power_source_target=5.0,
                max_power_target_source=5.0,
                min_charge_percentage=10.0,
                max_charge_percentage=90.0,
                efficiency_source_target=95.0,
                efficiency_target_source=95.0,
            )
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    hass.states.async_set("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})

    # Coordinator exists but has no data (optimization hasn't run yet)
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = None

    runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)
    entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Should fall back to subentry-based config
    participants = diagnostics["config"]["participants"]
    assert "Battery" in participants

    # Should fall back to StateProvider-based inputs
    inputs = diagnostics["inputs"]
    entity_ids = [inp["entity_id"] for inp in inputs]
    assert "sensor.battery_capacity" in entity_ids


async def test_diagnostics_historical_ignores_context(hass: HomeAssistant) -> None:
    """Historical diagnostics always uses StateProvider, even when context exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Coordinator with data IS available
    context_participants = {
        "Context Battery": cast(
            "ElementConfigSchema",
            _battery_config(
                name="Context Battery",
                connection="DC Bus",
                capacity=20.0,
                initial_charge_percentage=80.0,
                max_power_source_target=10.0,
                max_power_target_source=10.0,
                min_charge_percentage=5.0,
                max_charge_percentage=95.0,
                efficiency_source_target=90.0,
                efficiency_target_source=90.0,
            ),
        )
    }
    coordinator_data = _make_coordinator_data(context_participants)

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = coordinator_data

    runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)
    entry.runtime_data = runtime_data

    # Historical provider should be used instead of context
    state_provider = Mock()
    state_provider.is_historical = True
    state_provider.timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    state_provider.get_states = AsyncMock(return_value={})

    result = await collect_diagnostics(hass, entry, state_provider)

    # Should NOT use context — should use fallback path
    participants = result.data["config"]["participants"]
    assert "Context Battery" not in participants

    # StateProvider SHOULD have been called
    state_provider.get_states.assert_called_once()

    # Historical flag should be set
    assert result.data["environment"]["historical"] is True
