"""Shared utilities and mixin for element subentry config flows.

This module provides:
- get_unit_spec_for_output_type(): Map OutputType to UnitSpec for entity filtering
- build_inclusion_map(): Generate field → compatible entities mapping from input fields
- filter_compatible_entities(): Filter entity metadata by unit compatibility
- build_participant_selector(): Create dropdown selector for element names
- ElementSubentryFlow: Base class of every element subentry flow
"""

from collections.abc import Mapping, Sequence
from typing import ClassVar

from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfLength, UnitOfPower
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, is_element_type
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_ELEMENT_TYPE,
    CONF_NAME,
    HUB_SECTION_ADVANCED,
    ConnectivityLevel,
)
from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import EntityValue, as_entity_value, is_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.util import UnitSpec
from custom_components.haeo.core.units import DURATION_UNITS, ENERGY_DISTANCE_UNITS, PRICE_UNIT_SPEC, currency_symbol
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.elements.input_fields import (
    AnyInputFieldInfo,
    InputFieldGroups,
    accepts_calendar_forecast,
    localize_input_fields,
    reads_calendar,
)
from custom_components.haeo.flows.on_off_states import (
    CONF_OFF_STATES,
    CONF_ON_STATES,
    STEP_STATES,
    FieldPath,
    async_state_suggestions,
    fields_reading_words,
)


def get_unit_spec_for_output_type(output_type: OutputType) -> UnitSpec | list[UnitSpec] | None:
    """Map OutputType to the appropriate UnitSpec for entity filtering.

    Args:
        output_type: The output type from InputFieldInfo.

    Returns:
        UnitSpec for filtering compatible entities, or None if no filtering needed.

    """
    match output_type:
        case OutputType.POWER | OutputType.POWER_FLOW:
            return UnitOfPower
        case OutputType.POWER_LIMIT:
            return UnitOfPower
        case OutputType.ENERGY:
            return UnitOfEnergy
        case OutputType.STATE_OF_CHARGE | OutputType.EFFICIENCY:
            return [PERCENTAGE]
        case OutputType.PRICE:
            return PRICE_UNIT_SPEC
        case OutputType.DURATION:
            return [unit.value for unit in DURATION_UNITS]
        case OutputType.PRICE_RATE:
            return None
        case OutputType.DISTANCE:
            return UnitOfLength
        case OutputType.ENERGY_PER_DISTANCE:
            return [unit.value for unit in ENERGY_DISTANCE_UNITS]
        case _:
            # STATUS, AVAILABILITY, COST, SHADOW_PRICE - no unit filtering
            return None


def filter_compatible_entities(
    entity_metadata: list[EntityMetadata],
    accepted_units: UnitSpec | list[UnitSpec],
) -> list[str]:
    """Return entity IDs that ARE compatible with the accepted units.

    Args:
        entity_metadata: List of entity metadata from extract_entity_metadata.
        accepted_units: UnitSpec or list of UnitSpecs to match against.

    Returns:
        List of entity IDs that should be included in selection.

    """
    return [v.entity_id for v in entity_metadata if v.is_compatible_with(accepted_units)]


def build_inclusion_map(
    input_fields: Mapping[str, AnyInputFieldInfo],
    entity_metadata: list[EntityMetadata],
) -> dict[str, list[str]]:
    """Build field name → compatible entity IDs mapping from input fields.

    This dynamically generates the inclusion map by looking up each field's
    output_type and computing which entities are compatible. A field feeding
    calendar inputs includes only calendars, and a field that can read a
    calendar as a forecast also includes every calendar. A meter field only
    includes entities the recorder keeps a running total for, as it reads
    that total.

    Args:
        input_fields: Mapping of InputFieldInfo from element's schema.
        entity_metadata: List of entity metadata from extract_entity_metadata.

    Returns:
        Dict mapping field names to lists of entity IDs to include.

    """
    result: dict[str, list[str]] = {}

    calendars = [v.entity_id for v in entity_metadata if v.entity_id.startswith(f"{CALENDAR_DOMAIN}.")]
    totals = {v.entity_id for v in entity_metadata if v.keeps_running_total}
    for field_info in input_fields.values():
        unit_spec = get_unit_spec_for_output_type(field_info.output_type)
        if reads_calendar(field_info):
            result[field_info.field_name] = calendars
        elif unit_spec is not None:
            compatible = filter_compatible_entities(entity_metadata, unit_spec)
            included = [eid for eid in compatible if eid in totals] if field_info.meter is not None else compatible
            result[field_info.field_name] = (
                [*included, *calendars] if accepts_calendar_forecast(field_info) else included
            )

    return result


def build_sectioned_inclusion_map(
    input_fields: InputFieldGroups,
    entity_metadata: list[EntityMetadata],
) -> dict[str, dict[str, list[str]]]:
    """Build section -> field name -> compatible entity IDs mapping."""
    return {
        section_key: build_inclusion_map(section_fields, entity_metadata)
        for section_key, section_fields in input_fields.items()
    }


def build_participant_selector(
    participants: list[str],
    current_value: str | None = None,
) -> vol.All:
    """Build a selector for choosing element names from available participants.

    Args:
        participants: List of available element names.
        current_value: Current value to preserve if not in participants list.

    Returns:
        Voluptuous validator with SelectSelector.

    """
    options_list = list(participants)
    if current_value and current_value not in options_list:
        options_list.append(current_value)

    options: list[SelectOptionDict] = [SelectOptionDict(value=p, label=p) for p in options_list]
    return vol.All(
        vol.Coerce(str),
        vol.Strip,
        vol.Length(min=1, msg="Element name cannot be empty"),
        SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)),
    )


class ElementSubentryFlow(ConfigSubentryFlow):
    """Base of every element subentry flow.

    Provides name validation, the elements an element can connect to, and the
    save path, which first asks which states mean on and off for any on/off
    input reading an entity that reports words.
    """

    element_type: ClassVar[ElementType]

    _pending_title: str
    _pending_config: dict[str, object]
    _pending_fields: list[FieldPath]

    def _get_input_fields(self) -> InputFieldGroups:
        """Return the element type's input fields with monetary units in the user's currency."""
        currency = currency_symbol(self.hass.config.currency)
        return localize_input_fields(get_input_fields(self.element_type), currency)

    def _get_used_names(self) -> set[str]:
        """Return all configured element names excluding the current subentry."""
        current_id = self._get_current_subentry_id()
        return {
            subentry.title for subentry in self._get_entry().subentries.values() if subentry.subentry_id != current_id
        }

    def _get_participant_names(self) -> list[str]:
        """Return element names available as connection endpoints.

        Filters elements based on their connectivity level and the hub's
        advanced mode setting.
        """
        hub_entry = self._get_entry()
        advanced_mode = hub_entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
        connectable = {
            ConnectivityLevel.ALWAYS,
            ConnectivityLevel.ADVANCED if advanced_mode else ConnectivityLevel.ALWAYS,
        }
        current_id = self._get_current_subentry_id()
        return [
            subentry.title
            for subentry in hub_entry.subentries.values()
            if subentry.subentry_id != current_id
            and is_element_type(element_type := subentry.data.get(CONF_ELEMENT_TYPE))
            and ELEMENT_TYPES[element_type].connectivity in connectable
        ]

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        subentry_id = self.context.get("subentry_id")
        return subentry_id if isinstance(subentry_id, str) else None

    def _validate_name(self, name: str | None, errors: dict[str, str]) -> bool:
        """Validate an element name, adding an error and returning False when it is missing or taken."""
        if not name:
            errors[CONF_NAME] = "missing_name"
            return False
        if name in self._get_used_names():
            errors[CONF_NAME] = "name_exists"
            return False
        return True

    def _validate_endpoint(self, name: str | None, error_key: str, errors: dict[str, str]) -> None:
        """Add an error when an endpoint names an element that is never a connection endpoint.

        The participant selector keeps a saved endpoint selectable so a config
        saved before such endpoints were removed still renders, so the endpoint
        is rejected here when the form is submitted.
        """
        for subentry in self._get_entry().subentries.values():
            if (
                subentry.title == name
                and is_element_type(subentry.subentry_type)
                and ELEMENT_TYPES[subentry.subentry_type].connectivity == ConnectivityLevel.NEVER
            ):
                errors[error_key] = "invalid_endpoint"

    def _get_subentry(self) -> ConfigSubentry | None:
        """Get the subentry being reconfigured, or None for new entries."""
        try:
            return self._get_reconfigure_subentry()
        except (ValueError, UnknownSubEntry):
            return None

    async def _async_get_default_name(self) -> str:
        """Fetch the default name for the element type."""
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        return translations[f"component.{DOMAIN}.config_subentries.{self.element_type}.flow_title"]

    async def _async_save_entry(self, title: str, config: dict[str, object]) -> SubentryFlowResult:
        """Save an element's config, asking first for the on and off states of inputs reading words."""
        self._pending_title = title
        self._pending_config = config
        self._pending_fields = fields_reading_words(self.hass, config, get_input_fields(self.element_type))
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
        subentry = self._get_subentry()
        section = subentry.data.get(section_key) if subentry is not None else None
        value = section.get(field_name) if isinstance(section, Mapping) else None
        return value if is_entity_value(value) else None

    def _target_subentry(self) -> ConfigSubentry | None:
        """Return the subentry a save updates, or None when it creates a new one."""
        return self._get_subentry()

    def _write_entry(self) -> SubentryFlowResult:
        """Create the element, or update the subentry the save targets."""
        subentry = self._target_subentry()
        if subentry is not None:
            return self.async_update_and_abort(
                self._get_entry(), subentry, title=self._pending_title, data=self._pending_config
            )
        return self.async_create_entry(title=self._pending_title, data=self._pending_config)


def _states(raw: object) -> list[str]:
    """Return the states chosen in a multiple select."""
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return []
    return [str(state) for state in raw if str(state)]


__all__ = [
    "ElementSubentryFlow",
    "build_inclusion_map",
    "build_participant_selector",
    "filter_compatible_entities",
    "get_unit_spec_for_output_type",
]
