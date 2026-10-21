"""Tests for the HAEO data update coordinator."""

from types import MappingProxyType
from typing import Any  # noqa: TID251  # Mock-typed test doubles (MagicMock spec=) and monkeypatched callback stand-ins
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SALVAGE_VALUE,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.sections import SECTION_POWER_LIMITS, SECTION_PRICING
from custom_components.haeo.elements import get_element_configs
from custom_components.haeo.input_stores import build_input_stores

from .helpers import mock_horizon


def test_load_element_config_reflects_store_values(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    patch_state_change_listener: MagicMock,
) -> None:
    """Element config is assembled from the resolved values of its input stores.

    Input stores are the single source of truth. The coordinator reads each
    store's current value, so a value edit applied through the store (the way
    input entities mutate them) is reflected on the next load without rebuilding.
    """
    # Build the real stores backing this element's configured fields.
    mock_runtime_data.input_stores = build_input_stores(hass, mock_hub_entry, mock_runtime_data.horizon_manager)

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Every element loads, and the salvage value starts at 0.0 (from the store)
    configs = coordinator._load_from_input_stores()
    assert configs.keys() == {"Test Battery", "Test Grid"}
    battery_config = configs["Test Battery"]
    assert battery_config["element_type"] == ElementType.BATTERY
    assert battery_config[SECTION_PRICING].get(CONF_SALVAGE_VALUE) == 0.0

    # Simulate a value edit through the store (display units).
    salvage_store = mock_runtime_data.input_stores[("Test Battery", (SECTION_PRICING, CONF_SALVAGE_VALUE))]
    salvage_store.set_value(5.0)

    # Load again — must see the updated store value
    battery_config = coordinator._load_from_input_stores()["Test Battery"]
    assert battery_config["element_type"] == ElementType.BATTERY
    assert battery_config[SECTION_PRICING].get(CONF_SALVAGE_VALUE) == 5.0


def test_update_interval_is_none_for_event_driven(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Update interval is None since coordinator is event-driven."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    assert coordinator.update_interval is None


async def test_async_initialize_with_empty_input_stores(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Initialization surfaces network creation failures when inputs are empty."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Mock _load_from_input_stores to return minimal data
    with (
        patch.object(
            coordinator,
            "_load_from_input_stores",
            return_value={},
        ),
        patch("custom_components.haeo.coordinator.coordinator.build_network") as mock_load,
    ):
        mock_load.side_effect = UpdateFailed("Missing required data")
        with pytest.raises(UpdateFailed, match="Missing required data"):
            await coordinator.async_initialize()
        mock_load.assert_called_once()


@pytest.mark.parametrize(
    ("error", "match"),
    [
        pytest.param(UpdateFailed("missing data"), "missing data", id="update_failed"),
        pytest.param(ValueError("invalid config"), "invalid config", id="value_error"),
    ],
)
async def test_async_update_data_propagates_errors(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    error: Exception,
    match: str,
) -> None:
    """Coordinator surfaces optimization errors to callers."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._network = MagicMock()

    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
            side_effect=error,
        ),
        pytest.raises(type(error), match=match),
    ):
        await coordinator._async_update_data()


def test_coordinator_cleanup_invokes_listener(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    patch_state_change_listener: MagicMock,
) -> None:
    """cleanup() should call the unsubscribe callbacks and clear the references."""

    unsubscribe = MagicMock()
    patch_state_change_listener.return_value = unsubscribe

    # Add a mock input store so a store listener subscription gets created.
    # Its add_listener returns the same unsubscribe mock as the switch listener
    # so the total unsub count and call count line up.
    mock_store = MagicMock()
    mock_store.add_listener.return_value = unsubscribe
    mock_runtime_data.input_stores[("Test Battery", (SECTION_POWER_LIMITS, CONF_MAX_POWER_TARGET_SOURCE))] = mock_store

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Subscription now happens after first refresh, so simulate that
    coordinator._subscribe_to_input_stores()
    # Should have subscriptions for: store listener + auto-optimize switch
    num_subs = len(coordinator._state_change_unsubs)
    assert num_subs >= 2  # At least store listener + auto-optimize switch

    coordinator.cleanup()

    # All unsubscribers should be called
    assert unsubscribe.call_count == num_subs
    assert len(coordinator._state_change_unsubs) == 0


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
async def test_async_update_data_solves_with_current_horizon_periods(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """The network is solved with the period durations of the horizon its inputs were loaded for.

    At a horizon boundary the input stores reload first, and the last of them
    triggers the optimization before any horizon-change callback runs. The
    periods therefore have to be applied as part of the optimization itself,
    on the event loop, before the solve is handed to the executor.
    """
    horizon = mock_horizon(mock_runtime_data)
    horizon.periods_seconds = [60, 60, 300]
    horizon.get_forecast_timestamps.return_value = (0.0, 60.0, 120.0, 420.0)

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._network = Network(name="test", periods=np.array([1 / 60, 5 / 60, 5 / 60]))

    periods_at_solve: list[np.ndarray] = []

    def capture_periods(_job: Any) -> float:
        periods_at_solve.append(coordinator.network.periods.copy())
        msg = "stop after capturing the solve inputs"
        raise RuntimeError(msg)

    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        patch.object(hass, "async_add_executor_job", side_effect=capture_periods),
        pytest.raises(RuntimeError, match="stop after capturing"),
    ):
        await coordinator._async_update_data()

    np.testing.assert_allclose(periods_at_solve[0], [1 / 60, 1 / 60, 5 / 60])


@pytest.mark.usefixtures("mock_battery_subentry")
def test_load_from_input_stores_delegates_to_config_loader(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Loading delegates per participant to the value-based config loader.

    Each element's resolved store values are collected by field path and
    passed to ``load_element_config_from_values``.
    """
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Populate a store whose resolved value should flow through to the loader.
    field_path = (SECTION_STORAGE, CONF_CAPACITY)
    mock_store = MagicMock()
    mock_store.value = 42.0
    mock_runtime_data.input_stores[("Test Battery", field_path)] = mock_store

    loaded_config: dict[str, str] = {"element_type": "battery", "name": "Test Battery"}
    with patch(
        "custom_components.haeo.coordinator.coordinator.load_element_config_from_values",
        return_value=loaded_config,
    ) as mock_load:
        result = coordinator._load_from_input_stores()

    mock_load.assert_called_once()
    call_args = mock_load.call_args
    assert call_args.args[0] == "Test Battery"
    # The field_values mapping passed to the loader carries the store's value.
    assert call_args.args[2] == {field_path: 42.0}
    assert result == {"Test Battery": loaded_config}


def test_get_element_configs_raises_for_invalid_element_type(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Reading configs raises for elements with invalid element types.

    The coordinator snapshots participant configs at construction via
    ``get_element_configs``; this exercises that validation boundary directly.
    """
    invalid_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: "invalid_type",
                CONF_NAME: "Invalid Element",
            }
        ),
        subentry_type="invalid_type",
        title="Invalid Element",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, invalid_subentry)

    with pytest.raises(ValueError, match="Subentry 'Invalid Element' failed config validation"):
        get_element_configs(mock_hub_entry, {"Invalid Element": invalid_subentry.subentry_id})


@pytest.mark.usefixtures("mock_battery_subentry")
async def test_changed_inputs_reach_the_network_at_the_next_optimization(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """An element whose inputs change is updated from the configs the next optimization loads, and only then."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._network = MagicMock()
    updater = MagicMock()
    coordinator._element_updaters = {"Test Battery": updater}
    loaded = {"Test Battery": MagicMock()}

    with patch.object(coordinator, "signal_optimization_stale") as signal:
        coordinator._handle_element_update("Test Battery")
    signal.assert_called_once()
    updater.assert_not_called()

    for _ in range(2):
        with (
            patch.object(coordinator, "_load_from_input_stores", return_value=loaded),
            patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, side_effect=UpdateFailed("stop")),
            pytest.raises(UpdateFailed, match="stop"),
        ):
            await coordinator._async_update_data()

    updater.assert_called_once_with(loaded["Test Battery"])


def test_coordinator_requires_runtime_data(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """The coordinator reads its entry's runtime data, so the entry must have it first."""
    mock_hub_entry.runtime_data = None
    with pytest.raises(RuntimeError, match="runtime data must be set"):
        HaeoDataUpdateCoordinator(hass, mock_hub_entry)
