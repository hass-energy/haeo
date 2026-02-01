"""Shared definitions for details configuration sections."""

from typing import Any, Final, NotRequired, TypedDict

from homeassistant.helpers.selector import TextSelector, TextSelectorConfig  # type: ignore[reportUnknownVariableType]
import voluptuous as vol

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.flows.element_flow import build_participant_selector
from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_DETAILS: Final = "details"
CONF_CONNECTION: Final = "connection"


class DetailsConfig(TypedDict):
    """Details configuration for element identity and connectivity."""

    name: str
    connection: NotRequired[str]


class DetailsData(TypedDict):
    """Loaded details values for element identity and connectivity."""

    name: str
    connection: NotRequired[str]


def details_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard details section definition."""
    return SectionDefinition(key=SECTION_DETAILS, fields=fields, collapsed=collapsed)


def build_details_fields(
    *,
    include_connection: bool = False,
    participants: list[str] | None = None,
    current_connection: str | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build details field entries for config flows."""
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
        fields[CONF_CONNECTION] = (
            vol.Required(CONF_CONNECTION),
            build_participant_selector(participants or [], current_connection),
        )

    return fields


__all__ = [
    "CONF_CONNECTION",
    "DetailsConfig",
    "DetailsData",
    "SECTION_DETAILS",
    "build_details_fields",
    "details_section",
]