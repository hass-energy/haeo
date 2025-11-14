"""Tests for the HAEO data update coordinator."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.coordinator import (
    HaeoDataUpdateCoordinator,
    _build_coordinator_output,
    _collect_entity_ids,
    _extract_entity_ids_from_config,
)
from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ElementConfigSchema,
)
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
)
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET
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
    OUTPUT_NAME_POWER_PRODUCED,
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
    assert coordinator.config_entry is mock_hub_entry
    assert set(coordinator._participant_configs) == {"test_battery", "test_grid"}

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
    empty_element = MagicMock()
    empty_element.get_outputs.return_value = {}
    fake_network.elements = {
        "test_battery": fake_element,
        "empty": empty_element,
    }

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

    mock_load.assert_awaited_once_with(
        hass,
        mock_hub_entry,
        period_seconds=30 * 60,
        n_periods=2,
        participants=coordinator._participant_configs,
        forecast_times=expected_forecast_times,
    )

    mock_executor.assert_awaited_once_with(fake_network.optimize)

    network_outputs = result[slugify(mock_hub_entry.title)]
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
    # Forecast timestamps should be datetime objects in local timezone
    local_tz = dt_util.get_default_time_zone()
    assert battery_output.forecast == {
        datetime.fromtimestamp(expected_forecast_times[0], tz=local_tz): 1.0,
        datetime.fromtimestamp(expected_forecast_times[1], tz=local_tz): 2.0,
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


def test_collect_entity_ids_handles_nested_structures() -> None:
    """_collect_entity_ids should traverse mappings and sequences recursively."""

    value = {
        "single": "sensor.solo",
        "group": ["sensor.one", "sensor.two"],
        "nested": {
            "inner": ("sensor.three",),
        },
    }

    assert _collect_entity_ids(value) == {"sensor.solo", "sensor.one", "sensor.two", "sensor.three"}


def test_collect_entity_ids_returns_empty_for_unknown_types() -> None:
    """Non-iterable values should yield an empty set of entity identifiers."""

    assert _collect_entity_ids(123) == set()


def test_extract_entity_ids_skips_constant_fields() -> None:
    """_extract_entity_ids_from_config should ignore constant-only fields."""

    config: ElementConfigSchema = {
        CONF_NAME: "Battery",
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
        CONF_CAPACITY: "sensor.capacity",
        CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.soc",
        CONF_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_EFFICIENCY: 95.0,
    }

    extracted = _extract_entity_ids_from_config(config)

    assert extracted == {"sensor.capacity", "sensor.soc"}


def test_extract_entity_ids_skips_missing_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fields without schema metadata should be ignored when collecting entity identifiers."""

    config: ElementConfigSchema = {
        CONF_NAME: "Battery",
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
        CONF_CAPACITY: "sensor.capacity",
        CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.soc",
        CONF_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_EFFICIENCY: 95.0,
    }

    original_get_field_meta = _extract_entity_ids_from_config.__globals__["get_field_meta"]

    def fake_get_field_meta(field_name: str, config_class: type) -> Any:
        if field_name == CONF_CAPACITY:
            return None
        return original_get_field_meta(field_name, config_class)

    monkeypatch.setattr("custom_components.haeo.coordinator.get_field_meta", fake_get_field_meta)

    extracted = _extract_entity_ids_from_config(config)

    assert extracted == {"sensor.soc"}


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
    }

    def broken_collect(_value: Any) -> set[str]:
        msg = "boom"
        raise TypeError(msg)

    monkeypatch.setattr("custom_components.haeo.coordinator._collect_entity_ids", broken_collect)

    extracted = _extract_entity_ids_from_config(config)

    assert extracted == set()


def test_build_coordinator_output_emits_forecast_entries() -> None:
    """Forecast data is mapped onto ISO timestamps when lengths match."""

    base_time = datetime(2024, 6, 1, tzinfo=UTC)
    forecast_times = (int(base_time.timestamp()), int((base_time + timedelta(minutes=30)).timestamp()))
    output = _build_coordinator_output(
        OUTPUT_NAME_POWER_PRODUCED,
        OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.2, 3.4)),
        forecast_times=forecast_times,
    )

    assert output.forecast is not None
    assert list(output.forecast.values()) == [1.2, 3.4]


def test_build_coordinator_output_handles_timestamp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """ValueError from datetime conversion should clear the forecast payload."""

    class _ErrorDatetime:
        @staticmethod
        def fromtimestamp(*_args: Any, **_kwargs: Any) -> None:
            raise ValueError

    monkeypatch.setattr("custom_components.haeo.coordinator.datetime", _ErrorDatetime)

    output = _build_coordinator_output(
        OUTPUT_NAME_POWER_PRODUCED,
        OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0, 2.0)),
        forecast_times=(1, 2),
    )

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
async def test_state_change_handler_requests_refresh(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """State change events should trigger a coordinator refresh."""

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with patch.object(coordinator, "async_request_refresh", new_callable=AsyncMock) as request_mock:
        await coordinator._state_change_handler(None)

    request_mock.assert_awaited_once()
