"""Websocket commands the frontend calls."""

from collections.abc import Sequence
from datetime import timedelta
from typing import TYPE_CHECKING, Any  # noqa: TID251  # websocket messages are JSON dicts

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.const import ERR_INVALID_FORMAT, ERR_NOT_FOUND
from homeassistant.components.websocket_api.decorators import async_response, require_admin, websocket_command
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
import numpy as np
import voluptuous as vol

from custom_components.haeo.core.adapters.buffer_preview import buffer_config, preview_buffer, storage_state_of_charge
from custom_components.haeo.core.data.loader.config_loader import load_element_config, load_fused_sensors
from custom_components.haeo.core.data.util.input_values import InputError, enforce_non_negative
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.inputs.ha_state_machine import HomeAssistantStateMachine

from .const import DOMAIN

if TYPE_CHECKING:
    from . import HaeoConfigEntry

INPUT_PREVIEW = f"{DOMAIN}/input_preview"
BUFFER_PREVIEW = f"{DOMAIN}/buffer_preview"


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register HAEO's websocket commands."""
    websocket_api.async_register_command(hass, ws_input_preview)
    websocket_api.async_register_command(hass, ws_buffer_preview)


# The name a buffer being configured takes in its preview, when it has none yet
PREVIEW_BUFFER_NAME = "buffer preview"


@require_admin
@websocket_command(
    {
        vol.Required("type"): BUFFER_PREVIEW,
        vol.Required("entry_id"): str,
        vol.Optional("replaces"): vol.Any(None, str),
        vol.Required("buffer"): dict,
    }
)
@async_response
async def ws_buffer_preview(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """Plan once with a buffer as the form has it, and return what it would hold and how the batteries would charge.

    The buffer replaces the element named ``replaces``, the one being
    reconfigured, and every other element reads its inputs as they are now. The
    plan without the buffer is the hub's own latest plan.
    """
    entry: HaeoConfigEntry | None = hass.config_entries.async_get_entry(msg["entry_id"])
    runtime_data = entry.runtime_data if entry is not None and entry.state is ConfigEntryState.LOADED else None
    coordinator = runtime_data.coordinator if runtime_data is not None else None
    if runtime_data is None or coordinator is None:
        connection.send_error(msg["id"], ERR_NOT_FOUND, "HAEO hub is not loaded")
        return
    times = runtime_data.horizon_manager.get_forecast_timestamps()
    name = msg.get("replaces") or PREVIEW_BUFFER_NAME
    draft = buffer_config(name, msg["buffer"])
    if draft is None:
        connection.send_error(msg["id"], ERR_INVALID_FORMAT, "The buffer needs a battery and a window")
        return
    try:
        loaded = load_element_config(name, draft, HomeAssistantStateMachine(hass), times)
        participants = {**coordinator.loaded_configs(), name: loaded}
        periods = runtime_data.horizon_manager.periods_seconds
        result = await hass.async_add_executor_job(preview_buffer, participants, periods, name)
    except (InputError, TypeError, ValueError) as error:
        connection.send_error(msg["id"], ERR_INVALID_FORMAT, str(error))
        return
    current = storage_state_of_charge(coordinator.network, result["storage"])
    connection.send_result(msg["id"], {"times": list(times), **result, "current": current, "days": _midnights(times)})


@require_admin
@websocket_command(
    {
        vol.Required("type"): INPUT_PREVIEW,
        vol.Required("entry_id"): str,
        vol.Required("entity_ids"): cv.entity_ids,
        vol.Required("output_type"): vol.Coerce(OutputType),
        vol.Required("boundaries"): bool,
        vol.Required("non_negative"): bool,
    }
)
@callback
def ws_input_preview(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """Combine an input's entities on the hub's horizon, as the optimizer will read them.

    The result has the horizon's boundaries, the combined values, and the
    local midnights within the horizon in Home Assistant's time zone.
    """
    entry: HaeoConfigEntry | None = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED or not entry.runtime_data:
        connection.send_error(msg["id"], ERR_NOT_FOUND, "HAEO hub is not loaded")
        return
    times = entry.runtime_data.horizon_manager.get_forecast_timestamps()
    try:
        values = load_fused_sensors(
            HomeAssistantStateMachine(hass),
            msg["entity_ids"],
            times,
            output_type=msg["output_type"],
            boundaries=msg["boundaries"],
        )
        if values is not None and msg["non_negative"]:
            values = enforce_non_negative(np.array(values)).tolist()
    except InputError as error:
        connection.send_error(msg["id"], ERR_INVALID_FORMAT, str(error))
        return
    if values is None:
        connection.send_error(msg["id"], ERR_NOT_FOUND, "An entity has no data")
        return
    connection.send_result(msg["id"], {"times": list(times), "values": values, "days": _midnights(times)})


def _midnights(times: Sequence[float]) -> list[float]:
    """Return the local midnights after the horizon starts and before it ends."""
    if not times:
        return []
    day = dt_util.start_of_local_day(dt_util.as_local(dt_util.utc_from_timestamp(times[0])))
    midnights: list[float] = []
    while True:
        day = dt_util.start_of_local_day(dt_util.as_local(day + timedelta(hours=25)))
        if day.timestamp() >= times[-1]:
            return midnights
        midnights.append(day.timestamp())


__all__ = ["BUFFER_PREVIEW", "INPUT_PREVIEW", "async_register_websocket_commands"]
