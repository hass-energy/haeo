"""Test the HAEO integration."""

import asyncio
from collections.abc import Iterable
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar
from unittest.mock import AsyncMock, Mock

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, UrlManager
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigSubentry
from homeassistant.const import EVENT_COMPONENT_LOADED, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import async_get_integration
from homeassistant.setup import ATTR_COMPONENT
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo import (
    CARD_STATIC_DIR,
    INPUT_PLATFORMS,
    MIGRATION_MINOR_VERSION,
    OUTPUT_PLATFORMS,
    HaeoRuntimeData,
    _async_first_refresh,
    _async_register_static_frontend_resources,
    _element_flow_in_progress,
    _ensure_required_subentries,
    async_remove_config_entry_device,
    async_remove_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    async_update_listener,
    card_static_url,
)
from custom_components.haeo.const import (
    CONF_INTEGRATION_TYPE,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    INTEGRATION_TYPE_HUB,
    STATIC_CARD_BUNDLES,
    STATIC_CARD_STATIC_DIR,
    STATIC_CARD_STATIC_PATH,
)
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    CONF_NAME,
    HORIZON_PRESET_2_DAYS,
)
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType, map_element_references
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    SECTION_LIMITS,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.elements.buffer import (
    CONF_KIND,
    CONF_LOADS,
    CONF_STORAGE,
    KIND_RESERVE,
    SECTION_PARTICIPANTS,
)
from custom_components.haeo.core.schema.elements.connection import CONF_SOURCE, CONF_TARGET, SECTION_ENDPOINTS
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_PRICE, CONF_RULES
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON
from custom_components.haeo.repairs import create_node_replaced_by_junction_issue
from custom_components.haeo.util import (
    missing_element_references,
    remove_deleted_elements_rules,
    rename_element_references,
)


@pytest.fixture
def mock_hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock hub config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Network",
                CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS),
            },
            HUB_SECTION_ADVANCED: {},
        },
        entry_id="hub_entry_id",
        title="Test HAEO Integration",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_battery_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock battery subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.BATTERY,
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: as_connection_target("Switchboard"),
                SECTION_STORAGE: {
                    CONF_CAPACITY: as_constant_value(10000.0),
                    CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_charge"]),
                },
                SECTION_LIMITS: {},
                SECTION_POWER_LIMITS: {},
                SECTION_PRICING: {
                    CONF_SALVAGE_VALUE: as_constant_value(0.0),
                },
                SECTION_EFFICIENCY: {},
            }
        ),
        subentry_type=ElementType.BATTERY,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_grid_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock grid subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.GRID,
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: as_connection_target("Switchboard"),
                SECTION_PRICING: {
                    CONF_PRICE_SOURCE_TARGET: as_entity_value(["sensor.import_price"]),
                    CONF_PRICE_TARGET_SOURCE: as_entity_value(["sensor.export_price"]),
                },
                SECTION_POWER_LIMITS: {
                    CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10000.0),
                    CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5000.0),
                },
            }
        ),
        subentry_type=ElementType.GRID,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_connection_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock connection subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.CONNECTION,
                CONF_NAME: "Battery to Grid",
                SECTION_ENDPOINTS: {
                    CONF_SOURCE: as_connection_target("Test Battery"),
                    CONF_TARGET: as_connection_target("Test Grid"),
                },
                SECTION_POWER_LIMITS: {},
                SECTION_PRICING: {},
                SECTION_EFFICIENCY: {},
            }
        ),
        subentry_type=ElementType.CONNECTION,
        title="Battery to Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


def _create_mock_horizon_manager() -> Mock:
    """Create a mock horizon manager for tests."""
    horizon = Mock()
    horizon.get_forecast_timestamps.return_value = (1000.0, 2000.0, 3000.0)
    horizon.subscribe.return_value = Mock()  # Unsubscribe callback
    return horizon


def _create_mock_runtime_data(coordinator: Mock) -> HaeoRuntimeData:
    """Create mock runtime data with horizon manager and coordinator."""
    horizon = _create_mock_horizon_manager()
    return HaeoRuntimeData(horizon_manager=horizon, coordinator=coordinator)


@pytest.mark.parametrize("platforms_unloaded", [True, False], ids=["unloaded", "unload_failed"])
async def test_unload_hub_entry_reports_platform_unload(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    platforms_unloaded: bool,
) -> None:
    """Unloading unloads every input and output platform and reports whether that succeeded."""
    mock_hub_entry.runtime_data = _create_mock_runtime_data(Mock())
    unload_platforms = AsyncMock(return_value=platforms_unloaded)
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", unload_platforms)

    result = await async_unload_entry(hass, mock_hub_entry)

    assert result is platforms_unloaded
    unload_platforms.assert_awaited_once_with(mock_hub_entry, [*INPUT_PLATFORMS, *OUTPUT_PLATFORMS])
    assert (mock_hub_entry.runtime_data is None) is platforms_unloaded


async def test_remove_hub_entry_dismisses_its_repair_issues(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry
) -> None:
    """Removing a hub entry dismisses the repair issues raised for it."""
    create_node_replaced_by_junction_issue(hass, mock_hub_entry.entry_id, "Switchboard")

    await async_remove_entry(hass, mock_hub_entry)

    assert not ir.async_get(hass).issues


async def test_async_setup_entry_initializes_coordinator(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setup should create a coordinator, perform initial refresh, and forward platforms."""

    class DummyCoordinator:
        def __init__(self, hass_param: HomeAssistant, entry_param: ConfigEntry) -> None:
            super().__init__()
            self.hass = hass_param
            self.config_entry = entry_param
            self.async_initialize = AsyncMock()
            self.async_refresh = AsyncMock()
            self.cleanup = Mock()
            self.auto_optimize_enabled = True

    created: list[DummyCoordinator] = []

    def create_coordinator(hass_param: HomeAssistant, entry_param: ConfigEntry) -> DummyCoordinator:
        coordinator = DummyCoordinator(hass_param, entry_param)
        created.append(coordinator)
        return coordinator

    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", create_coordinator)

    forward_mock = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward_mock)

    # No input stores to wait for in this test
    monkeypatch.setattr("custom_components.haeo.build_input_stores", lambda *_args, **_kwargs: {})

    result = await async_setup_entry(hass, mock_hub_entry)

    assert result is True
    assert created, "Coordinator should be instantiated"
    coordinator = created[0]
    runtime_data = mock_hub_entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.coordinator is coordinator
    coordinator.async_initialize.assert_awaited_once()
    coordinator.async_refresh.assert_awaited_once()
    # forward_mock is called twice: once for INPUT_PLATFORMS, once for OUTPUT_PLATFORMS
    assert forward_mock.await_count == 2


async def test_ensure_required_subentries_network_already_exists(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry
) -> None:
    """Test that _ensure_required_subentries skips network if already exists."""
    # First, create a network subentry
    network_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_NAME: "Network", CONF_ELEMENT_TYPE: "network"}),
        subentry_type="network",
        title="Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, network_subentry)

    # Call ensure again - should skip creating another one
    await _ensure_required_subentries(hass, mock_hub_entry)

    # Count network subentries - should still be only 1
    network_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == "network")
    assert network_count == 1


async def test_ensure_required_subentries_creates_network(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test that _ensure_required_subentries creates network if missing."""
    # Verify no network subentry exists initially
    network_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == "network")
    assert network_count == 0

    # Call ensure - should create one
    await _ensure_required_subentries(hass, mock_hub_entry)

    # Verify network subentry was created
    network_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == "network")
    assert network_count == 1


@pytest.mark.parametrize(
    "existing_type",
    [None, ElementType.JUNCTION, ElementType.NODE],
    ids=["creates_switchboard", "skips_existing_junction", "skips_existing_node"],
)
async def test_ensure_required_subentries_switchboard_handling(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    existing_type: ElementType | None,
) -> None:
    """_ensure_required_subentries creates a switchboard junction only when no junction or node exists."""
    if existing_type is not None:
        hass.config_entries.async_add_subentry(
            mock_hub_entry,
            ConfigSubentry(
                data=MappingProxyType({CONF_ELEMENT_TYPE: existing_type, CONF_NAME: "Existing"}),
                subentry_type=existing_type,
                title="Existing",
                unique_id=None,
            ),
        )

    await _ensure_required_subentries(hass, mock_hub_entry)

    hub_points = [
        sub
        for sub in mock_hub_entry.subentries.values()
        if sub.subentry_type in (ElementType.JUNCTION, ElementType.NODE)
    ]
    assert len(hub_points) == 1
    if existing_type is None:
        assert hub_points[0].subentry_type == ElementType.JUNCTION
        assert dict(hub_points[0].data) == {CONF_ELEMENT_TYPE: ElementType.JUNCTION, CONF_NAME: "Switchboard"}


async def test_ensure_required_subentries_skips_switchboard_advanced_mode(
    hass: HomeAssistant,
) -> None:
    """Test that _ensure_required_subentries does not create switchboard in advanced mode."""
    advanced_hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Test Network",
                CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS),
            },
            HUB_SECTION_ADVANCED: {CONF_ADVANCED_MODE: True},
        },
        entry_id="hub_entry_id",
        title="Test HAEO Integration",
    )
    advanced_hub_entry.add_to_hass(hass)

    await _ensure_required_subentries(hass, advanced_hub_entry)

    assert not any(sub.subentry_type == ElementType.JUNCTION for sub in advanced_hub_entry.subentries.values())


async def test_async_update_listener(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Test async_update_listener schedules reload."""
    # Set up runtime_data (required by async_update_listener)
    mock_coordinator = Mock()
    mock_hub_entry.runtime_data = _create_mock_runtime_data(mock_coordinator)

    # Mock the schedule_reload function
    schedule_reload_called = False

    def mock_schedule_reload(entry_id: str) -> None:
        nonlocal schedule_reload_called
        schedule_reload_called = True

    hass.config_entries.async_schedule_reload = mock_schedule_reload

    # Call update listener
    await async_update_listener(hass, mock_hub_entry)

    # Verify reload was scheduled
    assert schedule_reload_called


async def test_async_remove_config_entry_device(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test device removal when config entry is removed."""
    device_registry = dr.async_get(hass)

    # Create a device for an element
    device = device_registry.async_get_or_create(
        config_entry_id=mock_hub_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_hub_entry.entry_id}_test_battery")},
        name="Test Battery",
    )

    # Device exists, so removal should be allowed
    result = await async_remove_config_entry_device(hass, mock_hub_entry, device)
    assert result is True

    # Now remove the device from registry
    device_registry.async_remove_device(device.id)

    # Try to remove again - device already gone, should return False
    result = await async_remove_config_entry_device(hass, mock_hub_entry, device)
    assert result is False


@pytest.mark.parametrize(
    ("with_coordinator", "expect_signal"),
    [
        pytest.param(True, True, id="with_coordinator"),
        pytest.param(False, False, id="no_coordinator"),
    ],
)
async def test_async_update_listener_value_update_in_progress(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    with_coordinator: bool,
    expect_signal: bool,
) -> None:
    """async_update_listener clears the flag and skips reload during value updates."""
    mock_coordinator = Mock() if with_coordinator else None
    mock_hub_entry.runtime_data = HaeoRuntimeData(
        horizon_manager=_create_mock_horizon_manager(),
        coordinator=mock_coordinator,
        value_update_in_progress=True,
    )

    schedule_reload_called = False

    def mock_schedule_reload(entry_id: str) -> None:
        nonlocal schedule_reload_called
        schedule_reload_called = True

    hass.config_entries.async_schedule_reload = mock_schedule_reload

    await async_update_listener(hass, mock_hub_entry)

    assert mock_hub_entry.runtime_data.value_update_in_progress is False
    assert not schedule_reload_called
    if expect_signal:
        assert mock_coordinator is not None
        mock_coordinator.signal_optimization_stale.assert_called_once()


def _mock_element_flow_in_progress(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Mark a subentry config flow as in progress for *entry*."""
    hass.config_entries.subentries.async_progress = Mock(
        return_value=[{"handler": (entry.entry_id, "battery")}],
    )


async def test_async_update_listener_defers_reload_during_element_flow(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Reload is deferred to the next loop iteration while an element flow commits subentries."""
    mock_hub_entry.runtime_data = _create_mock_runtime_data(Mock())
    _mock_element_flow_in_progress(hass, mock_hub_entry)

    schedule_reload_calls: list[str] = []
    hass.config_entries.async_schedule_reload = lambda entry_id: schedule_reload_calls.append(entry_id)

    await async_update_listener(hass, mock_hub_entry)

    assert schedule_reload_calls == []
    assert mock_hub_entry.runtime_data.reload_pending is True

    await hass.async_block_till_done()

    assert mock_hub_entry.runtime_data.reload_pending is False
    assert schedule_reload_calls == [mock_hub_entry.entry_id]


async def test_async_update_listener_coalesces_deferred_reload(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Further update events during a flow only schedule one deferred reload."""
    mock_hub_entry.runtime_data = _create_mock_runtime_data(Mock())
    mock_hub_entry.runtime_data.reload_pending = True
    _mock_element_flow_in_progress(hass, mock_hub_entry)

    schedule_reload = Mock()
    hass.config_entries.async_schedule_reload = schedule_reload

    await async_update_listener(hass, mock_hub_entry)
    await hass.async_block_till_done()

    schedule_reload.assert_not_called()
    assert mock_hub_entry.runtime_data.reload_pending is True


async def test_async_update_listener_defers_reload_without_runtime_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Deferred reload still runs when runtime_data is not yet populated."""
    mock_hub_entry.runtime_data = None
    _mock_element_flow_in_progress(hass, mock_hub_entry)

    schedule_reload_calls: list[str] = []
    hass.config_entries.async_schedule_reload = lambda entry_id: schedule_reload_calls.append(entry_id)

    await async_update_listener(hass, mock_hub_entry)

    assert schedule_reload_calls == []

    await hass.async_block_till_done()

    assert schedule_reload_calls == [mock_hub_entry.entry_id]


async def test_element_flow_in_progress(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Element flow detection matches subentry flows owned by the config entry."""
    hass.config_entries.subentries.async_progress = Mock(
        return_value=[{"handler": (mock_hub_entry.entry_id, "battery")}],
    )

    assert _element_flow_in_progress(hass, mock_hub_entry) is True

    hass.config_entries.subentries.async_progress = Mock(return_value=[])
    assert _element_flow_in_progress(hass, mock_hub_entry) is False


@pytest.mark.parametrize(
    ("input_error", "expected_translation_key", "expected_issues"),
    [
        pytest.param(
            None, "input_unavailable", ["unavailable_input_{entry_id}_Test Element_section.field"], id="unavailable"
        ),
        pytest.param(
            InputError(translation_key="negative_input_value", translation_placeholders={"value": "-4.5"}),
            "negative_input_value",
            [],
            id="input_error",
        ),
    ],
)
async def test_async_setup_entry_raises_config_entry_not_ready_on_timeout(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    input_error: InputError | None,
    expected_translation_key: str,
    expected_issues: list[str],
) -> None:
    """Setup raises ConfigEntryNotReady when input stores don't become ready in time.

    An input with no reading names its sensors in the error and in a repair
    issue. A store that rejected its source's value reports that check's
    translation instead. Cleanup is handled via async_on_unload callbacks
    registered during setup.
    """

    # Create a mock input store that never becomes ready
    class NeverReadyStore:
        source_entity_ids: ClassVar[list[str]] = ["sensor.limit", "sensor.other"]
        unavailable_sources = ("sensor.limit",)
        available = False

        def __init__(self) -> None:
            self.error = input_error

        async def wait_settled(self) -> None:
            # A store that rejected its value settles at once; one with no data never does
            if self.error is None:
                await asyncio.sleep(100)

        def is_ready(self) -> bool:
            return False

        def load(self, _sm: object) -> bool:
            return False

    # Create mock horizon manager
    mock_horizon = _create_mock_horizon_manager()

    never_ready_store = NeverReadyStore()

    class MockRuntimeData:
        def __init__(self) -> None:
            self.horizon_manager = mock_horizon
            self.input_stores: dict[object, object] = {}
            self.coordinator = None
            self.value_update_in_progress = False

    # Patch HaeoRuntimeData to return our mock
    def create_mock_runtime_data(horizon_manager: object) -> MockRuntimeData:
        return MockRuntimeData()

    # Patch the module-level imports to bypass normal setup
    monkeypatch.setattr("custom_components.haeo.HaeoRuntimeData", create_mock_runtime_data)

    # Patch store construction so the never-ready store is the one awaited
    monkeypatch.setattr(
        "custom_components.haeo.build_input_stores",
        lambda *_args, **_kwargs: {("Test Element", ("section", "field")): never_ready_store},
    )

    # Patch forward_entry_setups to bypass real platform setup
    async def mock_forward_setups(entry: object, platforms: list[object]) -> None:
        pass

    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", mock_forward_setups)

    # Patch asyncio.timeout to use a very short timeout
    original_timeout = asyncio.timeout

    def short_timeout(seconds: float) -> asyncio.Timeout:
        return original_timeout(0.01)  # 10ms timeout

    monkeypatch.setattr("asyncio.timeout", short_timeout)

    # Run setup - should raise ConfigEntryNotReady
    with pytest.raises(ConfigEntryNotReady) as exc_info:
        await async_setup_entry(hass, mock_hub_entry)

    # Verify the exception has the correct translation key
    assert exc_info.value.translation_key == expected_translation_key
    assert exc_info.value.translation_placeholders == {
        "element": "Test Element",
        "field": "section.field",
        "entities": "sensor.limit, sensor.other" if input_error else "sensor.limit",
        **({"value": "-4.5"} if input_error else {}),
    }
    assert [issue_id for _, issue_id in ir.async_get(hass).issues if issue_id.startswith("unavailable_input_")] == [
        issue_id.format(entry_id=mock_hub_entry.entry_id) for issue_id in expected_issues
    ]

    # Note: Platform cleanup is handled via async_on_unload callbacks.
    # When testing directly (not via hass.config_entries.async_setup), the HA
    # lifecycle that calls _async_process_on_unload is not exercised.
    # The async_on_unload mechanism is tested separately via the HA test framework.


async def test_first_refresh_continues_when_the_last_input_settles_as_the_wait_times_out(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An input that becomes ready while the timed-out wait is being cancelled lets setup carry on.

    The timeout cancels the wait, and the input's sensor can report in the loop
    iteration before the cancellation lands, so no input is left to report.
    """

    class SettlesOnCancelStore:
        source_entity_ids: ClassVar[list[str]] = ["sensor.solar_forecast"]
        unavailable_sources = ()
        error = None

        def __init__(self) -> None:
            self.ready = False

        async def wait_settled(self) -> None:
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                self.ready = True
                raise

        def is_ready(self) -> bool:
            return self.ready

    runtime_data = Mock(input_stores={("Solar", ("forecast", "forecast")): SettlesOnCancelStore()})
    coordinator = Mock(async_initialize=AsyncMock(), async_refresh=AsyncMock())
    original_timeout = asyncio.timeout
    monkeypatch.setattr("asyncio.timeout", lambda _seconds: original_timeout(0.01))

    await _async_first_refresh(hass, mock_hub_entry, runtime_data, coordinator)

    coordinator.async_refresh.assert_awaited_once()


async def test_setup_reentry_after_timeout_failure(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After setup fails with timeout, re-running setup on same entry succeeds.

    This tests the robustness of cleanup on failure - if cleanup is incomplete,
    the second setup attempt would fail with 'entity already exists' or similar.
    """
    attempt_count = 0

    # Create a mock input store that fails first time, succeeds second time
    class ConditionalReadyStore:
        source_entity_ids: ClassVar[list[str]] = ["sensor.limit"]
        unavailable_sources = ("sensor.limit",)
        error = None

        def __init__(self) -> None:
            self._ready = False

        @property
        def available(self) -> bool:
            return self._ready

        async def wait_settled(self) -> None:
            if attempt_count == 1:
                # First attempt: timeout
                await asyncio.sleep(100)
            else:
                # Subsequent attempts: succeed immediately
                self._ready = True

        def is_ready(self) -> bool:
            return self._ready

        def load(self, _sm: object) -> bool:
            return False

    # Create a runtime data factory that uses our conditional store
    store = ConditionalReadyStore()

    class MockRuntimeData:
        def __init__(self, horizon_manager: object) -> None:
            self.horizon_manager = horizon_manager
            self.input_stores: dict[object, object] = {}
            self.coordinator = None
            self.value_update_in_progress = False

    monkeypatch.setattr("custom_components.haeo.HaeoRuntimeData", MockRuntimeData)
    monkeypatch.setattr("custom_components.haeo.build_input_stores", lambda *_args, **_kwargs: {})

    # Patch store construction so the conditional store is the one awaited
    monkeypatch.setattr(
        "custom_components.haeo.build_input_stores",
        lambda *_args, **_kwargs: {("Test Element", ("section", "field")): store},
    )

    # Mock horizon manager - use a real-like one that tracks state
    def create_horizon_manager(hass: HomeAssistant, config_entry: ConfigEntry) -> Mock:
        return _create_mock_horizon_manager()

    monkeypatch.setattr("custom_components.haeo.HorizonManager", create_horizon_manager)

    # Patch forward_entry_setups - no-op for this test
    async def mock_forward_setups(entry: object, platforms: list[object]) -> None:
        pass

    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", mock_forward_setups)

    # Patch asyncio.timeout to use a very short timeout
    original_timeout = asyncio.timeout

    def short_timeout(seconds: float) -> asyncio.Timeout:
        return original_timeout(0.01)  # 10ms timeout

    monkeypatch.setattr("asyncio.timeout", short_timeout)

    # First attempt - should fail with timeout
    attempt_count = 1
    with pytest.raises(ConfigEntryNotReady) as exc_info:
        await async_setup_entry(hass, mock_hub_entry)

    # Verify the exception has the correct translation key
    assert exc_info.value.translation_key == "input_unavailable"

    # Restore normal timeout for second attempt
    monkeypatch.setattr("asyncio.timeout", original_timeout)

    # Mock coordinator for second attempt
    class DummyCoordinator:
        def __init__(self, hass_param: HomeAssistant, entry_param: ConfigEntry) -> None:
            self.hass = hass_param
            self.config_entry = entry_param
            self.async_initialize = AsyncMock()
            self.async_refresh = AsyncMock()
            self.cleanup = Mock()
            self.auto_optimize_enabled = True

    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", DummyCoordinator)

    # Second attempt - should succeed (cleanup on first failure was complete)
    attempt_count = 2
    result = await async_setup_entry(hass, mock_hub_entry)

    assert result is True, "Second setup attempt should succeed after cleanup"


class _FailingCoordinator:
    """A coordinator whose initialization raises the error it was given."""

    def __init__(self, error: Exception) -> None:
        self.auto_optimize_enabled = True
        self.error = error

    def cleanup(self) -> None:
        pass

    async def async_initialize(self) -> None:
        raise self.error

    async def async_refresh(self) -> None:
        pass


@pytest.mark.parametrize(
    ("failing", "error", "expected_error"),
    [
        pytest.param("coordinator", RuntimeError("solver crashed"), "RuntimeError: solver crashed", id="runtime_error"),
        pytest.param("coordinator", ValueError("bad value"), "ValueError: bad value", id="value_error"),
        pytest.param("coordinator", KeyError("missing"), "KeyError: 'missing'", id="key_error"),
        pytest.param("stores", TypeError("odd config"), "TypeError: odd config", id="building_stores"),
    ],
)
async def test_unexpected_setup_failure_retries_with_a_repair_issue(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    failing: str,
    error: Exception,
    expected_error: str,
) -> None:
    """Any unexpected setup error is retried and raises an issue that clears once setup succeeds."""
    monkeypatch.setattr("custom_components.haeo.HorizonManager", lambda **_kwargs: _create_mock_horizon_manager())

    def build_stores(*_args: object, **_kwargs: object) -> dict[object, object]:
        if failing == "stores":
            raise error
        return {}

    monkeypatch.setattr("custom_components.haeo.build_input_stores", build_stores)
    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", lambda *_args: _FailingCoordinator(error))

    async def forward_setups(_entry: ConfigEntry, _platforms: Iterable[Platform | str]) -> None:
        pass

    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward_setups)
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True))

    with pytest.raises(ConfigEntryNotReady) as exc_info:
        await async_setup_entry(hass, mock_hub_entry)

    assert exc_info.value.translation_key == "setup_failed"
    assert exc_info.value.translation_placeholders == {"error": expected_error}
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"setup_failed_{mock_hub_entry.entry_id}")
    assert issue is not None
    assert issue.translation_placeholders == {"error": expected_error}

    failing = "nothing"
    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", _ReadyCoordinator)

    assert await async_setup_entry(hass, mock_hub_entry) is True
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"setup_failed_{mock_hub_entry.entry_id}") is None


async def test_config_change_retries_failed_setup_at_once(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A config change made while setup waits to retry retries it straight away, and only once."""
    attempts: list[bool] = []

    async def setup(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
        attempts.append(True)
        if len(attempts) == 1:
            msg = "Bus not found"
            raise ValueError(msg)

    monkeypatch.setattr("custom_components.haeo._async_setup_entry", setup)
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True))

    assert not await hass.config_entries.async_setup(mock_hub_entry.entry_id)
    assert mock_hub_entry.state is ConfigEntryState.SETUP_RETRY

    add_participant(hass, mock_hub_entry, "Bus")
    add_participant(hass, mock_hub_entry, "Other Bus")
    await hass.async_block_till_done()

    assert mock_hub_entry.state is ConfigEntryState.LOADED
    assert len(attempts) == 2

    # Once setup succeeds the retry listener is gone, so a later change does not retry setup again
    add_participant(hass, mock_hub_entry, "Third Bus")
    await hass.async_block_till_done()
    assert len(attempts) == 2


async def test_repeated_setup_failure_logs_once_and_clears_when_the_cause_changes(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    haeo_caplog: pytest.LogCaptureFixture,
) -> None:
    """A repeated setup error logs its traceback once, and its issue clears once a retry waits on something else."""
    monkeypatch.setattr("custom_components.haeo.HorizonManager", lambda **_kwargs: _create_mock_horizon_manager())
    monkeypatch.setattr("custom_components.haeo.build_input_stores", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True))
    error: Exception = ValueError("bad value")
    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", lambda *_args: _FailingCoordinator(error))
    issue_id = f"setup_failed_{mock_hub_entry.entry_id}"

    for _ in range(2):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_hub_entry)

    assert [record.exc_info is not None for record in haeo_caplog.records if "setup failed" in record.message] == [
        True,
        False,
    ]
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

    error = ConfigEntryNotReady(
        translation_domain=DOMAIN,
        translation_key="horizon_entity_not_ready",
        translation_placeholders={"entity_id": "sensor.horizon"},
    )
    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, mock_hub_entry)

    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_setup_preserves_config_entry_not_ready_exception(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setup preserves ConfigEntryNotReady with original translation keys.

    When coordinator raises ConfigEntryNotReady with specific translation keys,
    the exception should be re-raised as-is rather than being wrapped.
    """
    # Mock horizon manager
    monkeypatch.setattr("custom_components.haeo.HorizonManager", lambda **_kwargs: _create_mock_horizon_manager())

    # Create a runtime data with ready entities
    class MockRuntimeData:
        def __init__(self, horizon_manager: object) -> None:
            self.horizon_manager = horizon_manager
            self.input_stores: dict[object, object] = {}  # No stores to wait for
            self.coordinator = None
            self.value_update_in_progress = False

    monkeypatch.setattr("custom_components.haeo.HaeoRuntimeData", MockRuntimeData)
    monkeypatch.setattr("custom_components.haeo.build_input_stores", lambda *_args, **_kwargs: {})

    # Patch forward_entry_setups
    async def mock_forward_setups(entry: ConfigEntry, platforms: Iterable[Platform | str]) -> None:
        pass

    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", mock_forward_setups)

    unload_platforms = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", unload_platforms)

    # Mock coordinator that raises ConfigEntryNotReady with custom translation key
    class FailingCoordinator:
        def __init__(self, _hass: HomeAssistant, _entry: ConfigEntry) -> None:
            self.auto_optimize_enabled = True

        def cleanup(self) -> None:
            pass

        async def async_initialize(self) -> None:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="horizon_entity_not_ready",
                translation_placeholders={"entity_id": "sensor.horizon"},
            )

    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", FailingCoordinator)

    # Run setup - should raise the original ConfigEntryNotReady with preserved translation key
    with pytest.raises(ConfigEntryNotReady) as exc_info:
        await async_setup_entry(hass, mock_hub_entry)

    # The original translation key is preserved rather than wrapped in setup_failed
    assert exc_info.value.translation_key == "horizon_entity_not_ready"
    # The input platforms forwarded before the failure are unloaded again
    unload_platforms.assert_awaited_once_with(mock_hub_entry, INPUT_PLATFORMS)


class _InterruptedCoordinator:
    """A coordinator whose first refresh is cancelled."""

    def __init__(self, _hass: HomeAssistant, _entry: ConfigEntry) -> None:
        self.auto_optimize_enabled = True

    def cleanup(self) -> None:
        pass

    async def async_initialize(self) -> None:
        raise asyncio.CancelledError

    async def async_refresh(self) -> None:
        pass


class _ReadyCoordinator(_InterruptedCoordinator):
    """A coordinator whose first refresh succeeds."""

    async def async_initialize(self) -> None:
        pass


@pytest.mark.parametrize(
    ("coordinator_class", "failing_platforms", "expected_error"),
    [
        pytest.param(_InterruptedCoordinator, [], asyncio.CancelledError, id="first_refresh_cancelled"),
        pytest.param(_ReadyCoordinator, OUTPUT_PLATFORMS, ConfigEntryNotReady, id="output_forward_failed"),
    ],
)
async def test_setup_failure_after_input_platforms_unloads_them(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    coordinator_class: type[_InterruptedCoordinator],
    failing_platforms: list[Platform],
    expected_error: type[BaseException],
) -> None:
    """Any failure once the input platforms are forwarded unloads them exactly once."""
    monkeypatch.setattr("custom_components.haeo.HorizonManager", lambda **_kwargs: _create_mock_horizon_manager())
    monkeypatch.setattr("custom_components.haeo.build_input_stores", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", coordinator_class)

    async def forward_setups(_entry: ConfigEntry, platforms: Iterable[Platform | str]) -> None:
        if list(platforms) == failing_platforms:
            msg = "platform setup failed"
            raise RuntimeError(msg)

    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward_setups)
    unload_platforms = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", unload_platforms)

    with pytest.raises(expected_error):
        await async_setup_entry(hass, mock_hub_entry)

    unload_platforms.assert_awaited_once_with(mock_hub_entry, INPUT_PLATFORMS)


# ---------------------------------------------------------------------------
# async_setup / frontend static registration
# ---------------------------------------------------------------------------


async def test_async_setup_registers_static_frontend_resource(hass: HomeAssistant) -> None:
    """Test that async_setup serves the bundles under a versioned URL with cache headers."""
    mock_http = Mock()
    mock_http.async_register_static_paths = AsyncMock()
    hass.http = mock_http  # type: ignore[attr-defined]
    # Frontend has already completed its own setup, so its registry exists.
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *_: None, [])
    hass.config.components.add("frontend")

    result = await async_setup(hass, {})
    await hass.async_block_till_done()

    assert result is True
    mock_http.async_register_static_paths.assert_called_once()
    configs: list[StaticPathConfig] = mock_http.async_register_static_paths.call_args[0][0]
    assert len(configs) == 1
    static_url = card_static_url(CARD_STATIC_DIR)
    assert configs[0].url_path == static_url
    assert configs[0].path.endswith(STATIC_CARD_STATIC_DIR)
    assert configs[0].cache_headers is True
    assert hass.data[DATA_EXTRA_MODULE_URL].urls == {f"{static_url}/{name}" for name in STATIC_CARD_BUNDLES}


async def test_async_setup_registers_static_urls_when_frontend_sets_up_later(hass: HomeAssistant) -> None:
    """Test that card URLs register even when HAEO's setup wins the race against frontend.

    Regression test for the startup ordering race where HAEO is set up before the
    frontend component creates hass.data[DATA_EXTRA_MODULE_URL]. Setup must not
    raise KeyError, and the cards must still be registered once frontend appears
    rather than being silently dropped until the next restart.
    """
    mock_http = Mock()
    mock_http.async_register_static_paths = AsyncMock()
    hass.http = mock_http  # type: ignore[attr-defined]
    # The frontend component has not run its own setup yet, so its registry is absent.
    assert DATA_EXTRA_MODULE_URL not in hass.data

    result = await async_setup(hass, {})

    assert result is True
    mock_http.async_register_static_paths.assert_called_once()

    # Frontend now finishes its setup: it creates the registry and announces itself.
    await async_get_integration(hass, "frontend")
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *_: None, [])
    hass.config.components.add("frontend")
    hass.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "frontend"})
    await hass.async_block_till_done()

    static_url = card_static_url(CARD_STATIC_DIR)
    assert hass.data[DATA_EXTRA_MODULE_URL].urls == {f"{static_url}/{name}" for name in STATIC_CARD_BUNDLES}


async def test_async_register_static_skips_when_http_unavailable(
    hass: HomeAssistant,
) -> None:
    """Test that static registration is skipped when HTTP component is not initialized."""
    # The test hass fixture has no http attribute - this exercises the getattr guard
    await _async_register_static_frontend_resources(hass)
    # No error raised - registration simply skipped


async def test_async_register_static_skips_when_card_not_found(
    hass: HomeAssistant,
) -> None:
    """Test that static registration is skipped when card bundle file is missing."""
    mock_http = Mock()
    mock_http.async_register_static_paths = AsyncMock()
    hass.http = mock_http  # type: ignore[attr-defined]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("custom_components.haeo.Path.exists", lambda _self: False)
        await _async_register_static_frontend_resources(hass)

    mock_http.async_register_static_paths.assert_not_called()


def test_card_static_url_changes_with_bundle_contents(tmp_path: Path) -> None:
    """Test that rebuilding a bundle moves the URL it is served under, so no cached copy goes stale."""
    (tmp_path / "haeo-forecast-card.min.js").write_text("a")
    (tmp_path / "haeo-forecast-card.forecast-card-controller.js").write_text("b")
    first = card_static_url(tmp_path)

    assert first.startswith(f"{STATIC_CARD_STATIC_PATH}/")
    assert card_static_url(tmp_path) == first

    (tmp_path / "haeo-forecast-card.forecast-card-controller.js").write_text("c")

    assert card_static_url(tmp_path) != first


def _add_subentry(hass: HomeAssistant, hub_entry: MockConfigEntry, data: dict[str, object]) -> ConfigSubentry:
    subentry = ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=str(data[CONF_ELEMENT_TYPE]),
        title=str(data[CONF_NAME]),
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _add_buffer(hass: HomeAssistant, hub_entry: MockConfigEntry, participants: dict[str, list[str]]) -> ConfigSubentry:
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.BUFFER,
                CONF_NAME: "Backup",
                CONF_KIND: KIND_RESERVE,
                SECTION_PARTICIPANTS: participants,
            }
        ),
        subentry_type=ElementType.BUFFER,
        title="Backup",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def test_rename_element_references_renames_buffer_participants(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry
) -> None:
    """Renaming an element renames it in every buffer that lists it."""
    subentry = _add_buffer(hass, mock_hub_entry, {CONF_LOADS: ["House"], CONF_STORAGE: ["Battery", "Spare"]})

    rename_element_references(hass, mock_hub_entry, "Battery", "Main Battery")

    assert mock_hub_entry.subentries[subentry.subentry_id].data[SECTION_PARTICIPANTS] == {
        CONF_LOADS: ["House"],
        CONF_STORAGE: ["Main Battery", "Spare"],
    }


def _rule(name: str, source: list[str] | None = None, target: list[str] | None = None) -> dict[str, object]:
    return {
        CONF_NAME: name,
        **({CONF_SOURCE: source} if source else {}),
        **({CONF_TARGET: target} if target else {}),
        CONF_PRICE: as_constant_value(0.1),
    }


RULES = [
    _rule("Battery charge cost", target=["Battery"]),
    _rule("Battery discharge cost", source=["Battery"]),
    _rule("Battery and solar out", source=["Battery", "Solar"]),
    _rule("Solar into battery", source=["Solar"], target=["Battery"]),
    _rule("House consumption cost", target=["House"]),
    _rule("Out of house", source=["House"]),
]


def _add_referencing_elements(hass: HomeAssistant, hub_entry: MockConfigEntry) -> list[ConfigSubentry]:
    """Add a load, battery, and solar, and the buffer, connection, and policy that name them."""
    add_participant(hass, hub_entry, "House", ElementType.LOAD)
    add_participant(hass, hub_entry, "Battery", ElementType.BATTERY)
    add_participant(hass, hub_entry, "Solar", ElementType.SOLAR)
    return [
        _add_buffer(hass, hub_entry, {CONF_LOADS: ["House"], CONF_STORAGE: ["Battery"]}),
        _add_subentry(
            hass,
            hub_entry,
            {
                CONF_ELEMENT_TYPE: ElementType.CONNECTION,
                CONF_NAME: "Link",
                SECTION_ENDPOINTS: {
                    CONF_SOURCE: as_connection_target("Battery"),
                    CONF_TARGET: as_connection_target("House"),
                },
            },
        ),
        _add_subentry(
            hass, hub_entry, {CONF_ELEMENT_TYPE: ElementType.POLICY, CONF_NAME: "Policies", CONF_RULES: RULES}
        ),
    ]


def _element(hub_entry: ConfigEntry, name: str) -> ConfigSubentry:
    return next(subentry for subentry in hub_entry.subentries.values() if subentry.title == name)


@pytest.mark.parametrize(
    ("deleted", "removed_rules", "missing"),
    [
        pytest.param(
            "Battery",
            {"Battery charge cost", "Battery discharge cost"},
            {"Backup": ["Battery"], "Link": ["Battery"], "Policies": ["Battery"]},
            id="battery",
        ),
        pytest.param(
            "House",
            {"House consumption cost"},
            {"Backup": ["House"], "Link": ["House"], "Policies": ["House"]},
            id="load",
        ),
        pytest.param("Solar", set(), {"Policies": ["Solar"]}, id="element_without_surfaced_prices"),
    ],
)
async def test_deleting_an_element_removes_only_its_own_pricing_rules(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    deleted: str,
    removed_rules: set[str],
    missing: dict[str, list[str]],
) -> None:
    """A deleted element takes the rules its form surfaces; everything else that names it stays and is reported."""
    schedule_reload = Mock()
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", schedule_reload)
    mock_hub_entry.runtime_data = None
    buffer, link, policy = _add_referencing_elements(hass, mock_hub_entry)
    remove_deleted_elements_rules(hass, mock_hub_entry)
    mock_hub_entry.add_update_listener(async_update_listener)

    hass.config_entries.async_remove_subentry(mock_hub_entry, _element(mock_hub_entry, deleted).subentry_id)
    await hass.async_block_till_done()

    schedule_reload.assert_called_with(mock_hub_entry.entry_id)
    assert mock_hub_entry.subentries[buffer.subentry_id].data == buffer.data
    assert mock_hub_entry.subentries[link.subentry_id].data == link.data
    assert mock_hub_entry.subentries[policy.subentry_id].data[CONF_RULES] == [
        rule for rule in RULES if rule[CONF_NAME] not in removed_rules
    ]
    assert missing_element_references(mock_hub_entry) == missing


def test_element_renamed_and_deleted_between_listener_runs_takes_its_rules(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry
) -> None:
    """A rename made while no update listener runs is remembered, so a later deletion finds the renamed rules."""
    *_, policy = _add_referencing_elements(hass, mock_hub_entry)
    remove_deleted_elements_rules(hass, mock_hub_entry)

    rename_element_references(hass, mock_hub_entry, "Battery", "Home Battery")
    hass.config_entries.async_update_subentry(mock_hub_entry, _element(mock_hub_entry, "Battery"), title="Home Battery")
    hass.config_entries.async_remove_subentry(mock_hub_entry, _element(mock_hub_entry, "Home Battery").subentry_id)
    remove_deleted_elements_rules(hass, mock_hub_entry)

    assert [rule[CONF_NAME] for rule in mock_hub_entry.subentries[policy.subentry_id].data[CONF_RULES]] == [
        rule[CONF_NAME] for rule in RULES if rule[CONF_NAME] not in {"Battery charge cost", "Battery discharge cost"}
    ]


async def test_renaming_an_element_keeps_its_pricing_rules_under_the_new_name(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rename is not a deletion, so the renamed element keeps its own rules."""
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", Mock())
    mock_hub_entry.runtime_data = None
    *_, policy = _add_referencing_elements(hass, mock_hub_entry)
    remove_deleted_elements_rules(hass, mock_hub_entry)
    mock_hub_entry.add_update_listener(async_update_listener)

    rename_element_references(hass, mock_hub_entry, "Battery", "Home Battery")
    hass.config_entries.async_update_subentry(mock_hub_entry, _element(mock_hub_entry, "Battery"), title="Home Battery")
    await hass.async_block_till_done()

    assert (
        mock_hub_entry.subentries[policy.subentry_id].data[CONF_RULES]
        == map_element_references(
            ElementType.POLICY, policy.data, lambda name: "Home Battery" if name == "Battery" else name
        )[CONF_RULES]
    )
    assert len(mock_hub_entry.subentries[policy.subentry_id].data[CONF_RULES]) == len(RULES)


async def test_removing_an_element_removes_its_entities(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Every entity is linked to its element's subentry, so deleting the element removes its entities."""
    hass.config_entries.async_update_entry(mock_hub_entry, minor_version=MIGRATION_MINOR_VERSION)
    grid = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.GRID,
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: as_connection_target("Switchboard"),
                SECTION_PRICING: {
                    CONF_PRICE_SOURCE_TARGET: as_constant_value(0.3),
                    CONF_PRICE_TARGET_SOURCE: as_constant_value(0.1),
                },
                SECTION_POWER_LIMITS: {},
            }
        ),
        subentry_type=ElementType.GRID,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, grid)
    assert await hass.config_entries.async_setup(mock_hub_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, mock_hub_entry.entry_id)
    network = next(s for s in mock_hub_entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK)
    linked = {entity.unique_id: entity.config_subentry_id for entity in entities}
    assert linked[f"{mock_hub_entry.entry_id}_auto_optimize"] == network.subentry_id
    assert linked[f"{mock_hub_entry.entry_id}_horizon"] == network.subentry_id
    grid_prefix = f"{mock_hub_entry.entry_id}_{grid.subentry_id}_"
    grid_entities = [entity for entity in entities if entity.unique_id.startswith(grid_prefix)]
    assert {entity.domain for entity in grid_entities} == {"number", "sensor"}
    assert {entity.config_subentry_id for entity in grid_entities} == {grid.subentry_id}

    hass.config_entries.async_remove_subentry(mock_hub_entry, grid.subentry_id)
    await hass.async_block_till_done()

    remaining = er.async_entries_for_config_entry(entity_registry, mock_hub_entry.entry_id)
    assert not [entity.unique_id for entity in remaining if entity.unique_id.startswith(grid_prefix)]


async def test_setup_succeeds_with_an_input_entity_disabled(hass: HomeAssistant) -> None:
    """An input loads from its config even while its entity is disabled, so setup still finishes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Home", CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS)},
            HUB_SECTION_ADVANCED: {},
        },
        version=1,
        minor_version=4,
    )
    entry.add_to_hass(hass)
    elements: tuple[dict[str, object], ...] = (
        {CONF_ELEMENT_TYPE: "junction", CONF_NAME: "Switchboard"},
        {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "Grid",
            CONF_CONNECTION: as_connection_target("Switchboard"),
            "power_limits": {
                "max_power_source_target": as_constant_value(10.0),
                "max_power_target_source": as_constant_value(5.0),
            },
            "pricing": {"price_source_target": as_constant_value(0.3), "price_target_source": as_constant_value(0.05)},
        },
        {
            CONF_ELEMENT_TYPE: "load",
            CONF_NAME: "Load",
            CONF_CONNECTION: as_connection_target("Switchboard"),
            "curtailment": {},
            "forecast": {"forecast": as_constant_value(1.0)},
            "pricing": {},
        },
    )
    for data in elements:
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType(data),
                subentry_type=str(data[CONF_ELEMENT_TYPE]),
                title=str(data[CONF_NAME]),
                unique_id=None,
            ),
        )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    registry = er.async_get(hass)
    load_forecast = next(
        reg_entry
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
        if reg_entry.domain == "number" and reg_entry.unique_id.endswith("forecast")
    )
    registry.async_update_entity(load_forecast.entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(load_forecast.entity_id) is None


def _hub_missing_inverter(hass: HomeAssistant) -> MockConfigEntry:
    """Return a hub whose load and connection name an "Inverter" it does not have."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Home", CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS)},
            HUB_SECTION_ADVANCED: {},
        },
        version=1,
        minor_version=MIGRATION_MINOR_VERSION,
    )
    entry.add_to_hass(hass)
    elements: tuple[dict[str, object], ...] = (
        {CONF_ELEMENT_TYPE: ElementType.JUNCTION, CONF_NAME: "Switchboard"},
        {
            CONF_ELEMENT_TYPE: ElementType.GRID,
            CONF_NAME: "Grid",
            CONF_CONNECTION: as_connection_target("Switchboard"),
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.3),
                CONF_PRICE_TARGET_SOURCE: as_constant_value(0.05),
            },
        },
        {
            CONF_ELEMENT_TYPE: ElementType.LOAD,
            CONF_NAME: "Load",
            CONF_CONNECTION: as_connection_target("Inverter"),
            "curtailment": {},
            "forecast": {"forecast": as_constant_value(1.0)},
            SECTION_PRICING: {},
        },
        {
            CONF_ELEMENT_TYPE: ElementType.CONNECTION,
            CONF_NAME: "Link",
            SECTION_ENDPOINTS: {
                CONF_SOURCE: as_connection_target("Inverter"),
                CONF_TARGET: as_connection_target("Switchboard"),
            },
            SECTION_POWER_LIMITS: {},
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {},
        },
        {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_NAME: "Policies",
            CONF_RULES: [
                {
                    CONF_NAME: "Load consumption cost",
                    CONF_ENABLED: True,
                    CONF_TARGET: ["Load"],
                    CONF_PRICE: as_constant_value(-0.1),
                }
            ],
        },
    )
    for data in elements:
        _add_subentry(hass, entry, dict(data))
    return entry


async def test_setup_waits_for_missing_elements_and_recovers_once_they_are_added(hass: HomeAssistant) -> None:
    """Elements naming a missing element stop setup with a repair issue until it is added again."""
    entry = _hub_missing_inverter(hass)
    issue_id = f"missing_element_references_{entry.entry_id}"

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {"references": "Link → Inverter\nLoad → Inverter"}
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"setup_failed_{entry.entry_id}") is None

    _add_subentry(hass, entry, {CONF_ELEMENT_TYPE: ElementType.JUNCTION, CONF_NAME: "Inverter"})
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_element_deleted_while_setup_waits_takes_its_pricing_rules_at_the_next_attempt(
    hass: HomeAssistant,
) -> None:
    """Setup removes the rules of an element deleted while no update listener was registered."""
    entry = _hub_missing_inverter(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY

    hass.config_entries.async_remove_subentry(entry, _element(entry, "Load").subentry_id)
    assert not await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert _element(entry, "Policies").data[CONF_RULES] == []
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"missing_element_references_{entry.entry_id}")
    assert issue is not None
    assert issue.translation_placeholders == {"references": "Link → Inverter"}
