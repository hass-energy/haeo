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
from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from homeassistant.util import dt as dt_util
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import EntityValue, as_entity_value, is_entity_value
from custom_components.haeo.elements import get_input_fields
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


class ElementSubentryFlow(ConfigSubentryFlow):
    """Subentry flow that saves an element, first asking for the on and off states its inputs need."""

    _pending_title: str
    _pending_config: dict[str, object]
    _pending_fields: list[FieldPath]

    async def _async_save_entry(self, title: str, config: dict[str, object]) -> SubentryFlowResult:
        """Save an element's config, asking first for the on and off states of inputs reading words."""
        input_fields = get_input_fields(str(config[CONF_ELEMENT_TYPE]))
        self._pending_title = title
        self._pending_config = config
        self._pending_fields = fields_reading_words(self.hass, config, input_fields)
        return await self._async_next_states_step(None)

    async def async_step_states(self, user_input: dict[str, object] | None = None) -> SubentryFlowResult:
        """Ask which states mean on and off for one input reading words."""
        section_key, field_name = self._pending_fields[0]
        value = self._pending_value(section_key, field_name)

        errors: dict[str, str] = {}
        if user_input is not None:
            on_states = _states(user_input.get(CONF_ON_STATES))
            off_states = _states(user_input.get(CONF_OFF_STATES))
            if not on_states and not off_states:
                errors["base"] = "states_required"
            else:
                self._pending_section(section_key)[field_name] = as_entity_value(
                    list(value["value"]), on_states=on_states, off_states=off_states
                )
                self._pending_fields.pop(0)
                return await self._async_next_states_step(None)
        return await self._async_next_states_step(errors)

    async def _async_next_states_step(self, errors: dict[str, str] | None) -> SubentryFlowResult:
        """Show the states form for the next input reading words, or save once none are left."""
        if not self._pending_fields:
            return self._write_entry()
        section_key, field_name = self._pending_fields[0]
        entity_ids = list(self._pending_value(section_key, field_name)["value"])

        options = await async_state_suggestions(self.hass, entity_ids)
        selector = SelectSelector(
            SelectSelectorConfig(options=options, multiple=True, custom_value=True, mode=SelectSelectorMode.DROPDOWN)
        )
        schema = vol.Schema({vol.Optional(CONF_ON_STATES): selector, vol.Optional(CONF_OFF_STATES): selector})
        stored = self._stored_value(section_key, field_name)
        suggested = {
            CONF_ON_STATES: list(stored.get("on_states", ())) if stored is not None else [],
            CONF_OFF_STATES: list(stored.get("off_states", ())) if stored is not None else [],
        }
        names = [
            state.name if (state := self.hass.states.get(entity_id)) is not None else entity_id
            for entity_id in entity_ids
        ]
        return self.async_show_form(
            step_id=STEP_STATES,
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders={"entities": ", ".join(names)},
        )

    def _pending_section(self, section_key: str) -> dict[str, object]:
        """Return a section of the config being saved."""
        section = self._pending_config[section_key]
        if not isinstance(section, dict):
            msg = f"Section {section_key} is not a mapping"
            raise TypeError(msg)
        return section

    def _pending_value(self, section_key: str, field_name: str) -> EntityValue:
        """Return the entity value of a field in the config being saved."""
        value = self._pending_section(section_key)[field_name]
        if not is_entity_value(value):
            msg = f"Field {section_key}.{field_name} is not entity-driven"
            raise TypeError(msg)
        return value

    def _stored_value(self, section_key: str, field_name: str) -> EntityValue | None:
        """Return the value a reconfigured element stored for a field, or None for a new element."""
        subentry = self._reconfigured_subentry()
        section = subentry.data.get(section_key) if subentry is not None else None
        value = section.get(field_name) if isinstance(section, Mapping) else None
        return value if is_entity_value(value) else None

    def _write_entry(self) -> SubentryFlowResult:
        """Create the element, or update it when reconfiguring."""
        subentry = self._reconfigured_subentry()
        if subentry is not None:
            return self.async_update_and_abort(
                self._get_entry(), subentry, title=self._pending_title, data=self._pending_config
            )
        return self.async_create_entry(title=self._pending_title, data=self._pending_config)

    def _reconfigured_subentry(self) -> ConfigSubentry | None:
        """Return the subentry being reconfigured, or None for a new element."""
        try:
            return self._get_reconfigure_subentry()
        except (ValueError, UnknownSubEntry):
            return None


def _states(raw: object) -> list[str]:
    """Return the states chosen in a multiple select."""
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return []
    return [str(state) for state in raw if str(state)]


__all__ = [
    "CONF_OFF_STATES",
    "CONF_ON_STATES",
    "STEP_STATES",
    "ElementSubentryFlow",
    "async_state_suggestions",
    "fields_reading_words",
]
