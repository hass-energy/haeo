"""Tests for HAEO's websocket commands."""

from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.websocket import INPUT_PREVIEW, ws_input_preview

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
