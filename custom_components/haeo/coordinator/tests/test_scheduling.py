"""Tests for when the coordinator optimizes: debouncing, alignment, auto-optimize, and overlapping requests."""

import asyncio
from datetime import timedelta
import threading
import time
from typing import Any  # noqa: TID251  # Mock-typed test doubles (MagicMock spec=) and monkeypatched callback stand-ins
from unittest.mock import MagicMock, Mock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import EventStateChangedData
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.core.const import DEFAULT_DEBOUNCE_SECONDS

from .helpers import mock_horizon


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_horizon_change_triggers_optimization(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Horizon manager changes trigger optimization."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    network = Mock()
    coordinator._network = network

    with patch.object(coordinator, "signal_optimization_stale") as trigger_mock:
        coordinator._subscribe_to_input_stores()
        on_horizon_change = mock_horizon(mock_runtime_data).subscribe.call_args.args[0]
        on_horizon_change()

    trigger_mock.assert_called_once()
    network.update_periods.assert_not_called()


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_signal_optimization_stale_schedules_timer_in_cooldown(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Trigger schedules timer when within cooldown period."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._last_optimization_time = time.time() - 0.5  # 0.5 seconds ago
    coordinator._debounce_seconds = 5.0  # 5 second cooldown

    with patch("custom_components.haeo.coordinator.coordinator.async_call_later") as mock_timer:
        mock_timer.return_value = MagicMock()  # Return unsubscribe callback
        coordinator.signal_optimization_stale()

    assert coordinator._rerun_wanted is True
    mock_timer.assert_called_once()
    # Timer should be set for approximately 4.5 seconds remaining
    call_args = mock_timer.call_args
    assert call_args[0][0] is hass
    assert 4.0 < call_args[0][1] < 5.0


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_signal_optimization_stale_reuses_existing_timer(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Trigger reuses existing timer rather than scheduling new one."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._last_optimization_time = time.time() - 0.5
    coordinator._debounce_seconds = 5.0
    existing_timer = MagicMock()
    coordinator._debounce_timer = existing_timer

    with patch("custom_components.haeo.coordinator.coordinator.async_call_later") as mock_timer:
        coordinator.signal_optimization_stale()

    # Should not schedule new timer since one exists
    mock_timer.assert_not_called()
    assert coordinator._debounce_timer is existing_timer


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_debounce_timer_callback_clears_timer(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Debounce timer callback clears timer reference."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._debounce_timer = MagicMock()
    coordinator._rerun_wanted = False

    coordinator._debounce_timer_callback(dt_util.utcnow())

    assert coordinator._debounce_timer is None


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_store_listener_calls_handle_element_update(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Created store listener should call _handle_element_update with element name."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Create a store listener for "Test Battery"
    listener = coordinator._create_store_listener("Test Battery")

    # Mock _handle_element_update
    with patch.object(coordinator, "_handle_element_update") as handle_mock:
        # The store listener is a no-arg callback
        listener()

    # Verify _handle_element_update was called with correct element name
    handle_mock.assert_called_once_with("Test Battery")


# ===== Tests for auto-optimize control =====


def test_cleanup_clears_debounce_timer(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """cleanup() cancels debounce timer if set."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    mock_timer_unsub = MagicMock()
    coordinator._debounce_timer = mock_timer_unsub

    coordinator.cleanup()

    mock_timer_unsub.assert_called_once()
    assert coordinator._debounce_timer is None


def test_auto_optimize_enabled_raises_when_no_switch(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Auto-optimize raises error when no switch is available."""
    # Create runtime data without auto_optimize_switch
    # Avoid circular import with horizon module
    from custom_components.haeo.horizon import HorizonManager  # noqa: PLC0415

    mock_horizon: Any = MagicMock(spec=HorizonManager)
    mock_hub_entry.runtime_data = HaeoRuntimeData(horizon_manager=mock_horizon)

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    with pytest.raises(RuntimeError, match="auto_optimize_switch not available"):
        _ = coordinator.auto_optimize_enabled


def test_auto_optimize_enabled_reads_from_switch(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Auto-optimize reads state from the switch entity."""
    switch = mock_runtime_data.auto_optimize_switch
    assert switch is not None

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Switch is on by default in fixture
    assert coordinator.auto_optimize_enabled is True

    # Change switch to off
    switch.is_on = False
    assert coordinator.auto_optimize_enabled is False

    # Change switch back to on
    switch.is_on = True
    assert coordinator.auto_optimize_enabled is True


def test_signal_optimization_stale_skips_when_auto_optimize_disabled(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """signal_optimization_stale does nothing when auto-optimize is disabled."""
    switch = mock_runtime_data.auto_optimize_switch
    assert switch is not None

    # Set switch to off
    switch.is_on = False

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Call signal_optimization_stale - should return early due to auto_optimize_enabled=False
    coordinator.signal_optimization_stale()

    # State should remain unchanged (no pending refresh set, no timers scheduled)
    assert coordinator._rerun_wanted is False
    assert coordinator._debounce_timer is None


def test_apply_auto_optimize_state_pauses_horizon_manager(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """_apply_auto_optimize_state pauses horizon manager when disabled."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Apply disabled state
    coordinator._apply_auto_optimize_state(is_enabled=False)

    # Horizon manager pause should have been called
    mock_horizon(mock_runtime_data).pause.assert_called_once()


def test_apply_auto_optimize_state_resumes_horizon_manager(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """_apply_auto_optimize_state resumes horizon manager when enabled."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Apply enabled state
    coordinator._apply_auto_optimize_state(is_enabled=True)

    # Horizon manager resume should have been called
    mock_horizon(mock_runtime_data).resume.assert_called_once()


def test_handle_auto_optimize_switch_change_off_pauses(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """_handle_auto_optimize_switch_change pauses horizon when turned off."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Create mock event for switch turning OFF
    new_state = MagicMock(spec=State)
    new_state.state = STATE_OFF
    event_data: EventStateChangedData = {
        "entity_id": "switch.haeo_auto_optimize",
        "old_state": None,
        "new_state": new_state,
    }
    event = MagicMock()
    event.data = event_data

    coordinator._handle_auto_optimize_switch_change(event)

    # Should pause horizon manager
    mock_horizon(mock_runtime_data).pause.assert_called()


def test_handle_auto_optimize_switch_change_none_state_returns_early(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """_handle_auto_optimize_switch_change returns early when new_state is None."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Create mock event with None new_state
    event_data: EventStateChangedData = {
        "entity_id": "switch.haeo_auto_optimize",
        "old_state": None,
        "new_state": None,
    }
    event = MagicMock()
    event.data = event_data

    # Reset mock to track new calls
    mock_horizon(mock_runtime_data).reset_mock()

    coordinator._handle_auto_optimize_switch_change(event)

    # Should NOT have called pause or resume
    mock_horizon(mock_runtime_data).pause.assert_not_called()
    mock_horizon(mock_runtime_data).resume.assert_not_called()


@pytest.fixture
def live_runtime_data(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> HaeoRuntimeData:
    """Create runtime data with a real horizon manager, which notifies its subscribers, and auto-optimize on."""
    # Avoid circular import with entities and horizon modules
    from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch  # noqa: PLC0415
    from custom_components.haeo.horizon import HorizonManager  # noqa: PLC0415

    switch: Any = MagicMock(spec=AutoOptimizeSwitch)
    switch.is_on = True
    switch.entity_id = "switch.haeo_auto_optimize"
    runtime_data = HaeoRuntimeData(horizon_manager=HorizonManager(hass, mock_hub_entry), auto_optimize_switch=switch)
    mock_hub_entry.runtime_data = runtime_data
    return runtime_data


class BlockingSolves:
    """A network solve that blocks in the executor until released, recording how many solves overlap."""

    def __init__(self) -> None:
        """Start with the solve blocked."""
        self.release = threading.Event()
        self.calls = 0
        self.peak = 0
        self._running = 0
        self._lock = threading.Lock()

    def __call__(self) -> float:
        """Solve once the solve is released."""
        with self._lock:
            self.calls += 1
            self._running += 1
            self.peak = max(self.peak, self._running)
        self.release.wait(timeout=2)
        with self._lock:
            self._running -= 1
        return 0.0


@pytest.fixture
def solves() -> BlockingSolves:
    """Return the blocking solve of the network an initialized coordinator would build."""
    return BlockingSolves()


async def _initialized_coordinator(
    hass: HomeAssistant, entry: MockConfigEntry, solves: BlockingSolves
) -> HaeoDataUpdateCoordinator:
    """Return a coordinator initialized with a network that solves through ``solves``."""
    network = MagicMock()
    network.optimize = solves
    network.relaxations = ()
    network.elements = {}
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    with patch(
        "custom_components.haeo.coordinator.coordinator.build_network",
        return_value=(network, {}),
    ):
        await coordinator.async_initialize()
    return coordinator


async def _settle(hass: HomeAssistant, solves: BlockingSolves) -> None:
    """Let the optimizations started so far reach their solve, then release them all and wait for them."""
    await asyncio.sleep(0.1)
    solves.release.set()
    await hass.async_block_till_done()


@pytest.mark.usefixtures("live_runtime_data")
async def test_setup_runs_one_optimization(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, solves: BlockingSolves
) -> None:
    """Initializing and then refreshing, as setup does, runs one optimization rather than two."""
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    refresh = hass.async_create_task(coordinator.async_refresh())
    await _settle(hass, solves)
    await refresh

    assert (solves.calls, solves.peak) == (1, 1)
    coordinator.cleanup()


async def test_optimizations_requested_during_one_share_one_follow_up(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, live_runtime_data: HaeoRuntimeData, solves: BlockingSolves
) -> None:
    """Optimizations requested while one runs wait for it, then run once between them, never overlapping it."""
    switch: Any = live_runtime_data.auto_optimize_switch
    switch.is_on = False
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    hass.async_create_task(coordinator.async_refresh())
    await asyncio.sleep(0.1)
    requests = [hass.async_create_task(coordinator.async_run_optimization()) for _ in range(3)]
    requests.append(hass.async_create_task(coordinator.async_request_refresh()))
    await _settle(hass, solves)
    await asyncio.gather(*requests)

    assert (solves.calls, solves.peak) == (2, 1)
    coordinator.cleanup()


async def test_turning_auto_optimize_on_runs_one_optimization(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, live_runtime_data: HaeoRuntimeData, solves: BlockingSolves
) -> None:
    """Turning auto-optimize on catches up with one optimization."""
    switch: Any = live_runtime_data.auto_optimize_switch
    switch.is_on = False
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    switch.is_on = True
    coordinator._handle_auto_optimize_switch_change(_switch_event(STATE_ON))
    await _settle(hass, solves)

    assert solves.calls == 1
    coordinator.cleanup()


async def test_turning_auto_optimize_off_cancels_a_waiting_optimization(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, live_runtime_data: HaeoRuntimeData, solves: BlockingSolves
) -> None:
    """An optimization waiting out the debounce window does not run once auto-optimize is turned off."""
    switch: Any = live_runtime_data.auto_optimize_switch
    solves.release.set()
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    await coordinator.async_refresh()
    coordinator.signal_optimization_stale()
    switch.is_on = False
    coordinator._handle_auto_optimize_switch_change(_switch_event(STATE_OFF))
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=DEFAULT_DEBOUNCE_SECONDS + 1))
    await hass.async_block_till_done()

    assert solves.calls == 1
    coordinator.cleanup()


@pytest.mark.usefixtures("live_runtime_data")
async def test_optimizations_wait_for_inputs_to_align(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, solves: BlockingSolves
) -> None:
    """While forecast inputs load for a new horizon, refreshes skip and the optimize action says why."""
    solves.release.set()
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    with patch.object(coordinator, "_are_inputs_aligned", return_value=False):
        await coordinator.async_refresh()
        await coordinator.async_request_refresh()
        with pytest.raises(HomeAssistantError) as raised:
            await coordinator.async_run_optimization()

    assert raised.value.translation_key == "inputs_not_aligned"
    assert solves.calls == 0
    coordinator.cleanup()


@pytest.mark.usefixtures("live_runtime_data")
async def test_inputs_changed_during_an_optimization_optimize_again(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, solves: BlockingSolves
) -> None:
    """An input change while an optimization runs optimizes again once the debounce window passes."""
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    hass.async_create_task(coordinator.async_refresh())
    await asyncio.sleep(0.1)
    coordinator.signal_optimization_stale()
    await _settle(hass, solves)
    assert solves.calls == 1

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=DEFAULT_DEBOUNCE_SECONDS + 1))
    await hass.async_block_till_done()

    assert solves.calls == 2
    coordinator.cleanup()


@pytest.mark.usefixtures("live_runtime_data")
async def test_requests_before_an_optimization_are_met_by_it(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, solves: BlockingSolves
) -> None:
    """A change waiting out the debounce window is met by an optimization that starts first."""
    solves.release.set()
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    await coordinator.async_refresh()
    coordinator.signal_optimization_stale()
    await coordinator.async_run_optimization()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=DEFAULT_DEBOUNCE_SECONDS + 1))
    await hass.async_block_till_done()

    assert solves.calls == 2
    coordinator.cleanup()


def _switch_event(state: str) -> Any:
    """Return a state change event for the auto-optimize switch."""
    new_state = MagicMock(spec=State)
    new_state.state = state
    event = MagicMock()
    event.data = {"entity_id": "switch.haeo_auto_optimize", "old_state": None, "new_state": new_state}
    return event


@pytest.mark.parametrize(
    ("stores", "aligned"),
    [
        pytest.param([(True, True, 1000.5)], True, id="aligned_within_a_second"),
        pytest.param([(True, True, 1002.0)], False, id="misaligned"),
        pytest.param([(True, True, None)], False, id="not_loaded"),
        pytest.param([(True, False, 500.0)], True, id="unavailable_store_reports_instead"),
        pytest.param([(True, True, 1000.0), (False, True, None)], True, id="scalar_inputs_are_neutral"),
    ],
)
def test_are_inputs_aligned(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
    stores: list[tuple[bool, bool, float | None]],
    aligned: bool,
) -> None:
    """Forecast inputs are aligned when each available one starts with the horizon.

    A store that is unavailable, because it rejected or could not load its source's
    value, keeps its previous horizon, and the optimization reports it instead of
    waiting for an alignment that will not come.
    """
    mock_horizon(mock_runtime_data).get_forecast_timestamps.return_value = (1000.0, 2000.0)
    for index, (time_series, available, horizon_start) in enumerate(stores):
        mock_runtime_data.input_stores[("Test Battery", (f"field_{index}",))] = MagicMock(
            time_series=time_series, available=available, horizon_start=horizon_start
        )
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    assert coordinator._are_inputs_aligned() is aligned


@pytest.mark.usefixtures("live_runtime_data")
async def test_optimize_action_says_when_the_horizon_moves_while_it_waits(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, solves: BlockingSolves
) -> None:
    """The optimize action fails, rather than reporting success, when inputs lose alignment while it waits."""
    solves.release.set()
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    async with coordinator._optimization_lock:
        request = hass.async_create_task(coordinator.async_run_optimization())
        await asyncio.sleep(0)
        aligned = patch.object(coordinator, "_are_inputs_aligned", return_value=False)
        aligned.start()
    with pytest.raises(HomeAssistantError) as raised:
        await request
    aligned.stop()

    assert raised.value.translation_key == "inputs_not_aligned"
    assert solves.calls == 0
    coordinator.cleanup()


@pytest.mark.usefixtures("live_runtime_data")
async def test_entity_update_requests_wait_out_the_debounce_window(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, solves: BlockingSolves
) -> None:
    """Repeated entity update requests share one optimization once the debounce window passes."""
    solves.release.set()
    coordinator = await _initialized_coordinator(hass, mock_hub_entry, solves)
    await coordinator.async_refresh()
    for _ in range(3):
        await coordinator.async_request_refresh()
    await hass.async_block_till_done()
    assert solves.calls == 1

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=DEFAULT_DEBOUNCE_SECONDS + 1))
    await hass.async_block_till_done()

    assert solves.calls == 2
    coordinator.cleanup()
