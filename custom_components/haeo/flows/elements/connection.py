"""Connection element configuration flows."""

from collections.abc import Mapping
from typing import ClassVar

import voluptuous as vol

from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.schema import normalize_connection_target
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
)
from custom_components.haeo.flows.connected_flow import connection_target_name
from custom_components.haeo.flows.element_flow import build_participant_selector
from custom_components.haeo.flows.field_schema import SectionDefinition, as_mapping
from custom_components.haeo.flows.sectioned_flow import FieldEntries, SectionedElementSubentryFlow
from custom_components.haeo.flows.sections import efficiency_section, power_limits_section, pricing_section


class ConnectionSubentryFlowHandler(SectionedElementSubentryFlow):
    """Handle connection element configuration flows.

    A connection joins two elements, so instead of one connection field it
    has source and target fields in its endpoints section.
    """

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        SectionDefinition(key=SECTION_ENDPOINTS, fields=(CONF_SOURCE, CONF_TARGET), collapsed=False),
        power_limits_section((CONF_MAX_POWER_SOURCE_TARGET,), collapsed=False),
        pricing_section((CONF_PRICE_SOURCE_TARGET,), collapsed=False),
        efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET,), collapsed=True),
    )

    def _current_endpoints(self, subentry_data: Mapping[str, object] | None) -> tuple[str, str]:
        """Return the source and target the form shows: the stored ones, or the first elements available."""
        endpoints = as_mapping(subentry_data.get(SECTION_ENDPOINTS)) if subentry_data else {}
        source = connection_target_name(endpoints.get(CONF_SOURCE))
        target = connection_target_name(endpoints.get(CONF_TARGET))
        participants = self._get_participant_names()
        return (
            source if source is not None else (participants[0] if participants else ""),
            target if target is not None else (participants[min(1, len(participants) - 1)] if participants else ""),
        )

    def _section_entries(
        self, subentry_data: Mapping[str, object] | None, entity_metadata: list[EntityMetadata]
    ) -> dict[str, FieldEntries]:
        """Add the source and target selectors to the endpoints section."""
        participants = self._get_participant_names()
        source, target = self._current_endpoints(subentry_data)
        endpoint_fields: FieldEntries = {
            CONF_SOURCE: (vol.Required(CONF_SOURCE), build_participant_selector(participants, source)),
            CONF_TARGET: (vol.Required(CONF_TARGET), build_participant_selector(participants, target)),
        }
        return {**super()._section_entries(subentry_data, entity_metadata), SECTION_ENDPOINTS: endpoint_fields}

    def _section_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, dict[str, object]]:
        """Add the source and target defaults."""
        source, target = self._current_endpoints(subentry_data)
        return {
            **super()._section_defaults(subentry_data),
            SECTION_ENDPOINTS: {CONF_SOURCE: source, CONF_TARGET: target},
        }

    def _validate_fields(self, user_input: Mapping[str, object], errors: dict[str, str]) -> None:
        """Reject endpoints that are never connection endpoints, and a connection from an element to itself."""
        endpoints = as_mapping(user_input.get(SECTION_ENDPOINTS))
        source = connection_target_name(endpoints.get(CONF_SOURCE))
        target = connection_target_name(endpoints.get(CONF_TARGET))
        self._validate_endpoint(source, SECTION_ENDPOINTS, errors)
        self._validate_endpoint(target, SECTION_ENDPOINTS, errors)
        if source and target and source == target:
            errors[SECTION_ENDPOINTS] = "cannot_connect_to_self"

    def _config_fields(
        self, user_input: Mapping[str, object], sections: Mapping[str, Mapping[str, object]]
    ) -> dict[str, object]:
        """Return the endpoints with the source and target as connection targets."""
        _ = user_input
        endpoints = sections[SECTION_ENDPOINTS]
        return {
            SECTION_ENDPOINTS: {
                key: normalize_connection_target(value) if key in (CONF_SOURCE, CONF_TARGET) else value
                for key, value in endpoints.items()
            }
        }
