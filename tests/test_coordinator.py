"""Tests for the HAEO data update coordinator."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_OPTIMIZER,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_OPTIMIZER,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
    OPTIMIZER_NAME_MAP,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY, ELEMENT_TYPE_CONNECTION, ELEMENT_TYPE_GRID
from custom_components.haeo.elements.battery import CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE
from custom_components.haeo.elements.connection import CONF_MAX_POWER, CONF_SOURCE, CONF_TARGET
from custom_components.haeo.elements.grid import (
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)
from custom_components.haeo.model.const import (
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_TYPE_COST,
    OUTPUT_TYPE_DURATION,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_STATUS,
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
            CONF_HORIZON_HOURS: 1,
            CONF_PERIOD_MINUTES: 30,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
            CONF_OPTIMIZER: DEFAULT_OPTIMIZER,
        },
        entry_id="hub_entry_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_battery_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock battery subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_NAME: "test_battery",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_CAPACITY: 10000,
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
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
                CONF_IMPORT_LIMIT: 10000,
                CONF_EXPORT_LIMIT: 5000,
                CONF_IMPORT_PRICE: {
                    "live": ["sensor.import_price"],
                    "forecast": ["sensor.import_price"],
                },
                CONF_EXPORT_PRICE: {
                    "live": ["sensor.export_price"],
                    "forecast": ["sensor.export_price"],
                },
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
                CONF_MAX_POWER: 5000,
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
        "custom_components.haeo.coordinator.async_track_state_change_event",
        return_value=lambda: None,
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
    assert coordinator.entry is mock_hub_entry
    assert set(coordinator._participant_configs) == {"test_battery", "test_grid"}

    tracked_entities = set(patch_state_change_listener.call_args.args[1])
    assert tracked_entities == {
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
        mock_hub_entry,
        data={**dict(mock_hub_entry.data), CONF_UPDATE_INTERVAL_MINUTES: 12},
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
    fake_element.get_outputs.return_value = {
        OUTPUT_NAME_POWER_CONSUMED: OutputData(
            type=OUTPUT_TYPE_POWER,
            unit="kW",
            values=(1.0, 2.0),
        )
    }

    fake_network = MagicMock()
    fake_network.elements = {"test_battery": fake_element}

    optimizer_name = OPTIMIZER_NAME_MAP.get(DEFAULT_OPTIMIZER, DEFAULT_OPTIMIZER)

    generated_at = datetime(2024, 1, 1, 0, 15, tzinfo=UTC)
    expected_forecast_times = (
        int(datetime(2024, 1, 1, 0, 0, tzinfo=UTC).timestamp()),
        int(datetime(2024, 1, 1, 0, 30, tzinfo=UTC).timestamp()),
    )

    with (
        patch(
            "custom_components.haeo.coordinator.data_module.load_network",
            new_callable=AsyncMock,
        ) as mock_load,
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock) as mock_executor,
        patch("custom_components.haeo.coordinator.dismiss_optimization_failure_issue") as mock_dismiss,
        patch("custom_components.haeo.coordinator.dt_util.utcnow", return_value=generated_at),
    ):
        mock_load.return_value = fake_network
        mock_executor.return_value = 123.45
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        result = await coordinator._async_update_data()

    assert coordinator.forecast_timestamps == expected_forecast_times

    mock_load.assert_awaited_once_with(
        hass,
        mock_hub_entry,
        period_seconds=30 * 60,
        n_periods=2,
        participants=coordinator._participant_configs,
        forecast_times=expected_forecast_times,
    )

    mock_executor.assert_awaited_once_with(fake_network.optimize, optimizer_name)

    network_outputs = result["network"]
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

    battery_outputs = result["test_battery"]
    battery_output = battery_outputs[OUTPUT_NAME_POWER_CONSUMED]
    assert battery_output.type == OUTPUT_TYPE_POWER
    assert battery_output.unit == "kW"
    assert battery_output.state == 1.0
    assert battery_output.forecast == {
        datetime.fromtimestamp(expected_forecast_times[0], tz=UTC).isoformat(): 1.0,
        datetime.fromtimestamp(expected_forecast_times[1], tz=UTC).isoformat(): 2.0,
    }

    mock_dismiss.assert_called_once_with(hass, mock_hub_entry.entry_id)


async def test_async_update_data_propagates_update_failed(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Coordinator surfaces loader failures as UpdateFailed."""
    with patch(
        "custom_components.haeo.coordinator.data_module.load_network",
        side_effect=UpdateFailed("missing data"),
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
    with patch(
        "custom_components.haeo.coordinator.data_module.load_network",
        side_effect=ValueError("invalid config"),
    ):
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        with pytest.raises(ValueError, match="invalid config"):
            await coordinator._async_update_data()
