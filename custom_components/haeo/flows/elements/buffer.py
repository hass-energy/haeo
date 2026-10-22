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
    BUFFER_ROLES,
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
    BufferRole,
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
        self, subentry_data: Mapping[str, object] | None, entity_metadata: list[EntityMetadata]
    ) -> dict[str, FieldEntries]:
        """Add a multi-select of elements for each participant list."""
        return {
            **super()._section_entries(subentry_data, entity_metadata),
            SECTION_PARTICIPANTS: {
                field: (vol.Optional(field), self._participant_selector(field)) for field in BUFFER_ROLES
            },
        }

    def _section_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, dict[str, object]]:
        """Add the stored participant lists."""
        participants = as_mapping(subentry_data.get(SECTION_PARTICIPANTS)) if subentry_data else {}
        return {
            **super()._section_defaults(subentry_data),
            SECTION_PARTICIPANTS: {field: participants.get(field, []) for field in BUFFER_ROLES},
        }

    def _validate_fields(self, user_input: Mapping[str, object], errors: dict[str, str]) -> None:
        """Require at least one battery to hold the buffer."""
        if not as_mapping(user_input.get(SECTION_PARTICIPANTS)).get(CONF_STORAGE):
            errors["base"] = "buffer_storage_required"

    def _config_fields(
        self, user_input: Mapping[str, object], sections: Mapping[str, Mapping[str, object]]
    ) -> dict[str, object]:
        """Return the kind and the non-empty participant lists."""
        _ = sections
        participants = as_mapping(user_input.get(SECTION_PARTICIPANTS))
        return {
            CONF_KIND: user_input[CONF_KIND],
            SECTION_PARTICIPANTS: {
                field: list(values)
                for field in BUFFER_ROLES
                if isinstance(values := participants.get(field), list) and values
            },
        }

    def _participant_selector(self, field: BufferRole) -> Selector[SelectSelectorConfig]:
        """Build a multi-select of the elements that can take a participant list's role."""
        current_id = self._get_current_subentry_id()
        options = [
            subentry.title
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_id != current_id
            and is_element_type(subentry.subentry_type)
            and field in ELEMENT_TYPES[subentry.subentry_type].buffer_roles
        ]
        return SelectSelector(SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN))
