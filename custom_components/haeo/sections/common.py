"""Shared definitions for common configuration sections."""

from typing import Any, Final, NotRequired, TypedDict

from homeassistant.helpers.selector import TextSelector, TextSelectorConfig  # type: ignore[reportUnknownVariableType]
import voluptuous as vol

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.flows.element_flow import build_participant_selector
from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_COMMON: Final = "common"
CONF_CONNECTION: Final = "connection"

type ConnectionTarget = str


class CommonConfig(TypedDict):
    """Common configuration for element identity and connectivity."""

    name: str
    connection: NotRequired[ConnectionTarget]


class CommonData(TypedDict):
    """Loaded common values for element identity and connectivity."""

    name: str
    connection: NotRequired[ConnectionTarget]


class ConnectedCommonConfig(TypedDict):
    """Common configuration with a required connection target."""

    name: str
    connection: ConnectionTarget


class ConnectedCommonData(TypedDict):
    """Loaded common values with a required connection target."""

    name: str
    connection: ConnectionTarget


def common_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard common section definition."""
    return SectionDefinition(key=SECTION_COMMON, fields=fields, collapsed=collapsed)


def build_common_fields(
    *,
    include_connection: bool = False,
    participants: list[str] | None = None,
    current_connection: str | None = None,
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
        fields[CONF_CONNECTION] = (
            vol.Required(CONF_CONNECTION),
            build_participant_selector(participants or [], current_connection),
        )

    return fields


__all__ = [
    "CONF_CONNECTION",
    "ConnectionTarget",
    "SECTION_COMMON",
    "CommonConfig",
    "CommonData",
    "ConnectedCommonConfig",
    "ConnectedCommonData",
    "build_common_fields",
    "common_section",
]
