"""Connection element configuration flows."""

from collections.abc import Mapping
from typing import ClassVar, Final

import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import normalize_connection_target
from custom_components.haeo.core.schema.elements.connection import (
    CONF_SEGMENT_TYPE,
    CONF_SEGMENTS,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    SEGMENT_FIELDS,
)
from custom_components.haeo.elements import get_list_input_fields
from custom_components.haeo.flows.connected_flow import connection_target_name
from custom_components.haeo.flows.connection_path_selector import ConnectionPathSelector, SegmentTypeConfig
from custom_components.haeo.flows.element_flow import build_inclusion_map
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    SelectorContext,
    as_mapping,
    build_input_selector,
    has_input_value,
)
from custom_components.haeo.flows.sectioned_flow import FieldEntries, SectionedElementSubentryFlow
from custom_components.haeo.flows.sections import build_common_fields

# The form field holding the connection's endpoints and segments
CONF_PATH: Final = "path"


class ConnectionSubentryFlowHandler(SectionedElementSubentryFlow):
    """Handle connection element configuration flows.

    A connection joins two elements through an ordered list of segments, which
    the form shows as one chain from the source to the target.
    """

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = ()

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

    def _segment_types(self, context: SelectorContext) -> dict[str, SegmentTypeConfig]:
        """Return how the path element edits each kind of segment: its field, through an input element."""
        sample = {
            CONF_ELEMENT_TYPE: self.element_type,
            CONF_SEGMENTS: [{CONF_SEGMENT_TYPE: kind, field: None} for kind, field in SEGMENT_FIELDS.items()],
        }
        fields = {
            field_name: field_info
            for section in get_list_input_fields(sample).values()
            for field_name, field_info in section.items()
        }
        inclusion_map = build_inclusion_map(fields, context.entity_metadata)
        return {
            kind: {
                "field": field,
                "input": build_input_selector(
                    fields[field], kinds=("entity", "constant"), entities=inclusion_map.get(field), context=context
                ).config,
            }
            for kind, field in SEGMENT_FIELDS.items()
        }

    def _top_level_entries(self, subentry_data: Mapping[str, object] | None, context: SelectorContext) -> FieldEntries:
        """Return the name, and the path from the source through the segments to the target."""
        participants = self._get_participant_names()
        source, target = self._current_endpoints(subentry_data)
        names = [*participants, *(name for name in (source, target) if name and name not in participants)]
        types = self._participant_types()
        return {
            **build_common_fields(),
            CONF_PATH: (
                vol.Required(CONF_PATH),
                ConnectionPathSelector(
                    {
                        "participants": [{"name": name, "element_type": types.get(name, "")} for name in names],
                        "segment_types": self._segment_types(context),
                    }
                ),
            ),
        }

    def _participant_types(self) -> dict[str, str]:
        """Return each element's type by its name."""
        return {subentry.title: subentry.subentry_type for subentry in self._get_entry().subentries.values()}

    def _top_level_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, object]:
        """Return the stored path, or a new connection's first endpoints with no segments."""
        source, target = self._current_endpoints(subentry_data)
        segments = subentry_data.get(CONF_SEGMENTS, []) if subentry_data else []
        return {CONF_PATH: {CONF_SOURCE: source, CONF_TARGET: target, CONF_SEGMENTS: segments}}

    def _validate_fields(self, user_input: Mapping[str, object], errors: dict[str, str]) -> None:
        """Reject a non-endpoint, a connection from an element to itself, and a segment left without a value."""
        path = as_mapping(user_input.get(CONF_PATH))
        source = connection_target_name(path.get(CONF_SOURCE))
        target = connection_target_name(path.get(CONF_TARGET))
        self._validate_endpoint(source, CONF_PATH, errors)
        self._validate_endpoint(target, CONF_PATH, errors)
        if source and target and source == target:
            errors[CONF_PATH] = "cannot_connect_to_self"
        segments = path.get(CONF_SEGMENTS)
        for segment in segments if isinstance(segments, list) else []:
            segment_map = as_mapping(segment)
            segment_type = segment_map.get(CONF_SEGMENT_TYPE)
            field = next((field for kind, field in SEGMENT_FIELDS.items() if kind == segment_type), None)
            if field is None or not has_input_value(segment_map.get(field)):
                errors[CONF_PATH] = "segment_value_required"

    def _config_fields(
        self, user_input: Mapping[str, object], sections: Mapping[str, Mapping[str, object]]
    ) -> dict[str, object]:
        """Return the endpoints as connection targets, and the segments in order."""
        _ = sections
        path = as_mapping(user_input.get(CONF_PATH))
        segments = path.get(CONF_SEGMENTS)
        return {
            SECTION_ENDPOINTS: {
                CONF_SOURCE: normalize_connection_target(path.get(CONF_SOURCE)),
                CONF_TARGET: normalize_connection_target(path.get(CONF_TARGET)),
            },
            CONF_SEGMENTS: list(segments) if isinstance(segments, list) else [],
        }
