"""Buffer element configuration flow."""

from collections.abc import Mapping
from typing import ClassVar

from homeassistant.helpers.selector import Selector, SelectSelector, SelectSelectorConfig, SelectSelectorMode
import voluptuous as vol

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, is_element_type
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import (
    BUFFER_KINDS,
    CONF_GENERATION,
    CONF_KIND,
    CONF_LEVEL,
    CONF_LOADS,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    KIND_RESERVE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)
from custom_components.haeo.flows.field_schema import SectionDefinition, as_mapping
from custom_components.haeo.flows.sectioned_flow import FieldEntries, SectionedElementSubentryFlow


class BufferSubentryFlowHandler(SectionedElementSubentryFlow):
    """Handle buffer element configuration flows."""

    element_type = ElementType.BUFFER

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        SectionDefinition(key=SECTION_PARTICIPANTS, fields=(CONF_LOADS, CONF_GENERATION, CONF_STORAGE)),
        SectionDefinition(key=SECTION_REQUIREMENT, fields=(CONF_WINDOW, CONF_LEVEL)),
        SectionDefinition(key=SECTION_PRICING, fields=(CONF_SHORTFALL_COST,)),
    )

    def _top_level_entries(self, subentry_data: Mapping[str, object] | None) -> FieldEntries:
        """Return the name and kind fields."""
        _ = subentry_data
        return {
            CONF_NAME: (vol.Required(CONF_NAME), str),
            CONF_KIND: (
                vol.Required(CONF_KIND),
                SelectSelector(
                    SelectSelectorConfig(
                        options=list(BUFFER_KINDS), mode=SelectSelectorMode.LIST, translation_key="buffer_kind"
                    )
                ),
            ),
        }

    def _top_level_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, object]:
        """Return the kind's default."""
        return {CONF_KIND: subentry_data.get(CONF_KIND) if subentry_data else KIND_RESERVE}

    def _section_entries(
        self,
        subentry_data: Mapping[str, object] | None,
        entity_metadata: list[EntityMetadata],
        shown_data: Mapping[str, object] | None,
    ) -> dict[str, FieldEntries]:
        """Add a multi-select of the batteries that can hold the buffer."""
        return {
            **super()._section_entries(subentry_data, entity_metadata, shown_data),
            SECTION_PARTICIPANTS: {CONF_STORAGE: (vol.Optional(CONF_STORAGE), self._storage_selector())},
        }

    def _section_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, dict[str, object]]:
        """Add the stored batteries."""
        participants = as_mapping(subentry_data.get(SECTION_PARTICIPANTS)) if subentry_data else {}
        return {
            **super()._section_defaults(subentry_data),
            SECTION_PARTICIPANTS: {CONF_STORAGE: participants.get(CONF_STORAGE, [])},
        }

    def _validate_fields(self, user_input: Mapping[str, object], errors: dict[str, str]) -> None:
        """Require at least one battery to hold the buffer."""
        if not as_mapping(user_input.get(SECTION_PARTICIPANTS)).get(CONF_STORAGE):
            errors["base"] = "buffer_storage_required"

    def _config_fields(
        self, user_input: Mapping[str, object], sections: Mapping[str, Mapping[str, object]]
    ) -> dict[str, object]:
        """Return the kind."""
        _ = sections
        return {CONF_KIND: user_input[CONF_KIND]}

    def _storage_selector(self) -> Selector[SelectSelectorConfig]:
        """Build a multi-select of the elements that can hold the buffer."""
        options = [
            subentry.title
            for subentry in self._get_entry().subentries.values()
            if is_element_type(subentry.subentry_type)
            and CONF_STORAGE in ELEMENT_TYPES[subentry.subentry_type].buffer_roles
        ]
        return SelectSelector(SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN))
