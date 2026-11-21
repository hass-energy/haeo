"""Tests for HAEO's websocket commands."""

from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.network_builder import build_network
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.websocket import BUFFER_PREVIEW, INPUT_PREVIEW, ws_buffer_preview, ws_input_preview

TIMES = (1_000_000.0, 1_001_800.0, 1_003_600.0)
DAY = 86_400


@pytest.fixture
def hub(hass: HomeAssistant) -> MockConfigEntry:
    """Add a loaded hub whose horizon is two half-hour intervals."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB, CONF_NAME: "Home"},
        entry_id="hub",
    )
    entry.add_to_hass(hass)
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    entry.runtime_data = HaeoRuntimeData(horizon_manager=Mock(get_forecast_timestamps=Mock(return_value=TIMES)))
    return entry


def _preview(hass: HomeAssistant, entity_ids: list[str], entry_id: str = "hub") -> Mock:
    """Run the preview command as an admin and return the connection it answered on."""
    connection = Mock(user=Mock(is_admin=True))
    msg = {
        "id": 1,
        "type": INPUT_PREVIEW,
        "entry_id": entry_id,
        "entity_ids": entity_ids,
        "output_type": OutputType.POWER,
        "boundaries": False,
        "non_negative": True,
    }
    ws_input_preview(hass, connection, msg)
    return connection


@pytest.mark.usefixtures("hub")
def test_preview_sums_current_values_for_now_and_across_the_horizon(hass: HomeAssistant) -> None:
    """Sensors read as their current value give the value for now, which repeats when there is no forecast."""
    hass.states.async_set("sensor.house", "1.5", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.pump", "500", {"unit_of_measurement": "W"})

    connection = _preview(hass, ["sensor.house", "sensor.pump"])

    connection.send_result.assert_called_once_with(1, {"times": list(TIMES), "values": [2.0, 2.0], "days": []})


@pytest.mark.parametrize(
    ("entry_id", "state", "error"),
    [
        pytest.param("missing", ("1", "kW"), "not_found", id="no_hub"),
        pytest.param("hub", None, "not_found", id="no_entity"),
        pytest.param("hub", ("20", "°C"), "invalid_format", id="wrong_unit"),
        pytest.param("hub", ("-3", "kW"), "invalid_format", id="negative_for_a_non_negative_input"),
    ],
)
@pytest.mark.usefixtures("hub")
def test_preview_reports_what_it_cannot_combine(
    hass: HomeAssistant, entry_id: str, state: tuple[str, str] | None, error: str
) -> None:
    """A missing hub, a missing entity, or a unit the input cannot use is an error."""
    if state is not None:
        hass.states.async_set("sensor.source", state[0], {"unit_of_measurement": state[1]})

    connection = _preview(hass, ["sensor.source"], entry_id)

    connection.send_result.assert_not_called()
    assert connection.send_error.call_args.args[:2] == (1, error)


def test_preview_is_for_admins(hass: HomeAssistant) -> None:
    """Only an admin may preview inputs, as only an admin can configure them."""
    connection = Mock(user=Mock(is_admin=False))

    with pytest.raises(Unauthorized):
        ws_input_preview(hass, connection, {"id": 1, "type": INPUT_PREVIEW})


@pytest.mark.usefixtures("hub")
async def test_preview_marks_each_local_midnight_within_the_horizon(hass: HomeAssistant) -> None:
    """The local midnights after the horizon starts and before it ends are listed, in Home Assistant's time zone."""
    await hass.config.async_set_time_zone("Australia/Sydney")
    start = datetime(2026, 1, 1, 22, tzinfo=ZoneInfo("Australia/Sydney")).timestamp()
    hub = hass.config_entries.async_get_entry("hub")
    assert hub is not None
    hub.runtime_data.horizon_manager.get_forecast_timestamps.return_value = (start, start + 2 * DAY)
    hass.states.async_set("sensor.house", "1", {"unit_of_measurement": "kW"})

    connection = _preview(hass, ["sensor.house"])

    days = connection.send_result.call_args.args[1]["days"]
    assert [datetime.fromtimestamp(day, ZoneInfo("Australia/Sydney")).isoformat() for day in days] == [
        "2026-01-02T00:00:00+11:00",
        "2026-01-03T00:00:00+11:00",
    ]


def _loaded_hub() -> dict[str, ElementConfigData]:
    """Return a battery at half charge and a grid on one bus, loaded for the two intervals."""
    bus = as_connection_target("Bus")
    battery = BatteryConfigData(
        element_type=ElementType.BATTERY,
        name="Battery",
        connection=bus,
        storage={"capacity": np.full(3, 10.0), "initial_charge_percentage": 0.5},
        limits={},
        power_limits={},
        pricing={"salvage_value": 0.0},
        efficiency={},
        advanced={"charge_limit_cost": 100.0},
    )
    grid = GridConfigData(
        element_type=ElementType.GRID,
        name="Grid",
        connection=bus,
        pricing={"price_source_target": np.full(2, 0.3), "price_target_source": np.full(2, 0.1)},
        power_limits={},
    )
    return {
        "Bus": {"element_type": ElementType.NODE, "name": "Bus", "role": {"is_source": False, "is_sink": False}},
        "Battery": battery,
        "Grid": grid,
    }


BUFFER_FORM: dict[str, object] = {
    "name": "Outage",
    "kind": "reserve",
    "participants": {"storage": ["Battery"]},
    "requirement": {"window": as_constant_value(1.0)},
    "pricing": {"shortfall_cost": as_constant_value(10.0)},
}


@pytest.fixture
def planned_hub(hub: MockConfigEntry) -> MockConfigEntry:
    """Give the hub a coordinator holding its loaded elements and the plan it solved from them."""
    configs = _loaded_hub()
    network = build_network("hub", configs, [1800.0, 1800.0])
    network.optimize()
    hub.runtime_data.horizon_manager.periods_seconds = [1800.0, 1800.0]
    hub.runtime_data.coordinator = Mock(loaded_configs=Mock(return_value=configs), network=network)
    return hub


async def _buffer_preview(hass: HomeAssistant, buffer: dict[str, object], entry_id: str = "hub") -> Mock:
    """Run the buffer preview command as an admin and return the connection it answered on."""
    connection = Mock(user=Mock(is_admin=True))
    ws_buffer_preview(hass, connection, {"id": 1, "type": BUFFER_PREVIEW, "entry_id": entry_id, "buffer": buffer})
    await hass.async_block_till_done(wait_background_tasks=True)
    return connection


@pytest.mark.usefixtures("planned_hub")
async def test_buffer_preview_plans_with_the_buffer_beside_the_plan_now(hass: HomeAssistant) -> None:
    """The preview has the buffer's line and its batteries' charge with the buffer and in the hub's plan now."""
    connection = await _buffer_preview(hass, BUFFER_FORM)

    result = connection.send_result.call_args.args[1]
    assert result["times"] == list(TIMES)
    assert result["kind"] == "reserve"
    assert result["storage"] == ["Battery"]
    assert len(result["buffer"]) == len(result["plan"]) == len(result["current"]) == len(TIMES)
    assert result["days"] == []


@pytest.mark.parametrize(
    ("entry_id", "buffer", "error"),
    [
        pytest.param("missing", BUFFER_FORM, "not_found", id="no_hub"),
        pytest.param("hub", {**BUFFER_FORM, "participants": {"storage": []}}, "invalid_format", id="no_battery"),
    ],
)
@pytest.mark.usefixtures("planned_hub")
async def test_buffer_preview_reports_what_it_cannot_plan(
    hass: HomeAssistant, entry_id: str, buffer: dict[str, object], error: str
) -> None:
    """A missing hub, or a buffer without what it needs to be planned, is an error."""
    connection = await _buffer_preview(hass, buffer, entry_id)

    connection.send_result.assert_not_called()
    assert connection.send_error.call_args.args[:2] == (1, error)


def test_buffer_preview_is_for_admins(hass: HomeAssistant) -> None:
    """Only an admin may preview a buffer, as only an admin can configure one."""
    connection = Mock(user=Mock(is_admin=False))

    with pytest.raises(Unauthorized):
        ws_buffer_preview(hass, connection, {"id": 1, "type": BUFFER_PREVIEW})
