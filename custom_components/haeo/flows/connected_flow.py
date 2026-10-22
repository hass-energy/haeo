"""Shared flow for elements that connect to one other element and configure sectioned inputs."""

from collections.abc import Mapping

from custom_components.haeo.core.schema import (
    get_connection_target_name,
    is_connection_target,
    normalize_connection_target,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows.field_schema import as_str
from custom_components.haeo.flows.sectioned_flow import FieldEntries, SectionedElementSubentryFlow
from custom_components.haeo.flows.sections import build_common_fields


def connection_target_name(value: object) -> str | None:
    """Return the element a connection target or element name names, or None for anything else."""
    return get_connection_target_name(value) if is_connection_target(value) else as_str(value)


class ConnectedElementSubentryFlow(SectionedElementSubentryFlow):
    """Flow for an element that connects to one other element and configures sectioned inputs."""

    def _current_connection(self, subentry_data: Mapping[str, object] | None) -> str:
        """Return the element the form connects to: the stored one, or the first an element can connect to."""
        stored = connection_target_name(subentry_data.get(CONF_CONNECTION)) if subentry_data else None
        if stored is not None:
            return stored
        participants = self._get_participant_names()
        return participants[0] if participants else ""

    def _top_level_entries(self, subentry_data: Mapping[str, object] | None) -> FieldEntries:
        """Return the name and connection fields."""
        return build_common_fields(
            include_connection=True,
            participants=self._get_participant_names(),
            current_connection=self._current_connection(subentry_data),
        )

    def _top_level_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, object]:
        """Return the connection's default."""
        return {CONF_CONNECTION: self._current_connection(subentry_data)}

    def _validate_fields(self, user_input: Mapping[str, object], errors: dict[str, str]) -> None:
        """Add an error when the connection names an element that is never a connection endpoint."""
        self._validate_endpoint(as_str(user_input.get(CONF_CONNECTION)), CONF_CONNECTION, errors)

    def _config_fields(
        self, user_input: Mapping[str, object], sections: Mapping[str, Mapping[str, object]]
    ) -> dict[str, object]:
        """Return the connection as a connection target."""
        _ = sections
        return {CONF_CONNECTION: normalize_connection_target(user_input[CONF_CONNECTION])}


__all__ = ["ConnectedElementSubentryFlow", "connection_target_name"]
