"""Flow builders for common configuration fields."""

from typing import Any

from homeassistant.helpers.selector import TextSelector, TextSelectorConfig  # type: ignore[reportUnknownVariableType]
import voluptuous as vol

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import ConnectionTarget, get_connection_target_name
from custom_components.haeo.core.schema.sections.common import CONF_CONNECTION
from custom_components.haeo.flows.element_flow import build_participant_selector


def build_common_fields(
    *,
    include_connection: bool = False,
    participants: list[str] | None = None,
    current_connection: ConnectionTarget | str | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build common field entries for config flows."""
    fields: dict[str, tuple[vol.Marker, Any]] = {
        CONF_NAME: (
            vol.Required(CONF_NAME),
            vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
        ),
    }

    if include_connection:
        connection_name = get_connection_target_name(current_connection)
        fields[CONF_CONNECTION] = (
            vol.Required(CONF_CONNECTION),
            build_participant_selector(participants or [], connection_name),
        )

    return fields


__all__ = [
    "build_common_fields",
]
