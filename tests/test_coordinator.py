"""Tests for the HAEO data update coordinator."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_DURATION,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    INTEGRATION_TYPE_HUB,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    OUTPUT_NAME_REQUIRED_ENERGY,
)
from custom_components.haeo.coordinator import (
    STATUS_OPTIONS,
    ForecastPoint,
    HaeoDataUpdateCoordinator,
    _build_coordinator_output,
    collect_entity_ids,
    extract_entity_ids_from_config,
)
from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPES,
    ElementConfigSchema,
)
from custom_components.haeo.elements.battery import (
    BATTERY_DEVICE_BATTERY,
    BATTERY_POWER_CHARGE,
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    BatteryConfigSchema,
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
from custom_components.haeo.model import (
    OUTPUT_TYPE_COST,
    OUTPUT_TYPE_DURATION,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_STATUS,
    Network,
    OutputData,
)


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
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
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
        "custom_components.haeo.coordinator.async_track_state_change_event", return_value=lambda: None
    ) as mock_track:
        yield mock_track


def test_coordinator_initialization_collects_participants_and_entity_ids(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    patch_state_change_listener: MagicMock,
) -> None:
    """Coordinator builds participant map and subscribes to referenced entities."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    assert coordinator.hass is hass
    assert coordinator.config_entry is mock_hub_entry
    assert set(coordinator._participant_configs) == {"Test Battery", "Test Grid"}

    tracked_entities = set(patch_state_change_listener.call_args.args[1])
    assert tracked_entities == {
        "sensor.battery_capacity",
        "sensor.battery_soc",
        "sensor.import_price",
        "sensor.export_price",
    }


def test_update_interval_respects_config(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Update interval honours the configured value."""
    hass.config_entries.async_update_entry(
        mock_hub_entry, data={**dict(mock_hub_entry.data), CONF_UPDATE_INTERVAL_MINUTES: 12}
    )
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    assert coordinator.update_interval == timedelta(minutes=12)


@pytest.mark.usefixtures("mock_connection_subentry")
async def test_async_update_data_returns_outputs(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Coordinator returns optimization results merged with element outputs."""
    fake_element = MagicMock()
    fake_element.outputs.return_value = {
        BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0, 2.0))
    }

    fake_network = MagicMock()
    empty_element = MagicMock()
    empty_element.outputs.return_value = {}

    # Add connection element (config name is slugified to "battery_to_grid")
    fake_connection = MagicMock()
    fake_connection.outputs.return_value = {
        CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,)),
        CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.3,)),
    }

    fake_network.elements = {
        "test_battery": fake_element,
        "empty": empty_element,
        "battery_to_grid": fake_connection,
    }
    # Set required_energy to a realistic list (one more than number of periods for timestep boundaries)
    fake_network.required_energy = [5.0, 3.0, 0.0]

    # Mock battery adapter
    mock_battery_adapter = MagicMock()
    mock_battery_adapter.outputs.return_value = {
        BATTERY_DEVICE_BATTERY: {BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0, 2.0))}
    }

    generated_at = datetime(2024, 1, 1, 0, 15, tzinfo=UTC)
    # Round to nearest 30-minute period (00:15 rounds to 00:00), then add two 30-minute intervals
    base_timestamp = int(datetime(2024, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    expected_forecast_times = (base_timestamp, base_timestamp + 30 * 60, base_timestamp + 2 * 30 * 60)

    # Mock connection adapter to return proper outputs
    mock_connection_adapter = MagicMock()
    mock_connection_adapter.outputs.return_value = {
        CONNECTION_DEVICE_CONNECTION: {
            CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,)),
            CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.3,)),
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

    # Patch the registry entries to use our mocked output functions
    with (
        patch("custom_components.haeo.coordinator.data_module.config_available", return_value=True),
        patch(
            "custom_components.haeo.coordinator.data_module.load_element_configs",
            new_callable=AsyncMock,
        ) as mock_load_configs,
        patch("custom_components.haeo.coordinator.data_module.load_network", new_callable=AsyncMock) as mock_load,
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock) as mock_executor,
        patch("custom_components.haeo.coordinator.dismiss_optimization_failure_issue") as mock_dismiss,
        patch("custom_components.haeo.coordinator.dt_util.utcnow", return_value=generated_at),
        patch("custom_components.haeo.coordinator.async_get_translations", mock_translations),
        patch.dict(
            ELEMENT_TYPES,
            {
                "battery": ELEMENT_TYPES["battery"]._replace(outputs=mock_battery_adapter.outputs),
                "grid": ELEMENT_TYPES["grid"]._replace(outputs=mock_empty_outputs),
                "connection": ELEMENT_TYPES["connection"]._replace(outputs=mock_connection_adapter.outputs),
            },
        ),
    ):
        mock_load_configs.return_value = mock_loaded_configs
        mock_load.return_value = fake_network
        mock_executor.return_value = 123.45
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        result = await coordinator._async_update_data()

    mock_load_configs.assert_awaited_once_with(
        hass,
        coordinator._participant_configs,
        expected_forecast_times,
    )
    mock_load.assert_awaited_once_with(
        mock_hub_entry,
        periods_seconds=[30 * 60, 30 * 60],  # Two 30-minute intervals
        participants=mock_loaded_configs,
    )

    mock_executor.assert_awaited_once_with(fake_network.optimize)

    network_outputs = result["System"][ELEMENT_TYPE_NETWORK]
    cost_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_COST]
    assert cost_output.type == OUTPUT_TYPE_COST
    assert cost_output.unit == hass.config.currency
    assert cost_output.state == 123.45
    assert cost_output.forecast is None

    status_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_STATUS]
    assert status_output.type == OUTPUT_TYPE_STATUS
    assert status_output.unit is None
    assert status_output.state == "success"
    assert status_output.forecast is None

    duration_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_DURATION]
    assert duration_output.type == OUTPUT_TYPE_DURATION
    assert duration_output.state is not None
    assert duration_output.forecast is None

    required_energy_output = network_outputs[OUTPUT_NAME_REQUIRED_ENERGY]
    assert required_energy_output.state == 5.0
    assert required_energy_output.unit == "kWh"
    # required_energy has a forecast (one value per timestep boundary)
    assert required_energy_output.forecast is not None
    assert len(required_energy_output.forecast) == 3

    battery_outputs = result["Test Battery"][BATTERY_DEVICE_BATTERY]
    battery_output = battery_outputs[BATTERY_POWER_CHARGE]
    assert battery_output.type == OUTPUT_TYPE_POWER
    assert battery_output.unit == "kW"
    assert battery_output.state == 1.0
    # Forecast should be list of ForecastPoint with datetime objects in local timezone
    local_tz = dt_util.get_default_time_zone()
    assert battery_output.forecast == [
        ForecastPoint(time=datetime.fromtimestamp(expected_forecast_times[0], tz=local_tz), value=1.0),
        ForecastPoint(time=datetime.fromtimestamp(expected_forecast_times[1], tz=local_tz), value=2.0),
    ]

    mock_dismiss.assert_called_once_with(hass, mock_hub_entry.entry_id)


@pytest.mark.usefixtures("mock_connection_subentry")
async def test_async_update_data_handles_none_required_energy(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Coordinator handles network with required_energy=None (fallback to 0.0)."""
    fake_element = MagicMock()
    fake_element.outputs.return_value = {}

    fake_network = MagicMock()
    fake_network.elements = {"test_battery": fake_element}
    # Explicitly set required_energy to None to test the fallback branch
    fake_network.required_energy = None

    mock_adapter = MagicMock(return_value={})

    # Mock translations to return the expected network subentry name
    mock_translations = AsyncMock(return_value={"component.haeo.common.network_subentry_name": "System"})

    with (
        patch("custom_components.haeo.coordinator.data_module.config_available", return_value=True),
        patch(
            "custom_components.haeo.coordinator.data_module.load_element_configs",
            new_callable=AsyncMock,
            return_value={
                "Test Battery": mock_battery_subentry.data,
                "Test Grid": mock_grid_subentry.data,
                "Battery to Grid": {CONF_ELEMENT_TYPE: "connection"},
            },
        ),
        patch("custom_components.haeo.coordinator.data_module.load_network", new_callable=AsyncMock) as mock_load,
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, return_value=0.0),
        patch("custom_components.haeo.coordinator.dismiss_optimization_failure_issue"),
        patch("custom_components.haeo.coordinator.async_get_translations", mock_translations),
        patch.dict(
            ELEMENT_TYPES,
            {
                "battery": ELEMENT_TYPES["battery"]._replace(outputs=mock_adapter),
                "grid": ELEMENT_TYPES["grid"]._replace(outputs=mock_adapter),
                "connection": ELEMENT_TYPES["connection"]._replace(outputs=mock_adapter),
            },
        ),
    ):
        mock_load.return_value = fake_network
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        result = await coordinator._async_update_data()

    # When required_energy is None, the output should have a fallback value of (0.0,)
    network_outputs = result["System"][ELEMENT_TYPE_NETWORK]
    required_energy_output = network_outputs[OUTPUT_NAME_REQUIRED_ENERGY]
    assert required_energy_output.state == 0.0
    assert required_energy_output.unit == "kWh"


async def test_async_update_data_raises_on_missing_sensors(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Coordinator raises UpdateFailed when sensor data is unavailable."""
    # config_available returns False to simulate missing sensor data
    with patch("custom_components.haeo.coordinator.data_module.config_available", return_value=False):
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        # Verify the error contains the element names with missing sensors
        assert exc_info.value.translation_key == "missing_sensors"


async def test_async_update_data_propagates_update_failed(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Coordinator surfaces loader failures as UpdateFailed."""
    with (
        patch("custom_components.haeo.coordinator.data_module.config_available", return_value=True),
        patch(
            "custom_components.haeo.coordinator.data_module.load_element_configs",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch("custom_components.haeo.coordinator.data_module.load_network", side_effect=UpdateFailed("missing data")),
    ):
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        with pytest.raises(UpdateFailed, match="missing data"):
            await coordinator._async_update_data()


async def test_async_update_data_propagates_value_error(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Coordinator allows unexpected errors to bubble up."""
    with (
        patch("custom_components.haeo.coordinator.data_module.config_available", return_value=True),
        patch(
            "custom_components.haeo.coordinator.data_module.load_element_configs",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch("custom_components.haeo.coordinator.data_module.load_network", side_effect=ValueError("invalid config")),
    ):
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        with pytest.raises(ValueError, match="invalid config"):
            await coordinator._async_update_data()


async def test_async_update_data_raises_on_missing_model_element(
    hass: HomeAssistant,
    mock_hub_entry: ConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator should surface KeyError when adapter cannot find model element outputs."""

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    fake_network = Network(name="net", periods=[1.0] * 1)
    # Network must have at least one element for HiGHS to optimize (empty networks are rejected)
    fake_network.add("node", "dummy_node")

    def broken_outputs(_name: str, _outputs: object, _config: object) -> dict[str, dict[str, OutputData]]:
        msg = "missing model element"
        raise KeyError(msg)

    battery_entry = ELEMENT_TYPES["battery"]
    patched_entry = battery_entry._replace(outputs=broken_outputs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "custom_components.haeo.coordinator.ELEMENT_TYPES",
        {**ELEMENT_TYPES, "battery": patched_entry},
    )
    monkeypatch.setattr(
        "custom_components.haeo.coordinator.data_module.load_network",
        AsyncMock(return_value=fake_network),
    )

    with pytest.raises(KeyError):
        await coordinator._async_update_data()


def test_collect_entity_ids_handles_nested_structures() -> None:
    """collect_entity_ids should traverse mappings and sequences recursively."""
    value = {
        "single": "sensor.solo",
        "group": ["sensor.one", "sensor.two"],
        "nested": {
            "inner": ("sensor.three",),
        },
    }

    assert collect_entity_ids(value) == {"sensor.solo", "sensor.one", "sensor.two", "sensor.three"}


def test_collect_entity_ids_returns_empty_for_unknown_types() -> None:
    """Non-iterable values should yield an empty set of entity identifiers."""
    assert collect_entity_ids(123) == set()


def test_extract_entity_ids_skips_constant_fields() -> None:
    """extract_entity_ids_from_config should ignore constant-only fields."""
    config: BatteryConfigSchema = {
        CONF_NAME: "Battery",
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
        CONF_CAPACITY: "sensor.capacity",
        CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.soc",
        CONF_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_EFFICIENCY: 95.0,
        CONF_CONNECTION: "DC Bus",
    }

    extracted = extract_entity_ids_from_config(config)

    assert extracted == {"sensor.capacity", "sensor.soc"}


def test_extract_entity_ids_catches_type_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected type errors should fall back to an empty identifier set."""
    config: ElementConfigSchema = {
        CONF_NAME: "Battery",
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
        CONF_CAPACITY: "sensor.capacity",
        CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.soc",
        CONF_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_EFFICIENCY: 95.0,
        CONF_CONNECTION: "DC Bus",
    }

    def broken_collect(_value: Any) -> set[str]:
        msg = "boom"
        raise TypeError(msg)

    monkeypatch.setattr("custom_components.haeo.coordinator.collect_entity_ids", broken_collect)

    extracted = extract_entity_ids_from_config(config)

    assert extracted == set()


def test_build_coordinator_output_emits_forecast_entries() -> None:
    """Forecast data is mapped onto ISO timestamps when lengths match."""

    base_time = datetime(2024, 6, 1, tzinfo=UTC)
    forecast_times = (int(base_time.timestamp()), int((base_time + timedelta(minutes=30)).timestamp()))
    output = _build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.2, 3.4)),
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

    monkeypatch.setattr("custom_components.haeo.coordinator.datetime", _ErrorDatetime)

    output = _build_coordinator_output(
        SOLAR_POWER, OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0, 2.0)), forecast_times=(1, 2)
    )

    assert output.forecast is None


def test_build_coordinator_output_sets_status_options() -> None:
    """Status outputs should carry enum options."""

    output = _build_coordinator_output(
        OUTPUT_NAME_OPTIMIZATION_STATUS,
        OutputData(type=OUTPUT_TYPE_STATUS, unit=None, values=("success",)),
        forecast_times=None,
    )

    assert output.options == STATUS_OPTIONS
    assert output.state == "success"
    assert output.forecast is None


def test_build_coordinator_output_skips_forecast_for_single_value() -> None:
    """Single-value outputs should not emit forecast entries."""

    output = _build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(5.0,)),
        forecast_times=(1, 2),
    )

    assert output.state == 5.0
    assert output.forecast is None


def test_coordinator_cleanup_invokes_listener(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    patch_state_change_listener: MagicMock,
) -> None:
    """cleanup() should call the unsubscribe callback and clear the reference."""

    unsubscribe = MagicMock()
    patch_state_change_listener.return_value = unsubscribe

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    assert coordinator._state_change_unsub is not None

    coordinator.cleanup()

    unsubscribe.assert_called_once()
    assert coordinator._state_change_unsub is None


@pytest.mark.usefixtures("mock_battery_subentry", "mock_grid_subentry")
async def test_state_change_handler_requests_refresh(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """State change events should trigger a coordinator refresh."""

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with patch.object(coordinator, "async_request_refresh", new_callable=AsyncMock) as request_mock:
        await coordinator._state_change_handler(None)

    request_mock.assert_awaited_once()
