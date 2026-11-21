"""Shared flow for elements that connect to one other element and configure sectioned inputs."""

from collections.abc import Mapping

import voluptuous as vol

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, is_element_type
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import (
    get_connection_target_name,
    is_connection_target,
    normalize_connection_target,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows.connection_selector import ConnectedElement, ConnectionSelector, ConnectionTarget
from custom_components.haeo.flows.field_schema import as_str
from custom_components.haeo.flows.sectioned_flow import FieldEntries, SectionedElementSubentryFlow
from custom_components.haeo.flows.sections import build_common_fields


def connection_target_name(value: object) -> str | None:
    """Return the element a connection target or element name names, or None for anything else."""
    return get_connection_target_name(value) if is_connection_target(value) else as_str(value)


class ConnectedElementSubentryFlow(SectionedElementSubentryFlow):
    """Flow for an element that connects to one other element and configures sectioned inputs."""

    def _connection_targets(self, subentry_data: Mapping[str, object] | None) -> list[ConnectionTarget]:
        """Return the elements this one can connect to, each with the elements already connected to it.

        An element with no switchboard role, such as an inverter, offers a DC bus.
        A stored connection to an element that no longer exists is offered too, so
        the form shows it and validation reports it.
        """
        current_id = self._get_current_subentry_id()
        others = [sub for sub in self._get_entry().subentries.values() if sub.subentry_id != current_id]
        types = {sub.title: str(sub.data.get(CONF_ELEMENT_TYPE)) for sub in others}
        connected: dict[str, list[ConnectedElement]] = {}
        for sub in others:
            target = connection_target_name(sub.data.get(CONF_CONNECTION))
            if target is not None:
                connected.setdefault(target, []).append({"name": sub.title, "element_type": types[sub.title]})

        names = self._get_participant_names()
        stored = connection_target_name(subentry_data.get(CONF_CONNECTION)) if subentry_data else None
        if stored is not None and stored not in names:
            names = [*names, stored]
        targets: list[ConnectionTarget] = []
        for name in names:
            element_type = types.get(name, "")
            dc = is_element_type(element_type) and not ELEMENT_TYPES[element_type].switchboard
            targets.append({"name": name, "element_type": element_type, "dc": dc, "elements": connected.get(name, [])})
        return targets

    def _current_connection(self, subentry_data: Mapping[str, object] | None) -> str:
        """Return the element the form connects to.

        That is the stored one, or for a new element the first bus of its kind:
        a DC bus for DC equipment such as a battery, and an AC bus otherwise.
        """
        stored = connection_target_name(subentry_data.get(CONF_CONNECTION)) if subentry_data else None
        if stored is not None:
            return stored
        targets = self._connection_targets(None)
        dc = ELEMENT_TYPES[self.element_type].dc
        suggested = next((target for target in targets if target["dc"] == dc), None)
        if suggested is not None:
            return suggested["name"]
        return targets[0]["name"] if targets else ""

    def _top_level_entries(self, subentry_data: Mapping[str, object] | None) -> FieldEntries:
        """Return the name and connection fields."""
        return {
            **build_common_fields(),
            CONF_CONNECTION: (
                vol.Required(CONF_CONNECTION),
                ConnectionSelector(
                    {"element_type": str(self.element_type), "targets": self._connection_targets(subentry_data)}
                ),
            ),
        }

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
