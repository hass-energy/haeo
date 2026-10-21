"""Ask which states mean on and off for on/off inputs that read entities reporting words.

An on/off input, such as whether an EV is plugged in, normally reads binary
sensors. When one of its entities reports words instead, such as a charger
reporting ``Charging`` or ``Idle``, the flow asks which states mean on and
which mean off before saving, one input at a time. Leaving one list empty
counts every other state as the opposite.
"""

from collections.abc import Mapping, Sequence
from datetime import timedelta
import logging
from typing import Final

from homeassistant.components.recorder import history
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import is_entity_value
from custom_components.haeo.elements.input_fields import InputFieldGroups, reads_calendar

_LOGGER = logging.getLogger(__name__)

STEP_STATES: Final = "states"
CONF_ON_STATES: Final = "on_states"
CONF_OFF_STATES: Final = "off_states"

# Domains whose states already read as on or off
_ON_OFF_DOMAINS: Final = frozenset({"binary_sensor", "input_boolean", "switch"})

# States that already read as on or off, or as no reading
_ON_OFF_STATES: Final = frozenset({"on", "off", "true", "false"})
_NO_READING: Final = frozenset({"unavailable", "unknown"})

# How far back the recorder is read for states to suggest
_SUGGESTION_LOOKBACK: Final = timedelta(days=7)

type FieldPath = tuple[str, str]


def _reads_words(state: State | None) -> bool:
    """Return True when an entity reports words rather than on, off, or a number."""
    if state is None or state.domain in _ON_OFF_DOMAINS:
        return False
    if isinstance(state.attributes.get("options"), Sequence):
        return True
    if state.state.lower() in _ON_OFF_STATES:
        return False
    try:
        float(state.state)
    except ValueError:
        return True
    return False


def fields_reading_words(
    hass: HomeAssistant, config: Mapping[str, object], input_fields: InputFieldGroups
) -> list[FieldPath]:
    """Return the on/off fields in a config that read an entity reporting words."""
    paths: list[FieldPath] = []
    for section_key, fields in input_fields.items():
        section = config.get(section_key)
        if not isinstance(section, Mapping):
            continue
        for field_name, field_info in fields.items():
            value = section.get(field_name)
            if (
                field_info.output_type is OutputType.AVAILABILITY
                and not reads_calendar(field_info)
                and is_entity_value(value)
                and any(_reads_words(hass.states.get(entity_id)) for entity_id in value["value"])
            ):
                paths.append((section_key, field_name))
    return paths


async def async_state_suggestions(hass: HomeAssistant, entity_ids: Sequence[str]) -> list[str]:
    """Return the states to offer for entities reporting words.

    These are the states an enum sensor lists, the states the recorder saw
    over the past week, and the current states, in that order.
    """
    found: list[str] = []
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        options = state.attributes.get("options") if state is not None else None
        if isinstance(options, Sequence) and not isinstance(options, str):
            found.extend(str(option) for option in options)
        found.extend(await _async_recorded_states(hass, entity_id))
        if state is not None:
            found.append(state.state)
    return list(dict.fromkeys(state for state in found if state not in _NO_READING))


async def _async_recorded_states(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Return the states the recorder saw for an entity over the past week, or none without it."""
    if "recorder" not in hass.config.components:
        return []
    end = dt_util.utcnow()

    def _query() -> list[str]:
        changes = history.state_changes_during_period(
            hass, end - _SUGGESTION_LOOKBACK, end, entity_id, no_attributes=True
        )
        return [state.state for state in changes.get(entity_id, [])]

    try:
        return await get_instance(hass).async_add_executor_job(_query)
    except Exception:
        _LOGGER.warning("Failed to read recorded states for %s", entity_id, exc_info=True)
        return []


__all__ = [
    "CONF_OFF_STATES",
    "CONF_ON_STATES",
    "STEP_STATES",
    "async_state_suggestions",
    "fields_reading_words",
]
