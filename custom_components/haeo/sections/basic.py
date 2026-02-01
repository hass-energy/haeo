"""Shared definitions for basic configuration sections."""

from typing import Any, Final, TypedDict

from homeassistant.helpers.selector import TextSelector, TextSelectorConfig  # type: ignore[reportUnknownVariableType]
import voluptuous as vol

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.flows.element_flow import build_participant_selector
from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_BASIC: Final = "basic"
CONF_CONNECTION: Final = "connection"


class BasicNameConfig(TypedDict):
    """Basic section with a name field."""

    name: str


class BasicNameConnectionConfig(TypedDict):
    """Basic section with name and connection fields."""

    name: str
    connection: str


class BasicNameData(TypedDict):
    """Loaded basic values with a name field."""

    name: str


class BasicNameConnectionData(TypedDict):
    """Loaded basic values with name and connection fields."""

    name: str
    connection: str


def basic_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard basic section definition."""
    return SectionDefinition(key=SECTION_BASIC, fields=fields, collapsed=collapsed)


def build_name_field() -> tuple[vol.Marker, Any]:
    """Build the name field entry for config flows."""
    return (
        vol.Required(CONF_NAME),
        vol.All(
            vol.Coerce(str),
            vol.Strip,
            vol.Length(min=1, msg="Name cannot be empty"),
            TextSelector(TextSelectorConfig()),
        ),
    )


def build_connection_field(
    participants: list[str],
    current_connection: str | None = None,
) -> tuple[vol.Marker, Any]:
    """Build the connection field entry for config flows."""
    return (
        vol.Required(CONF_CONNECTION),
        build_participant_selector(participants, current_connection),
    )


__all__ = [  # noqa: RUF022
    "basic_section",
    "BasicNameConfig",
    "BasicNameConnectionConfig",
    "BasicNameConnectionData",
    "BasicNameData",
    "build_connection_field",
    "build_name_field",
    "CONF_CONNECTION",
    "SECTION_BASIC",
]
