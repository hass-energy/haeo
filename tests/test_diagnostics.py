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
    OUTPUT_NAME_OPTIMIZATION_DURATION,
)
from custom_components.haeo.coordinator import CoordinatorData, HaeoDataUpdateCoordinator, OptimizationContext
from custom_components.haeo.diagnostics import (
    CurrentStateProvider,
    HistoricalStateProvider,
    async_get_config_entry_diagnostics,
    collect_diagnostics,
)
from custom_components.haeo.diagnostics.collector import (
    _collect_entity_ids_from_entry,
    _extract_entity_ids_from_config,
    _fetch_inputs_at,
    _get_last_run_before,
)
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
from custom_components.haeo.flows import HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.sections import SECTION_COMMON, SECTION_EFFICIENCY, SECTION_POWER_LIMITS, SECTION_PRICING
from custom_components.haeo.sensor_utils import get_duration_sensor_entity_id


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


# --- Current (non-historical) diagnostics tests ---


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


async def test_diagnostics_basic_structure(hass: HomeAssistant) -> None:
    """Diagnostics returns correct structure with main keys."""
    hub_config = _hub_entry_data("Test Hub")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=hub_config,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator_data = _make_coordinator_data(participants={}, hub_config=hub_config)
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = coordinator_data
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify the main keys
    assert "config" in diagnostics
    assert "environment" in diagnostics
    assert "inputs" in diagnostics
    assert "info" in diagnostics
    assert "outputs" in diagnostics

    # Verify hub config is captured (tiers, common, etc.)
    assert diagnostics["config"][HUB_SECTION_TIERS][CONF_TIER_1_COUNT] == DEFAULT_TIER_1_COUNT
    assert diagnostics["config"][HUB_SECTION_TIERS][CONF_TIER_1_DURATION] == DEFAULT_TIER_1_DURATION
    assert "participants" in diagnostics["config"]

    # Verify environment has static info only
    assert "ha_version" in diagnostics["environment"]
    assert "haeo_version" in diagnostics["environment"]
    assert "timezone" in diagnostics["environment"]

    # Verify info has per-snapshot context
    info = diagnostics["info"]
    assert "diagnostic_target_time" in info
    assert "diagnostic_request_time" in info
    assert "optimization_start" in info
    assert "optimization_end" in info


async def test_diagnostics_errors_when_no_optimization_has_run(hass: HomeAssistant) -> None:
    """Non-historical diagnostics raises RuntimeError when no optimization has completed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = None

    with pytest.raises(RuntimeError, match="no optimization has completed"):
        await async_get_config_entry_diagnostics(hass, entry)


async def test_diagnostics_errors_when_coordinator_has_no_data(hass: HomeAssistant) -> None:
    """Non-historical diagnostics raises RuntimeError when coordinator.data is None."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = None
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)

    with pytest.raises(RuntimeError, match="no optimization has completed"):
        await async_get_config_entry_diagnostics(hass, entry)


async def test_diagnostics_uses_context_for_config_and_inputs(hass: HomeAssistant) -> None:
    """Current diagnostics pulls config and inputs from OptimizationContext."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

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
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)

    result = await collect_diagnostics(hass, entry)

    # Config comes from context
    participants = result.data["config"]["participants"]
    assert "Context Battery" in participants
    assert participants["Context Battery"][SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(20.0)

    # Inputs come from context source_states
    inputs = result.data["inputs"]
    assert len(inputs) == 1
    assert inputs[0]["entity_id"] == "sensor.power"
    assert inputs[0]["state"] == "100"

    # No missing entity IDs on the context path
    assert result.missing_entity_ids == []

    # Info has standardized timestamps
    info = result.data["info"]
    assert datetime.fromisoformat(info["optimization_start"]) == coordinator_data.started_at.astimezone()
    assert datetime.fromisoformat(info["optimization_end"]) == coordinator_data.completed_at.astimezone()
    assert datetime.fromisoformat(info["diagnostic_target_time"]) == coordinator_data.context.horizon_start.astimezone()
    assert "diagnostic_request_time" in info


async def test_diagnostics_with_outputs(hass: HomeAssistant) -> None:
    """Current diagnostics includes output sensor states."""
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

    # Register output sensor in entity registry (required for get_output_sensors)
    entity_registry = er.async_get(hass)
    output_entity_id = f"sensor.{DOMAIN}_hub_entry_{grid_subentry.subentry_id}_{GRID_POWER_IMPORT}"
    entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"hub_entry_{grid_subentry.subentry_id}_{GRID_POWER_IMPORT}",
        config_entry=entry,
    )
    hass.states.async_set(output_entity_id, "5.5", {"unit_of_measurement": "kW", "element_name": "Grid"})

    coordinator_data = _make_coordinator_data(participants={})
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = coordinator_data
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    outputs = diagnostics["outputs"]
    assert len(outputs) >= 1
    output_entity = next(
        (s for s in outputs.values() if GRID_POWER_IMPORT in s["entity_id"]),
        None,
    )
    assert output_entity is not None
    assert output_entity["state"] == "5.5"


# --- Historical diagnostics tests ---


async def test_historical_diagnostics_uses_last_run(hass: HomeAssistant) -> None:
    """Historical diagnostics finds last run before T, fetches inputs at started_at."""
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
    entry.runtime_data = None

    as_of = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    run_completed = datetime(2024, 1, 1, 11, 55, tzinfo=UTC)
    run_duration = 0.5  # seconds
    run_started = run_completed - timedelta(seconds=run_duration)

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(run_started, run_completed),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=(
                [State("sensor.battery_capacity", "5000").as_dict()],
                ["sensor.battery_soc"],
            ),
        ) as mock_fetch_inputs,
    ):
        result = await collect_diagnostics(hass, entry, as_of=as_of)

    # Inputs should have been fetched at started_at (the run's start time)
    mock_fetch_inputs.assert_called_once_with(hass, entry, run_started)

    # Config should be current config from the entry
    participants = result.data["config"]["participants"]
    assert "Battery" in participants

    # Inputs come from recorder at the run's started_at
    assert len(result.data["inputs"]) == 1
    assert result.data["inputs"][0]["entity_id"] == "sensor.battery_capacity"

    # Missing entities reported
    assert "sensor.battery_soc" in result.missing_entity_ids

    # Info has standardized timestamps
    info = result.data["info"]
    assert datetime.fromisoformat(info["diagnostic_target_time"]) == as_of.astimezone()
    assert datetime.fromisoformat(info["optimization_start"]) == run_started.astimezone()
    assert datetime.fromisoformat(info["optimization_end"]) == run_completed.astimezone()
    assert "diagnostic_request_time" in info

    # No outputs for historical
    assert "outputs" not in result.data


async def test_historical_diagnostics_no_run_found_errors(hass: HomeAssistant) -> None:
    """Historical diagnostics raises RuntimeError when no run found before T."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = None

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(RuntimeError, match="no optimization run found"),
    ):
        await collect_diagnostics(hass, entry, as_of=datetime(2024, 1, 1, tzinfo=UTC))


async def test_historical_diagnostics_ignores_context(hass: HomeAssistant) -> None:
    """Historical diagnostics always uses recorder, even when coordinator context exists."""
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
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)

    as_of = datetime(2024, 1, 1, tzinfo=UTC)
    run_completed = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    run_started = run_completed - timedelta(seconds=0.1)

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(run_started, run_completed),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=([], []),
        ),
    ):
        result = await collect_diagnostics(hass, entry, as_of=as_of)

    # Should NOT use context — should use entry-based config
    participants = result.data["config"]["participants"]
    assert "Context Battery" not in participants

    # Has standardized timestamps
    assert "diagnostic_target_time" in result.data["info"]


async def test_historical_diagnostics_with_participants(hass: HomeAssistant) -> None:
    """Historical diagnostics includes participant configs from current config entry."""
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
    entry.runtime_data = None

    as_of = datetime(2024, 1, 1, tzinfo=UTC)
    run_completed = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    run_started = run_completed - timedelta(seconds=0.2)

    capacity_state = State("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})
    soc_state = State("sensor.battery_soc", "75", {"unit_of_measurement": "%"})

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(run_started, run_completed),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=(
                [capacity_state.as_dict(), soc_state.as_dict()],
                [],
            ),
        ),
    ):
        result = await collect_diagnostics(hass, entry, as_of=as_of)

    # Config has participants (current config)
    participants = result.data["config"]["participants"]
    assert "Battery One" in participants
    battery_config = participants["Battery One"]
    assert battery_config[CONF_ELEMENT_TYPE] == ELEMENT_TYPE_BATTERY
    assert battery_config[SECTION_COMMON][CONF_NAME] == "Battery One"

    # Inputs from recorder
    inputs = result.data["inputs"]
    assert len(inputs) == 2
    entity_ids = [inp["entity_id"] for inp in inputs]
    assert "sensor.battery_capacity" in entity_ids
    assert "sensor.battery_soc" in entity_ids


async def test_historical_diagnostics_skips_network_subentry(hass: HomeAssistant) -> None:
    """Historical diagnostics skips network subentries when collecting participants."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    network_subentry = ConfigSubentry(
        data=MappingProxyType({"some_network_config": "value"}),
        subentry_type="network",
        title="Network Config",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, network_subentry)

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
    entry.runtime_data = None

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 1, tzinfo=UTC)),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=([], []),
        ),
    ):
        result = await collect_diagnostics(hass, entry, as_of=datetime(2024, 1, 1, tzinfo=UTC))

    participants = result.data["config"]["participants"]
    assert "Network Config" not in participants
    assert "Battery" in participants


async def test_historical_diagnostics_invalid_element_config(hass: HomeAssistant) -> None:
    """Historical diagnostics includes invalid subentry in participants."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    invalid_subentry = ConfigSubentry(
        data=MappingProxyType({"some_data": "value"}),
        subentry_type="unknown_element_type",
        title="Unknown Element",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, invalid_subentry)
    entry.runtime_data = None

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 1, tzinfo=UTC)),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=([], []),
        ),
    ):
        result = await collect_diagnostics(hass, entry, as_of=datetime(2024, 1, 1, tzinfo=UTC))

    participants = result.data["config"]["participants"]
    assert "Unknown Element" in participants
    assert result.data["inputs"] == []


# --- StateProvider tests ---


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
        end_time=target_time,
        entity_ids=["sensor.test"],
        include_start_time_state=True,
        significant_changes_only=False,
        no_attributes=False,
    )

    assert result == {"sensor.test": [mock_state]}


# --- Internal function tests ---


def test_extract_entity_ids_handles_non_dict_values() -> None:
    """_extract_entity_ids_from_config ignores non-dict/non-schema values."""
    config = cast(
        "ElementConfigSchema",
        {
            CONF_ELEMENT_TYPE: "grid",
            "plain_string": "not_a_schema_value",
            "plain_number": 42,
        },
    )
    entity_ids = _extract_entity_ids_from_config(config)
    assert entity_ids == set()


def test_collect_entity_ids_from_entry_with_battery_subentry(hass: HomeAssistant) -> None:
    """_collect_entity_ids_from_entry collects entity IDs from battery subentry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
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
            )
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    entity_ids = _collect_entity_ids_from_entry(entry)

    assert "sensor.battery_capacity" in entity_ids
    assert "sensor.battery_soc" in entity_ids


def test_collect_entity_ids_from_entry_skips_network_subentry(hass: HomeAssistant) -> None:
    """_collect_entity_ids_from_entry skips network subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    network_subentry = ConfigSubentry(
        data=MappingProxyType({"some_config": "value"}),
        subentry_type="network",
        title="Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, network_subentry)

    entity_ids = _collect_entity_ids_from_entry(entry)
    assert entity_ids == set()


def test_collect_entity_ids_from_entry_skips_invalid_element(hass: HomeAssistant) -> None:
    """_collect_entity_ids_from_entry skips subentries that don't pass is_element_config_schema."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    invalid_subentry = ConfigSubentry(
        data=MappingProxyType({"random_field": "value"}),
        subentry_type="unknown_type",
        title="Invalid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, invalid_subentry)

    entity_ids = _collect_entity_ids_from_entry(entry)
    assert entity_ids == set()


async def test_fetch_inputs_at_returns_states(hass: HomeAssistant) -> None:
    """_fetch_inputs_at fetches recorder states for entity IDs in subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
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
            )
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    target_time = datetime(2024, 1, 1, tzinfo=UTC)
    cap_state = State("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})
    soc_state = State("sensor.battery_soc", "75", {"unit_of_measurement": "%"})

    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())

    with (
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.recorder_history.get_significant_states",
            return_value={
                "sensor.battery_capacity": [cap_state],
                "sensor.battery_soc": [soc_state],
            },
        ),
    ):
        inputs, missing = await _fetch_inputs_at(hass, entry, target_time)

    assert len(inputs) == 2
    assert missing == []
    entity_ids = [inp["entity_id"] for inp in inputs]
    assert "sensor.battery_capacity" in entity_ids
    assert "sensor.battery_soc" in entity_ids


async def test_fetch_inputs_at_reports_missing_entities(hass: HomeAssistant) -> None:
    """_fetch_inputs_at reports entities not found in recorder."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
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
            )
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    target_time = datetime(2024, 1, 1, tzinfo=UTC)
    cap_state = State("sensor.battery_capacity", "5000")

    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())

    with (
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.recorder_history.get_significant_states",
            return_value={"sensor.battery_capacity": [cap_state]},
        ),
    ):
        inputs, missing = await _fetch_inputs_at(hass, entry, target_time)

    assert len(inputs) == 1
    assert "sensor.battery_soc" in missing


async def test_fetch_inputs_at_empty_subentries(hass: HomeAssistant) -> None:
    """_fetch_inputs_at returns empty when no entity IDs found in subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    inputs, missing = await _fetch_inputs_at(hass, entry, datetime(2024, 1, 1, tzinfo=UTC))

    assert inputs == []
    assert missing == []


async def test_get_last_run_before_finds_run(hass: HomeAssistant) -> None:
    """_get_last_run_before returns (started_at, completed_at) from duration sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    completed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    duration_seconds = 2.5
    duration_state = State(
        "sensor.haeo_optimization_duration",
        str(duration_seconds),
        last_updated=completed_at,
    )

    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())

    with (
        patch(
            "custom_components.haeo.diagnostics.collector.get_duration_sensor_entity_id",
            return_value="sensor.haeo_optimization_duration",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.recorder_history.get_significant_states",
            return_value={"sensor.haeo_optimization_duration": [duration_state]},
        ),
    ):
        result = await _get_last_run_before(hass, entry, datetime(2024, 1, 1, 13, 0, tzinfo=UTC))

    assert result is not None
    started_at, returned_completed = result
    assert returned_completed == completed_at
    assert started_at == completed_at - timedelta(seconds=duration_seconds)


async def test_get_last_run_before_no_duration_sensor(hass: HomeAssistant) -> None:
    """_get_last_run_before returns None when no duration sensor exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.haeo.diagnostics.collector.get_duration_sensor_entity_id",
        return_value=None,
    ):
        result = await _get_last_run_before(hass, entry, datetime(2024, 1, 1, tzinfo=UTC))

    assert result is None


async def test_get_last_run_before_no_recorder_state(hass: HomeAssistant) -> None:
    """_get_last_run_before returns None when recorder has no state for duration sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())

    with (
        patch(
            "custom_components.haeo.diagnostics.collector.get_duration_sensor_entity_id",
            return_value="sensor.haeo_optimization_duration",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.recorder_history.get_significant_states",
            return_value={},
        ),
    ):
        result = await _get_last_run_before(hass, entry, datetime(2024, 1, 1, tzinfo=UTC))

    assert result is None


async def test_get_last_run_before_invalid_duration_state(hass: HomeAssistant) -> None:
    """_get_last_run_before returns None when duration state is not a valid number."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    invalid_state = State("sensor.haeo_optimization_duration", "unavailable")

    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())

    with (
        patch(
            "custom_components.haeo.diagnostics.collector.get_duration_sensor_entity_id",
            return_value="sensor.haeo_optimization_duration",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.recorder_history.get_significant_states",
            return_value={"sensor.haeo_optimization_duration": [invalid_state]},
        ),
    ):
        result = await _get_last_run_before(hass, entry, datetime(2024, 1, 1, tzinfo=UTC))

    assert result is None


# --- get_duration_sensor_entity_id tests ---


def test_get_duration_sensor_entity_id_found(hass: HomeAssistant) -> None:
    """get_duration_sensor_entity_id returns entity_id when duration sensor exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"hub_entry_{OUTPUT_NAME_OPTIMIZATION_DURATION}",
        config_entry=entry,
    )

    result = get_duration_sensor_entity_id(hass, entry)
    assert result is not None
    assert OUTPUT_NAME_OPTIMIZATION_DURATION in result


def test_get_duration_sensor_entity_id_not_found(hass: HomeAssistant) -> None:
    """get_duration_sensor_entity_id returns None when no duration sensor exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    result = get_duration_sensor_entity_id(hass, entry)
    assert result is None
