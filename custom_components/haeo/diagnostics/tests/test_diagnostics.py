"""Tests for HAEO diagnostics utilities."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
import json
from types import MappingProxyType
from typing import (
    Any,  # noqa: TID251  # deep chained subscripts into a JSON payload; narrowing would explode assertions
)
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.json import ExtendedJSONEncoder
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.coordinator import CoordinatorData, HaeoDataUpdateCoordinator, OptimizationContext
from custom_components.haeo.core.adapters.elements.grid import GRID_POWER_IMPORT
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_HORIZON, CONF_NAME, HORIZON_PRESET_2_DAYS
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.config_loader import ElementInput
from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementConfigSchema, ElementType
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_LIMIT_COST,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    SECTION_ADVANCED,
    SECTION_LIMITS,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.field_hints import FieldHint, MeterFieldHint
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.diagnostics import async_get_config_entry_diagnostics, collect_diagnostics
from custom_components.haeo.diagnostics.collector import (
    DIAGNOSTICS_SCHEMA_VERSION,
    HISTORICAL_CALENDAR_LOOKAHEAD,
    _collect_entity_ids_from_entry,
    _extract_entity_ids_from_config,
    _fetch_inputs_at,
    _get_last_run_before,
)
from custom_components.haeo.flows import HUB_SECTION_COMMON


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
) -> dict[str, object]:
    """Build a sectioned battery config dict for diagnostics tests."""
    limits: dict[str, object] = {}
    power_limits: dict[str, object] = {}
    efficiency_section: dict[str, object] = {}
    pricing: dict[str, object] = {CONF_SALVAGE_VALUE: as_constant_value(salvage_value)}
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
        CONF_ELEMENT_TYPE: ElementType.BATTERY,
        CONF_NAME: name,
        CONF_CONNECTION: as_connection_target(connection),
        SECTION_STORAGE: storage,
        SECTION_LIMITS: limits,
        SECTION_POWER_LIMITS: power_limits,
        SECTION_PRICING: pricing,
        SECTION_EFFICIENCY: efficiency_section,
        SECTION_ADVANCED: {CONF_CHARGE_LIMIT_COST: as_constant_value(100.0)},
    }


def _grid_config(
    *,
    name: str,
    connection: str,
    price_source_target: list[str] | str | float,
    price_target_source: list[str] | str | float,
) -> dict[str, object]:
    """Build a sectioned grid config dict for diagnostics tests."""
    return {
        CONF_ELEMENT_TYPE: "grid",
        CONF_NAME: name,
        CONF_CONNECTION: as_connection_target(connection),
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


def _hub_entry_data(name: str = "Test Hub") -> dict[str, object]:
    """Build hub entry data using the sectioned schema."""
    return {
        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
        HUB_SECTION_COMMON: {CONF_NAME: name, CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS)},
    }


def _participants(config: Mapping[str, object]) -> Any:
    """Return the config's ``participants`` section for exploratory test assertions.

    ``DiagnosticsResult.config`` is honestly typed as ``dict[str, object]`` since its
    shape is dynamic (redacted, arbitrary element schemas); tests need to chain
    subscripts into it freely, which this narrow, well-named helper isolates.
    """
    return config["participants"]


def test_extract_entity_ids_from_config_collects_nested_entities() -> None:
    """_extract_entity_ids_from_config collects valid entity IDs from nested config."""
    config = {
        CONF_ELEMENT_TYPE: "grid",
        CONF_NAME: "Grid",
        CONF_CONNECTION: as_connection_target("bus"),
        SECTION_PRICING: {
            CONF_PRICE_SOURCE_TARGET: as_entity_value(["sensor.import", "invalid"]),
            CONF_PRICE_TARGET_SOURCE: as_constant_value(0.1),
        },
        "nested": {"inner": as_entity_value(["sensor.export"])},
        "ignored": {"type": "constant", "value": 2.0},
    }

    # Fixture includes non-schema keys and invalid entity placeholders; structural guard would reject it.
    entity_ids = _extract_entity_ids_from_config(config)  # type: ignore[arg-type]

    assert entity_ids == {"sensor.import", "sensor.export"}


# --- Current (non-historical) diagnostics tests ---


def _make_coordinator_data(
    participants: Mapping[str, object],
    source_states: dict[str, State] | None = None,
    hub_config: dict[str, object] | None = None,
) -> CoordinatorData:
    """Build a CoordinatorData with an OptimizationContext for testing."""
    context = OptimizationContext(
        hub_config=hub_config or _hub_entry_data(),
        horizon_start=datetime(2024, 1, 1, tzinfo=UTC),
        # Fixture participants are built by _battery_config/_grid_config and don't carry
        # the full ElementConfigSchema shape; only the diagnostics plumbing is under test.
        participants=participants,  # type: ignore[arg-type]
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
    """Diagnostics returns correct structure with main keys via HA entry point."""
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

    # HA entry point returns a dict (via to_dict)
    diagnostics: dict[str, Any] = await async_get_config_entry_diagnostics(hass, entry)

    assert "schema_version" not in diagnostics
    assert "diagnostics_version" not in diagnostics
    assert "config" in diagnostics
    assert "environment" in diagnostics
    assert "inputs" in diagnostics
    assert "info" not in diagnostics
    assert "outputs" in diagnostics

    assert diagnostics["config"][HUB_SECTION_COMMON][CONF_HORIZON] == as_horizon_preset_value(HORIZON_PRESET_2_DAYS)
    assert "participants" in diagnostics["config"]

    environment = diagnostics["environment"]
    assert environment["diagnostics_version"] == DIAGNOSTICS_SCHEMA_VERSION
    assert "ha_version" in environment
    assert "haeo_version" in environment
    assert "timezone" in environment
    assert "diagnostic_request_time" in environment
    assert environment["diagnostic_target_time"] is None
    assert "optimization_start_time" in environment
    assert "optimization_end_time" in environment
    assert "horizon_start" in environment


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
        "Context Battery": _battery_config(
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
    assert "Context Battery" in _participants(result.config)
    assert _participants(result.config)["Context Battery"][SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(20.0)

    # Inputs come from context source_states
    assert len(result.inputs) == 1
    assert result.inputs[0]["entity_id"] == "sensor.power"
    assert result.inputs[0]["state"] == "100"

    # No missing entity IDs on the context path
    assert result.missing_entity_ids == ()

    environment = result.environment
    assert environment.diagnostic_target_time is None
    assert datetime.fromisoformat(environment.optimization_start_time) == coordinator_data.started_at.astimezone()
    assert datetime.fromisoformat(environment.optimization_end_time) == coordinator_data.completed_at.astimezone()
    assert datetime.fromisoformat(environment.horizon_start) == coordinator_data.context.horizon_start.astimezone()

    # Outputs present for current
    assert result.outputs is not None


async def test_collect_diagnostics_unwraps_mappingproxy_participants(hass: HomeAssistant) -> None:
    """``collect_diagnostics`` returns plain dicts for participant configs.

    HA exposes ``ConfigSubentry.data`` as ``MappingProxyType``. We follow HA's standard
    diagnostics convention and pipe the assembled config through ``async_redact_data``,
    which spreads any ``Mapping`` into a plain ``dict`` as a side-effect of its
    ``{**data}`` recursion. Without that, HA's ``ExtendedJSONEncoder`` (which both our
    save service and HA's diagnostics download path use) emits ``{"__type": ...,
    "repr": "mappingproxy(...)"}`` placeholders.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    grid_config = MappingProxyType(
        _grid_config(
            name="Grid",
            connection="Main Bus",
            price_source_target=0.20,
            price_target_source=0.08,
        )
    )
    battery_config = MappingProxyType(
        _battery_config(
            name="Battery",
            connection="Main Bus",
            capacity=10.0,
            initial_charge_percentage=50.0,
        )
    )
    participants = {"Grid": grid_config, "Battery": battery_config}

    coordinator_data = _make_coordinator_data(participants=participants)
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = coordinator_data
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)

    result = await collect_diagnostics(hass, entry)

    grid = _participants(result.config)["Grid"]
    battery = _participants(result.config)["Battery"]
    assert type(grid) is dict
    assert type(battery) is dict
    assert grid[CONF_NAME] == "Grid"
    assert battery[CONF_NAME] == "Battery"

    serialized = json.dumps(result.to_dict(), cls=ExtendedJSONEncoder)
    assert "__type" not in serialized
    assert "mappingproxy" not in serialized


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

    diagnostics: dict[str, Any] = await async_get_config_entry_diagnostics(hass, entry)

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
        subentry_type=ElementType.BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)
    entry.runtime_data = None

    target_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    run_completed = datetime(2024, 1, 1, 11, 55, tzinfo=UTC)
    run_duration = 0.5  # seconds
    run_started = run_completed - timedelta(seconds=run_duration)

    horizon_iso = "2024-01-01T11:50:00+00:00"
    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(run_started, run_completed, horizon_iso),
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
        result = await collect_diagnostics(hass, entry, target_time=target_time)

    # Inputs should have been fetched at started_at (the run's start time)
    mock_fetch_inputs.assert_called_once_with(hass, entry, run_started)

    # Config should be current config from the entry
    assert "Battery" in _participants(result.config)

    # Inputs come from recorder at the run's started_at
    assert len(result.inputs) == 1
    assert result.inputs[0]["entity_id"] == "sensor.battery_capacity"

    # Missing entities reported
    assert "sensor.battery_soc" in result.missing_entity_ids

    environment = result.environment
    assert environment.diagnostic_target_time is not None
    assert datetime.fromisoformat(environment.diagnostic_target_time) == target_time.astimezone()
    assert datetime.fromisoformat(environment.optimization_start_time) == run_started.astimezone()
    assert datetime.fromisoformat(environment.optimization_end_time) == run_completed.astimezone()
    assert environment.diagnostic_request_time is not None
    assert environment.horizon_start == horizon_iso

    # No outputs for historical
    assert result.outputs is None


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
        await collect_diagnostics(hass, entry, target_time=datetime(2024, 1, 1, tzinfo=UTC))


async def test_historical_diagnostics_ignores_context(hass: HomeAssistant) -> None:
    """Historical diagnostics always uses recorder, even when coordinator context exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data=_hub_entry_data("Test Hub"),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    context_participants = {
        "Context Battery": _battery_config(
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
    }
    coordinator_data = _make_coordinator_data(context_participants)
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = coordinator_data
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(), coordinator=coordinator)

    target_time = datetime(2024, 1, 1, tzinfo=UTC)
    run_completed = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    run_started = run_completed - timedelta(seconds=0.1)

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(run_started, run_completed, "2024-01-01T00:00:00+00:00"),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=([], []),
        ),
    ):
        result = await collect_diagnostics(hass, entry, target_time=target_time)

    # Should NOT use context — should use entry-based config
    assert "Context Battery" not in _participants(result.config)

    assert result.environment.diagnostic_target_time is not None


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
        subentry_type=ElementType.BATTERY,
        title="Battery One",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)
    entry.runtime_data = None

    target_time = datetime(2024, 1, 1, tzinfo=UTC)
    run_completed = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    run_started = run_completed - timedelta(seconds=0.2)

    capacity_state = State("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})
    soc_state = State("sensor.battery_soc", "75", {"unit_of_measurement": "%"})

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(run_started, run_completed, "2024-01-01T00:00:00+00:00"),
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
        result = await collect_diagnostics(hass, entry, target_time=target_time)

    participants = _participants(result.config)
    assert "Battery One" in participants
    assert participants["Battery One"][CONF_ELEMENT_TYPE] == ElementType.BATTERY
    assert participants["Battery One"][CONF_NAME] == "Battery One"

    inputs = result.inputs
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
        subentry_type=ElementType.BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)
    entry.runtime_data = None

    with (
        patch(
            "custom_components.haeo.diagnostics.collector._get_last_run_before",
            new_callable=AsyncMock,
            return_value=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 1, tzinfo=UTC),
                "2024-01-01T00:00:00+00:00",
            ),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=([], []),
        ),
    ):
        result = await collect_diagnostics(hass, entry, target_time=datetime(2024, 1, 1, tzinfo=UTC))

    assert "Network Config" not in _participants(result.config)
    assert "Battery" in _participants(result.config)


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
            return_value=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 1, tzinfo=UTC),
                "2024-01-01T00:00:00+00:00",
            ),
        ),
        patch(
            "custom_components.haeo.diagnostics.collector._fetch_inputs_at",
            new_callable=AsyncMock,
            return_value=([], []),
        ),
    ):
        result = await collect_diagnostics(hass, entry, target_time=datetime(2024, 1, 1, tzinfo=UTC))

    assert "Unknown Element" in _participants(result.config)
    assert result.inputs == []


# --- Internal function tests ---


def test_extract_entity_ids_handles_non_dict_values() -> None:
    """_extract_entity_ids_from_config ignores non-dict/non-schema values."""
    config: ElementConfigSchema = {  # type: ignore[typeddict-item]  # non-schema keys must reach runtime filtering under test
        CONF_ELEMENT_TYPE: "grid",
        "plain_string": "not_a_schema_value",
        "plain_number": 42,
    }
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
        subentry_type=ElementType.BATTERY,
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
        subentry_type=ElementType.BATTERY,
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
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
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


async def test_fetch_inputs_at_injects_meter_totals_as_of_the_run(hass: HomeAssistant) -> None:
    """Historical inputs carry each meter input's running totals as of the run, as a live run injects them."""
    entry = MockConfigEntry(domain=DOMAIN, data=_hub_entry_data(), entry_id="hub_entry")
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
        subentry_type=ElementType.BATTERY,
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)
    target_time = datetime(2024, 1, 1, tzinfo=UTC)
    meter_input = ElementInput(
        ("storage", "capacity"),
        ("storage", "capacity"),
        FieldHint(output_type=OutputType.ENERGY, meter=MeterFieldHint(since="initial_charge_percentage")),
    )
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())
    totals_at = AsyncMock(return_value=[(target_time.timestamp(), 42.0)])

    with (
        patch("custom_components.haeo.diagnostics.collector.get_recorder_instance", return_value=mock_recorder),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
            return_value={
                "sensor.battery_capacity": [State("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})],
                "sensor.battery_soc": [State("sensor.battery_soc", "75", {"unit_of_measurement": "%"})],
            },
        ),
        patch("custom_components.haeo.diagnostics.collector.element_inputs", return_value=[meter_input]),
        patch("custom_components.haeo.diagnostics.collector.async_meter_totals_at", totals_at),
    ):
        inputs, missing = await _fetch_inputs_at(hass, entry, target_time)

    assert missing == []
    by_id = {inp["entity_id"]: inp for inp in inputs}
    capacity_attributes = by_id["sensor.battery_capacity"]["attributes"]
    assert isinstance(capacity_attributes, Mapping)
    assert capacity_attributes[METER_TOTALS_ATTRIBUTE] == [(target_time.timestamp(), 42.0)]
    soc_attributes = by_id["sensor.battery_soc"]["attributes"]
    assert isinstance(soc_attributes, Mapping)
    assert METER_TOTALS_ATTRIBUTE not in soc_attributes
    assert totals_at.await_args is not None
    assert totals_at.await_args.args[1:3] == ("sensor.battery_capacity", target_time)


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
        subentry_type=ElementType.BATTERY,
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
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
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
    """_get_last_run_before returns (started_at, completed_at, horizon_start) from recorder."""
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
    horizon_iso = "2024-01-01T12:00:00+00:00"
    horizon_state = State("sensor.haeo_forecast_horizon", horizon_iso)

    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())

    with (
        patch(
            "custom_components.haeo.diagnostics.collector.get_duration_sensor_entity_id",
            return_value="sensor.haeo_optimization_duration",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_horizon_sensor_entity_id",
            return_value="sensor.haeo_forecast_horizon",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
            return_value={
                "sensor.haeo_optimization_duration": [duration_state],
                "sensor.haeo_forecast_horizon": [horizon_state],
            },
        ),
    ):
        result = await _get_last_run_before(hass, entry, datetime(2024, 1, 1, 13, 0, tzinfo=UTC))

    assert result is not None
    started_at, returned_completed, returned_horizon = result
    assert returned_completed == completed_at
    assert started_at == completed_at - timedelta(seconds=duration_seconds)
    assert returned_horizon == horizon_iso


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


async def test_get_last_run_before_no_horizon_sensor(hass: HomeAssistant) -> None:
    """_get_last_run_before returns None when no horizon sensor exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.haeo.diagnostics.collector.get_duration_sensor_entity_id",
            return_value="sensor.haeo_optimization_duration",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_horizon_sensor_entity_id",
            return_value=None,
        ),
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
            "custom_components.haeo.diagnostics.collector.get_horizon_sensor_entity_id",
            return_value="sensor.haeo_forecast_horizon",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
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
            "custom_components.haeo.diagnostics.collector.get_horizon_sensor_entity_id",
            return_value="sensor.haeo_forecast_horizon",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
            return_value={
                "sensor.haeo_optimization_duration": [invalid_state],
                "sensor.haeo_forecast_horizon": [State("sensor.haeo_forecast_horizon", "2024-01-01T00:00:00+00:00")],
            },
        ),
    ):
        result = await _get_last_run_before(hass, entry, datetime(2024, 1, 1, tzinfo=UTC))

    assert result is None


async def test_get_last_run_before_no_horizon_state(hass: HomeAssistant) -> None:
    """_get_last_run_before returns None when horizon sensor has no recorded state."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data(),
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    completed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    duration_state = State(
        "sensor.haeo_optimization_duration",
        "2.5",
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
            "custom_components.haeo.diagnostics.collector.get_horizon_sensor_entity_id",
            return_value="sensor.haeo_forecast_horizon",
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_recorder_instance",
            return_value=mock_recorder,
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
            return_value={
                "sensor.haeo_optimization_duration": [duration_state],
            },
        ),
    ):
        result = await _get_last_run_before(hass, entry, datetime(2024, 1, 1, 13, 0, tzinfo=UTC))

    assert result is None


def _calendar_hub(hass: HomeAssistant) -> MockConfigEntry:
    """Return a hub with one element whose trip section reads calendar.trips."""
    entry = MockConfigEntry(domain=DOMAIN, data=_hub_entry_data(), entry_id="hub_entry")
    entry.add_to_hass(hass)
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({CONF_NAME: "EV", "trip": {"trip_calendar": as_entity_value(["calendar.trips"])}}),
            subentry_type="ev",
            title="EV",
            unique_id=None,
        ),
    )
    return entry


@pytest.mark.parametrize(("fetched", "expect_missing"), [([{"summary": "Trip"}], False), (None, True)])
async def test_fetch_inputs_at_injects_calendar_events_fetched_for_the_run(
    hass: HomeAssistant, fetched: list[dict[str, str]] | None, *, expect_missing: bool
) -> None:
    """Historical inputs carry each calendar's events from the run, which the recorder never holds."""
    entry = _calendar_hub(hass)
    target_time = datetime(2024, 1, 1, tzinfo=UTC)
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())
    fetch = AsyncMock(return_value=fetched)

    with (
        patch("custom_components.haeo.diagnostics.collector.get_recorder_instance", return_value=mock_recorder),
        patch(
            "custom_components.haeo.diagnostics.collector._collect_entity_ids_from_entry",
            return_value={"calendar.trips"},
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
            return_value={"calendar.trips": [State("calendar.trips", "off", {"friendly_name": "Trips"})]},
        ),
        patch("custom_components.haeo.diagnostics.collector.async_fetch_calendar_events", fetch),
    ):
        inputs, missing = await _fetch_inputs_at(hass, entry, target_time)

    fetch.assert_awaited_once_with(hass, "calendar.trips", target_time, target_time + HISTORICAL_CALENDAR_LOOKAHEAD)
    if expect_missing:
        assert inputs == []
        assert missing == ["calendar.trips"]
    else:
        assert missing == []
        [captured] = inputs
        assert captured["attributes"] == {"friendly_name": "Trips", CALENDAR_EVENTS_ATTRIBUTE: fetched}


async def test_fetch_inputs_at_gives_up_on_a_calendar_that_does_not_answer(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saving diagnostics waits only briefly for a calendar, then reports it as missing."""
    monkeypatch.setattr("custom_components.haeo.diagnostics.collector.HISTORICAL_CALENDAR_TIMEOUT", 0.01, raising=False)
    entry = _calendar_hub(hass)
    target_time = datetime(2024, 1, 1, tzinfo=UTC)
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())

    async def never_answers(*_args: object) -> None:
        await asyncio.Event().wait()

    with (
        patch("custom_components.haeo.diagnostics.collector.get_recorder_instance", return_value=mock_recorder),
        patch(
            "custom_components.haeo.diagnostics.collector._collect_entity_ids_from_entry",
            return_value={"calendar.trips"},
        ),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
            return_value={"calendar.trips": [State("calendar.trips", "off", {"friendly_name": "Trips"})]},
        ),
        patch("custom_components.haeo.diagnostics.collector.async_fetch_calendar_events", never_answers),
    ):
        inputs, missing = await _fetch_inputs_at(hass, entry, target_time)

    assert inputs == []
    assert missing == ["calendar.trips"]


async def test_fetch_inputs_at_keeps_only_the_meter_totals_the_open_window_reads(hass: HomeAssistant) -> None:
    """Historical meter totals are the one the open window rises from and the latest, not a whole week."""
    entry = MockConfigEntry(domain=DOMAIN, data=_hub_entry_data(), entry_id="hub_entry")
    entry.add_to_hass(hass)
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType(
                _battery_config(
                    name="Battery",
                    connection="DC Bus",
                    capacity="sensor.battery_capacity",
                    initial_charge_percentage="calendar.runs",
                )
            ),
            subentry_type=ElementType.BATTERY,
            title="Battery",
            unique_id=None,
        ),
    )
    target = datetime(2024, 1, 1, 12, tzinfo=UTC)
    run = {
        "start": (target - timedelta(minutes=50)).isoformat(),
        "end": (target + timedelta(hours=1)).isoformat(),
        "summary": "Run",
    }
    meter_input = ElementInput(
        ("storage", "capacity"),
        ("storage", "capacity"),
        FieldHint(output_type=OutputType.ENERGY, meter=MeterFieldHint(since="initial_charge_percentage")),
    )
    mock_recorder = Mock()
    mock_recorder.async_add_executor_job = AsyncMock(side_effect=lambda fn: fn())
    week = [((target - timedelta(minutes=minutes)).timestamp(), 100.0 - minutes) for minutes in (120, 60, 10, 0)]

    with (
        patch("custom_components.haeo.diagnostics.collector.get_recorder_instance", return_value=mock_recorder),
        patch(
            "custom_components.haeo.diagnostics.collector.get_significant_states_full",
            return_value={
                "sensor.battery_capacity": [State("sensor.battery_capacity", "5000", {"unit_of_measurement": "Wh"})],
                "calendar.runs": [State("calendar.runs", "on", {})],
            },
        ),
        patch("custom_components.haeo.diagnostics.collector.element_inputs", return_value=[meter_input]),
        patch(
            "custom_components.haeo.diagnostics.collector.async_fetch_calendar_events", AsyncMock(return_value=[run])
        ),
        patch("custom_components.haeo.diagnostics.collector.async_meter_totals_at", AsyncMock(return_value=week)),
    ):
        inputs, _missing = await _fetch_inputs_at(hass, entry, target)

    capacity = next(inp for inp in inputs if inp["entity_id"] == "sensor.battery_capacity")["attributes"]
    assert isinstance(capacity, Mapping)
    assert capacity[METER_TOTALS_ATTRIBUTE] == [week[1], week[-1]]
