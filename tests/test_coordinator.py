"""Tests for the HAEO data update coordinator."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
import time
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
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
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    INTEGRATION_TYPE_HUB,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)
from custom_components.haeo.coordinator import (
    STATUS_OPTIONS,
    ForecastPoint,
    HaeoDataUpdateCoordinator,
    _build_coordinator_output,
)
from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPES,
)
from custom_components.haeo.elements.battery import (
    BATTERY_DEVICE_BATTERY,
    BATTERY_POWER_CHARGE,
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
)
from custom_components.haeo.elements.connection import (
    CONF_SOURCE,
    CONF_TARGET,
    CONNECTION_DEVICE_CONNECTION,
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
)
from custom_components.haeo.elements.grid import CONF_CONNECTION as CONF_CONNECTION_GRID
from custom_components.haeo.elements.grid import (
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)
from custom_components.haeo.elements.solar import SOLAR_POWER
from custom_components.haeo.model import Network, OutputData, OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_NODE


@pytest.fixture
def mock_hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock hub config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Power Network",
            CONF_TIER_1_COUNT: 2,  # 2 intervals of 30 min = 1 hour horizon
            CONF_TIER_1_DURATION: 30,
            CONF_TIER_2_COUNT: 0,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: 0,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: 0,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
        entry_id="hub_entry_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_battery_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock battery subentry."""
    # Set up required sensors
    hass.states.async_set("sensor.battery_capacity", "10000", {"unit_of_measurement": UnitOfEnergy.WATT_HOUR})
    hass.states.async_set("sensor.battery_soc", "50.0")

    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_NAME: "test_battery",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_CAPACITY: "sensor.battery_capacity",
                CONF_CONNECTION: "DC Bus",
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
                CONF_MIN_CHARGE_PERCENTAGE: 20.0,
                CONF_MAX_CHARGE_PERCENTAGE: 80.0,
                CONF_EFFICIENCY: 95.0,
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
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
                CONF_NAME: "test_grid",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID,
                CONF_CONNECTION_GRID: "AC Bus",
                CONF_IMPORT_LIMIT: 10000,
                CONF_EXPORT_LIMIT: 5000,
                CONF_IMPORT_PRICE: ["sensor.import_price"],
                CONF_EXPORT_PRICE: ["sensor.export_price"],
            }
        ),
        subentry_type=ELEMENT_TYPE_GRID,
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
                CONF_NAME: "test_connection",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION,
                CONF_SOURCE: "test_battery",
                CONF_TARGET: "test_grid",
            }
        ),
        subentry_type=ELEMENT_TYPE_CONNECTION,
        title="Battery to Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture(autouse=True)
def patch_state_change_listener() -> Generator[MagicMock]:
    """Patch state change listener registration for tests."""
    with patch(
        "custom_components.haeo.coordinator.coordinator.async_track_state_change_event", return_value=lambda: None
    ) as mock_track:
        yield mock_track


def _get_mock_horizon(runtime_data: HaeoRuntimeData) -> MagicMock:
    """Get the mock horizon manager from runtime data.

    The horizon_manager in test fixtures is a MagicMock, but typed as HorizonManager.
    This helper provides proper typing for accessing mock methods.
    """
    return runtime_data.horizon_manager  # type: ignore[return-value]


@pytest.fixture
def mock_runtime_data(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> HaeoRuntimeData:
    """Create mock runtime data with horizon manager and input entities.

    The horizon_manager is a MagicMock - use _get_mock_horizon() to access mock methods.
    """
    from custom_components.haeo.horizon import HorizonManager  # noqa: PLC0415

    # Create mock horizon manager (typed as HorizonManager but is MagicMock at runtime)
    mock_horizon: Any = MagicMock(spec=HorizonManager)
    mock_horizon.get_forecast_timestamps.return_value = (1000.0, 2000.0, 3000.0)
    mock_horizon.subscribe.return_value = MagicMock()  # Unsubscribe function

    # Create runtime data
    runtime_data = HaeoRuntimeData(horizon_manager=mock_horizon)

    # Store on config entry
    mock_hub_entry.runtime_data = runtime_data

    return runtime_data


def test_coordinator_initialization_collects_participants(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    patch_state_change_listener: MagicMock,
) -> None:
    """Coordinator builds participant map from subentries."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    assert coordinator.hass is hass
    assert coordinator.config_entry is mock_hub_entry
    assert set(coordinator._participant_configs) == {"Test Battery", "Test Grid"}


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


@pytest.mark.usefixtures("mock_connection_subentry")
async def test_async_update_data_returns_outputs(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator returns optimization results merged with element outputs."""
    fake_element = MagicMock()
    fake_element.outputs.return_value = {
        BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0, 2.0))
    }

    fake_network = MagicMock()
    empty_element = MagicMock()
    empty_element.outputs.return_value = {}

    # Add connection element (config name is slugified to "battery_to_grid")
    fake_connection = MagicMock()
    fake_connection.outputs.return_value = {
        CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,)),
        CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER, unit="kW", values=(0.3,)),
    }

    fake_network.elements = {
        "test_battery": fake_element,
        "empty": empty_element,
        "battery_to_grid": fake_connection,
    }

    # Mock battery adapter
    mock_battery_adapter = MagicMock()
    mock_battery_adapter.outputs.return_value = {
        BATTERY_DEVICE_BATTERY: {BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0, 2.0))}
    }

    generated_at = datetime(2024, 1, 1, 0, 15, tzinfo=UTC)
    # Round to nearest 30-minute period (00:15 rounds to 00:00), then add two 30-minute intervals
    base_timestamp = int(datetime(2024, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    expected_forecast_times = (base_timestamp, base_timestamp + 30 * 60, base_timestamp + 2 * 30 * 60)

    # Configure mock horizon manager with forecast timestamps
    _get_mock_horizon(mock_runtime_data).get_forecast_timestamps.return_value = expected_forecast_times

    # Mock connection adapter to return proper outputs
    mock_connection_adapter = MagicMock()
    mock_connection_adapter.outputs.return_value = {
        CONNECTION_DEVICE_CONNECTION: {
            CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,)),
            CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER, unit="kW", values=(0.3,)),
        }
    }

    # Mock empty outputs for grid
    mock_empty_outputs = MagicMock(return_value={})

    # Create mock loaded configs (use subentry titles as keys)
    mock_loaded_configs = {
        "Test Battery": mock_battery_subentry.data,
        "Test Grid": mock_grid_subentry.data,
        "Battery to Grid": {
            CONF_ELEMENT_TYPE: "connection",
            CONF_NAME: "battery_to_grid",
            CONF_SOURCE: "test_battery",
            CONF_TARGET: "test_grid",
        },
    }

    # Mock translations to return the expected network subentry name
    mock_translations = AsyncMock(return_value={"component.haeo.common.network_subentry_name": "System"})

    # Patch coordinator to use mocked _load_from_input_entities
    with (
        patch("custom_components.haeo.coordinator.coordinator.network_module.create_network", new_callable=AsyncMock),
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock) as mock_executor,
        patch("custom_components.haeo.coordinator.coordinator.dismiss_optimization_failure_issue") as mock_dismiss,
        patch("custom_components.haeo.coordinator.coordinator.dt_util.utcnow", return_value=generated_at),
        patch("custom_components.haeo.coordinator.coordinator.async_get_translations", mock_translations),
        patch.dict(
            ELEMENT_TYPES,
            {
                "battery": MagicMock(outputs=mock_battery_adapter.outputs),
                "grid": MagicMock(outputs=mock_empty_outputs),
                "connection": MagicMock(outputs=mock_connection_adapter.outputs),
            },
        ),
    ):
        mock_executor.return_value = 123.45
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        # Set network directly (it's created in async_initialize in production)
        coordinator.network = fake_network

        # Mock the _load_from_input_entities method
        with patch.object(coordinator, "_load_from_input_entities", return_value=mock_loaded_configs):
            result = await coordinator._async_update_data()

    mock_executor.assert_awaited_once_with(fake_network.optimize)

    network_outputs = result["System"][ELEMENT_TYPE_NETWORK]
    cost_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_COST]
    assert cost_output.type == OutputType.COST
    assert cost_output.unit == hass.config.currency
    assert cost_output.state == 123.45
    assert cost_output.forecast is None

    status_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_STATUS]
    assert status_output.type == OutputType.STATUS
    assert status_output.unit is None
    assert status_output.state == "success"
    assert status_output.forecast is None

    duration_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_DURATION]
    assert duration_output.type == OutputType.DURATION
    assert duration_output.state is not None
    assert duration_output.forecast is None

    battery_outputs = result["Test Battery"][BATTERY_DEVICE_BATTERY]
    battery_output = battery_outputs[BATTERY_POWER_CHARGE]
    assert battery_output.type == OutputType.POWER
    assert battery_output.unit == "kW"
    assert battery_output.state == 1.0
    # Forecast should be list of ForecastPoint with datetime objects in local timezone
    local_tz = dt_util.get_default_time_zone()
    assert battery_output.forecast == [
        ForecastPoint(time=datetime.fromtimestamp(expected_forecast_times[0], tz=local_tz), value=1.0),
        ForecastPoint(time=datetime.fromtimestamp(expected_forecast_times[1], tz=local_tz), value=2.0),
    ]

    mock_dismiss.assert_called_once_with(hass, mock_hub_entry.entry_id)


async def test_async_initialize_with_empty_input_entities(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Initialization surfaces network creation failures when inputs are empty."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Mock _load_from_input_entities to return minimal data
    with (
        patch.object(
            coordinator,
            "_load_from_input_entities",
            return_value={},
        ),
        patch("custom_components.haeo.coordinator.coordinator.network_module.create_network") as mock_load,
    ):
        mock_load.side_effect = UpdateFailed("Missing required data")
        with pytest.raises(UpdateFailed, match="Missing required data"):
            await coordinator.async_initialize()
        mock_load.assert_called_once()


async def test_async_update_data_propagates_update_failed(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator surfaces UpdateFailed exceptions from optimization."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator.network = MagicMock()

    with (
        patch.object(coordinator, "_load_from_input_entities", return_value={}),
        patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
            side_effect=UpdateFailed("missing data"),
        ),
        pytest.raises(UpdateFailed, match="missing data"),
    ):
        await coordinator._async_update_data()


async def test_async_update_data_propagates_value_error(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator allows unexpected optimization errors to bubble up."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator.network = MagicMock()

    with (
        patch.object(coordinator, "_load_from_input_entities", return_value={}),
        patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
            side_effect=ValueError("invalid config"),
        ),
        pytest.raises(ValueError, match="invalid config"),
    ):
        await coordinator._async_update_data()


async def test_async_update_data_raises_on_missing_model_element(
    hass: HomeAssistant,
    mock_hub_entry: ConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator should surface KeyError when adapter cannot find model element outputs."""

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    fake_network = Network(name="net", periods=np.array([1.0]))
    # Network must have at least one element for HiGHS to optimize (empty networks are rejected)
    fake_network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "dummy_node"})

    def broken_outputs(*_args: Any, **_kwargs: Any) -> dict[str, dict[str, OutputData]]:
        msg = "missing model element"
        raise KeyError(msg)

    patched_entry = MagicMock(outputs=broken_outputs)

    monkeypatch.setattr(
        "custom_components.haeo.coordinator.coordinator.ELEMENT_TYPES",
        {**ELEMENT_TYPES, "battery": patched_entry},
    )
    coordinator.network = fake_network

    with (
        patch.object(
            coordinator,
            "_load_from_input_entities",
            return_value={"Test Battery": mock_battery_subentry.data},
        ),
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, return_value=0.0),
        patch(
            "custom_components.haeo.coordinator.coordinator.async_get_translations",
            AsyncMock(return_value={"component.haeo.common.network_subentry_name": "System"}),
        ),
        pytest.raises(KeyError),
    ):
        await coordinator._async_update_data()


def test_build_coordinator_output_emits_forecast_entries() -> None:
    """Forecast data is mapped onto ISO timestamps when lengths match."""

    base_time = datetime(2024, 6, 1, tzinfo=UTC)
    forecast_times = (int(base_time.timestamp()), int((base_time + timedelta(minutes=30)).timestamp()))
    output = _build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OutputType.POWER, unit="kW", values=(1.2, 3.4)),
        forecast_times=forecast_times,
    )

    assert output.forecast is not None
    assert [item["value"] for item in output.forecast] == [1.2, 3.4]


def test_build_coordinator_output_handles_timestamp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """ValueError from datetime conversion should clear the forecast payload."""

    class _ErrorDatetime:
        @staticmethod
        def fromtimestamp(*_args: Any, **_kwargs: Any) -> None:
            raise ValueError

    monkeypatch.setattr("custom_components.haeo.coordinator.coordinator.datetime", _ErrorDatetime)

    output = _build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OutputType.POWER, unit="kW", values=(1.0, 2.0)),
        forecast_times=(1, 2),
    )

    assert output.forecast is None


def test_build_coordinator_output_sets_status_options() -> None:
    """Status outputs should carry enum options."""

    output = _build_coordinator_output(
        OUTPUT_NAME_OPTIMIZATION_STATUS,
        OutputData(type=OutputType.STATUS, unit=None, values=("success",)),
        forecast_times=None,
    )

    assert output.options == STATUS_OPTIONS
    assert output.state == "success"
    assert output.forecast is None


def test_build_coordinator_output_skips_forecast_for_single_value() -> None:
    """Single-value outputs should not emit forecast entries."""

    output = _build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OutputType.POWER, unit="kW", values=(5.0,)),
        forecast_times=(1, 2),
    )

    assert output.state == 5.0
    assert output.forecast is None


def test_build_coordinator_output_uses_last_value_when_state_last() -> None:
    """Cumulative outputs with state_last=True should use the last value as state."""

    output = _build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OutputType.POWER, unit="kW", values=(1.0, 2.0, 3.0), state_last=True),
        forecast_times=(1, 2, 3),
    )

    assert output.state == 3.0  # Last value, not first
    assert output.forecast is not None


def test_build_coordinator_output_handles_empty_values() -> None:
    """Empty values should result in None state."""

    output = _build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OutputType.POWER, unit="kW", values=()),
        forecast_times=(1, 2),
    )

    assert output.state is None
    assert output.forecast is None


def test_coordinator_cleanup_invokes_listener(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    patch_state_change_listener: MagicMock,
) -> None:
    """cleanup() should call the unsubscribe callback and clear the reference."""

    unsubscribe = MagicMock()
    patch_state_change_listener.return_value = unsubscribe

    # Add a mock input entity so subscription gets created
    mock_input_entity = MagicMock()
    mock_input_entity.entity_id = "number.haeo_test_battery_power"
    mock_runtime_data.input_entities[("Test Battery", "power")] = mock_input_entity

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Subscription now happens after first refresh, so simulate that
    coordinator._subscribe_to_input_entities()
    assert len(coordinator._state_change_unsubs) > 0

    coordinator.cleanup()

    unsubscribe.assert_called_once()
    assert len(coordinator._state_change_unsubs) == 0


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_element_state_change_triggers_update_and_optimization(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Input entity state change events update element and trigger optimization."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with (
        patch.object(coordinator, "_load_element_config") as load_mock,
        patch.object(coordinator, "_trigger_optimization") as trigger_mock,
        patch("custom_components.haeo.coordinator.coordinator.network_module.update_element") as update_mock,
    ):
        load_mock.return_value = {"element_type": "battery", "name": "Test Battery"}
        # Set network so update path is taken
        coordinator.network = MagicMock()

        # Simulate an element update
        coordinator._handle_element_update("Test Battery")

    load_mock.assert_called_once_with("Test Battery")
    update_mock.assert_called_once()
    trigger_mock.assert_called_once()


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_horizon_change_triggers_optimization(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Horizon manager changes trigger optimization."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with patch.object(coordinator, "_trigger_optimization") as trigger_mock:
        coordinator._handle_horizon_change()

    trigger_mock.assert_called_once()


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_trigger_optimization_marks_pending_when_in_progress(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Trigger marks pending and exits if optimization already in progress."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._optimization_in_progress = True
    coordinator._pending_refresh = False

    coordinator._trigger_optimization()

    assert coordinator._pending_refresh is True


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_trigger_optimization_schedules_timer_in_cooldown(
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
        coordinator._trigger_optimization()

    assert coordinator._pending_refresh is True
    mock_timer.assert_called_once()
    # Timer should be set for approximately 4.5 seconds remaining
    call_args = mock_timer.call_args
    assert call_args[0][0] is hass
    assert 4.0 < call_args[0][1] < 5.0


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_trigger_optimization_reuses_existing_timer(
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
        coordinator._trigger_optimization()

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
    coordinator._pending_refresh = False

    coordinator._debounce_timer_callback(dt_util.utcnow())

    assert coordinator._debounce_timer is None


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_debounce_timer_callback_triggers_refresh_if_pending(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Debounce timer callback triggers refresh when pending."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._debounce_timer = MagicMock()
    coordinator._pending_refresh = True

    with patch.object(coordinator, "_maybe_trigger_refresh") as mock_trigger:
        coordinator._debounce_timer_callback(dt_util.utcnow())

    mock_trigger.assert_called_once()
    assert coordinator._pending_refresh is False


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_maybe_trigger_refresh_skips_when_not_aligned(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator skips refresh when inputs are not aligned."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with (
        patch.object(coordinator, "_are_inputs_aligned", return_value=False),
        patch.object(hass, "async_create_task") as mock_task,
    ):
        coordinator._maybe_trigger_refresh()

    mock_task.assert_not_called()


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_maybe_trigger_refresh_creates_task_when_aligned(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator creates refresh task when inputs are aligned."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Need to properly handle the coroutine created by async_refresh mock
    with (
        patch.object(coordinator, "_are_inputs_aligned", return_value=True),
        patch.object(coordinator, "async_refresh", return_value=None),
        patch.object(hass, "async_create_task") as mock_task,
    ):
        coordinator._maybe_trigger_refresh()

        # Close the coroutine to prevent unawaited coroutine warning
        if mock_task.call_args:
            coro = mock_task.call_args[0][0]
            if hasattr(coro, "close"):
                coro.close()

    mock_task.assert_called_once()


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_are_inputs_aligned_returns_false_without_runtime_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Input alignment check returns False when runtime data is missing."""
    # Don't use mock_runtime_data fixture - no runtime data set
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = coordinator._are_inputs_aligned()

    assert result is False


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_are_inputs_aligned_returns_false_without_horizon(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Input alignment check returns False when no forecast timestamps."""
    _get_mock_horizon(mock_runtime_data).get_forecast_timestamps.return_value = ()
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = coordinator._are_inputs_aligned()

    assert result is False


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_are_inputs_aligned_returns_false_with_none_horizon_start(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Input alignment check returns False when entity has None horizon_start."""
    _get_mock_horizon(mock_runtime_data).get_forecast_timestamps.return_value = (1000.0, 2000.0)

    # Add mock input entity with None horizon_start
    mock_entity = MagicMock()
    mock_entity.horizon_start = None
    mock_runtime_data.input_entities[("Test Battery", "capacity")] = mock_entity

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = coordinator._are_inputs_aligned()

    assert result is False


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_are_inputs_aligned_returns_false_with_misaligned_horizon(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Input alignment check returns False when horizons differ by more than tolerance."""
    expected_start = 1000.0
    _get_mock_horizon(mock_runtime_data).get_forecast_timestamps.return_value = (expected_start, 2000.0)

    # Add mock input entity with misaligned horizon (more than 1.0 seconds off)
    mock_entity = MagicMock()
    mock_entity.horizon_start = expected_start + 5.0  # 5 seconds off > 1.0 tolerance
    mock_runtime_data.input_entities[("Test Battery", "capacity")] = mock_entity

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = coordinator._are_inputs_aligned()

    assert result is False


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_are_inputs_aligned_returns_true_when_aligned(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Input alignment check returns True when all horizons match."""
    expected_start = 1000.0
    _get_mock_horizon(mock_runtime_data).get_forecast_timestamps.return_value = (expected_start, 2000.0)

    # Add mock input entity with aligned horizon (within tolerance)
    mock_entity = MagicMock()
    mock_entity.horizon_start = expected_start + 0.5  # Within 1.0 tolerance
    mock_runtime_data.input_entities[("Test Battery", "capacity")] = mock_entity

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = coordinator._are_inputs_aligned()

    assert result is True


@pytest.mark.usefixtures("mock_battery_subentry")
async def test_async_update_data_returns_existing_when_concurrent(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator returns existing data when optimization is in progress."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Simulate existing data and in-progress flag
    existing_data = {"existing": "data"}
    coordinator.data = existing_data  # type: ignore[assignment]
    coordinator._optimization_in_progress = True

    result = await coordinator._async_update_data()

    assert result == existing_data


@pytest.mark.usefixtures("mock_battery_subentry")
async def test_async_update_data_raises_on_concurrent_first_refresh(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator raises UpdateFailed for concurrent calls during first refresh."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # No existing data, but in-progress flag set
    coordinator._optimization_in_progress = True
    assert coordinator.data is None

    with pytest.raises(UpdateFailed, match="Concurrent optimization during first refresh"):
        await coordinator._async_update_data()  # type: ignore[misc]


@pytest.mark.usefixtures("mock_battery_subentry")
async def test_async_update_data_clears_flags_in_finally(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Coordinator clears optimization flags even on exception."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with (
        patch.object(coordinator, "_load_from_input_entities", side_effect=UpdateFailed("test")),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()

    # Flags should be cleared by finally block
    assert coordinator._optimization_in_progress is False
    assert coordinator._pending_refresh is False


@pytest.mark.usefixtures("mock_battery_subentry")
async def test_load_from_input_entities_raises_without_runtime_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Loading from input entities raises when runtime data unavailable."""
    # Don't use mock_runtime_data fixture
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with pytest.raises(UpdateFailed, match="Runtime data not available"):
        coordinator._load_from_input_entities()


def test_subscribe_to_input_entities_no_op_without_runtime_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
) -> None:
    """Subscription does nothing when runtime data unavailable."""
    # Don't use mock_runtime_data fixture
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Should not raise
    coordinator._subscribe_to_input_entities()

    # No subscriptions created
    assert len(coordinator._state_change_unsubs) == 0


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


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_trigger_optimization_optimizes_immediately_outside_cooldown(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Trigger optimizes immediately when outside cooldown period."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    # Set last optimization time far in the past (beyond cooldown)
    coordinator._last_optimization_time = time.time() - 100.0
    coordinator._debounce_seconds = 5.0

    with patch.object(coordinator, "_maybe_trigger_refresh") as mock_trigger:
        coordinator._trigger_optimization()

    mock_trigger.assert_called_once()


@pytest.mark.usefixtures("mock_battery_subentry")
def test_load_from_input_entities_raises_when_required_input_missing(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Loading raises error when required input entities are missing."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # runtime_data exists but input_entities is empty
    mock_runtime_data.input_entities = {}

    # Should raise when required fields are missing
    with pytest.raises(ValueError, match="Missing required field 'capacity' for element 'Test Battery'"):
        coordinator._load_from_input_entities()


@pytest.mark.usefixtures("mock_battery_subentry")
def test_load_from_input_entities_loads_time_series_fields(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Time series fields are loaded as arrays from input entities."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Create mock input entities for all required fields
    from custom_components.haeo.elements import get_input_fields  # noqa: PLC0415

    element_config = coordinator._participant_configs["Test Battery"]
    for field_info in get_input_fields(element_config).values():
        mock_entity = MagicMock()
        mock_entity.get_values.return_value = (1.0, 2.0, 3.0)
        mock_runtime_data.input_entities[("Test Battery", field_info.field_name)] = mock_entity

    result = coordinator._load_from_input_entities()

    assert "Test Battery" in result
    # Narrow the discriminated union type using element_type
    battery_config = result["Test Battery"]
    assert battery_config["element_type"] == "battery"
    assert isinstance(battery_config["capacity"], np.ndarray)
    np.testing.assert_array_equal(battery_config["capacity"], [1.0, 2.0, 3.0])


@pytest.mark.usefixtures("mock_battery_subentry")
def test_load_from_input_entities_raises_when_required_field_returns_none(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Loading raises error when required input entity returns None values."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Create mock input entity that returns None for required field (capacity)
    mock_entity = MagicMock()
    mock_entity.get_values.return_value = None
    mock_runtime_data.input_entities[("Test Battery", "capacity")] = mock_entity

    # Should raise since required field (capacity) returned None
    with pytest.raises(ValueError, match="Missing required field 'capacity' for element 'Test Battery'"):
        coordinator._load_from_input_entities()


@pytest.mark.usefixtures("mock_battery_subentry")
async def test_async_update_data_raises_when_runtime_data_none_in_body(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Optimization raises when runtime data becomes None during execution."""
    # Don't use mock_runtime_data fixture so _get_runtime_data returns None
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with pytest.raises(UpdateFailed, match="Runtime data not available"):
        await coordinator._async_update_data()


def test_load_from_input_entities_raises_for_invalid_element_type(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Loading raises error for elements with invalid element types."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Inject an invalid element type into participant configs
    invalid_config: Any = {
        "Invalid Element": {
            CONF_ELEMENT_TYPE: "invalid_type",
            CONF_NAME: "Invalid Element",
        }
    }
    coordinator._participant_configs = invalid_config

    # Should raise for invalid element type
    with pytest.raises(ValueError, match="Invalid element type 'invalid_type' for element 'Invalid Element'"):
        coordinator._load_from_input_entities()


@pytest.mark.usefixtures("mock_battery_subentry")
def test_load_from_input_entities_raises_for_invalid_config_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Loading raises error for elements with invalid config data."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    invalid_config: Any = {
        "Bad Battery": {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
            CONF_NAME: "Bad Battery",
            CONF_CAPACITY: "sensor.battery_capacity",
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            # Missing required non-input field: connection
        }
    }
    coordinator._participant_configs = invalid_config

    from custom_components.haeo.elements import get_input_fields  # noqa: PLC0415

    element_config = coordinator._participant_configs["Bad Battery"]
    for field_info in get_input_fields(element_config).values():
        mock_entity = MagicMock()
        mock_entity.get_values.return_value = (1.0, 2.0, 3.0)
        mock_runtime_data.input_entities[("Bad Battery", field_info.field_name)] = mock_entity

    with pytest.raises(ValueError, match="Invalid config data for element 'Bad Battery'"):
        coordinator._load_from_input_entities()


@pytest.mark.usefixtures("mock_battery_subentry")
async def test_async_initialize_raises_without_runtime_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """async_initialize raises RuntimeError when runtime data is unavailable."""
    # Don't use mock_runtime_data fixture - no runtime data set
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with pytest.raises(RuntimeError, match="Runtime data not available"):
        await coordinator.async_initialize()


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_handle_element_update_logs_and_returns_on_load_error(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """_handle_element_update logs exception and returns when load fails."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator.network = MagicMock()

    # Mock _load_element_config to raise ValueError
    with (
        patch.object(
            coordinator,
            "_load_element_config",
            side_effect=ValueError("Missing required field"),
        ),
        patch.object(coordinator, "_trigger_optimization") as trigger_mock,
        patch("custom_components.haeo.coordinator.coordinator._LOGGER") as mock_logger,
    ):
        # Should not raise - logs and returns
        coordinator._handle_element_update("Test Battery")

    # Trigger should NOT be called since we returned early
    trigger_mock.assert_not_called()

    # Should have logged the exception
    mock_logger.exception.assert_called_once()
    call_args = mock_logger.exception.call_args
    assert "Failed to load config for element" in call_args[0][0]
    assert "Test Battery" in call_args[0][1]


@pytest.mark.usefixtures("mock_battery_subentry")
def test_load_element_config_raises_for_unknown_element(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """_load_element_config raises ValueError for unknown element name."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with pytest.raises(ValueError, match="Element 'NonExistent' not found in participant configs"):
        coordinator._load_element_config("NonExistent")


@pytest.mark.usefixtures("mock_battery_subentry")
def test_load_element_config_raises_without_runtime_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """_load_element_config raises ValueError when runtime data is unavailable."""
    # Don't use mock_runtime_data fixture
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with pytest.raises(ValueError, match="Runtime data not available when loading element 'Test Battery'"):
        coordinator._load_element_config("Test Battery")


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
def test_element_update_callback_calls_handle_element_update(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Created callback should call _handle_element_update with element name."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Create a callback for "Test Battery"
    callback_fn = coordinator._create_element_update_callback("Test Battery")

    # Mock _handle_element_update
    with patch.object(coordinator, "_handle_element_update") as handle_mock:
        # Call the callback with a mock event
        mock_event = MagicMock()
        callback_fn(mock_event)

    # Verify _handle_element_update was called with correct element name
    handle_mock.assert_called_once_with("Test Battery")


# ===== Tests for auto-optimize control =====


def test_auto_optimize_enabled_defaults_to_true(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Auto-optimize is enabled by default."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    assert coordinator.auto_optimize_enabled is True


def test_auto_optimize_enabled_setter(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Auto-optimize can be disabled and re-enabled."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    coordinator.auto_optimize_enabled = False
    assert coordinator.auto_optimize_enabled is False

    coordinator.auto_optimize_enabled = True
    assert coordinator.auto_optimize_enabled is True


def test_trigger_optimization_skips_when_auto_optimize_disabled(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """_trigger_optimization does nothing when auto-optimize is disabled."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator.auto_optimize_enabled = False

    # Set initial state - _optimization_in_progress False, no pending
    coordinator._optimization_in_progress = False
    coordinator._pending_refresh = False

    # Call _trigger_optimization - should return early due to auto_optimize_enabled=False
    coordinator._trigger_optimization()

    # State should remain unchanged (no pending refresh set, no timers scheduled)
    assert coordinator._pending_refresh is False
    assert coordinator._debounce_timer is None


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry", "mock_runtime_data")
async def test_async_run_optimization_runs_when_inputs_aligned(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """async_run_optimization runs optimization when inputs are aligned."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Mock _are_inputs_aligned to return True
    with (
        patch.object(coordinator, "_are_inputs_aligned", return_value=True),
        patch.object(coordinator, "async_refresh", new_callable=AsyncMock) as refresh_mock,
    ):
        await coordinator.async_run_optimization()

    refresh_mock.assert_called_once()


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry", "mock_runtime_data")
async def test_async_run_optimization_skips_when_inputs_not_aligned(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """async_run_optimization skips when inputs are not aligned."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Mock _are_inputs_aligned to return False
    with (
        patch.object(coordinator, "_are_inputs_aligned", return_value=False),
        patch.object(coordinator, "async_refresh", new_callable=AsyncMock) as refresh_mock,
    ):
        await coordinator.async_run_optimization()

    # async_refresh should not be called
    refresh_mock.assert_not_called()
