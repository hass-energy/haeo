"""Translation placeholders built from an element's configuration."""

from collections.abc import Mapping

from homeassistant.config_entries import ConfigSubentry

from custom_components.haeo.core.schema import (
    is_connection_target,
    is_constant_value,
    is_entity_value,
    is_none_value,
    is_schema_value,
)


def _format_placeholder(value: object) -> str:
    """Render a configured value as placeholder text."""
    if is_entity_value(value):
        return ", ".join(value["value"])
    if is_constant_value(value):
        return str(value["value"])
    if is_none_value(value):
        return ""
    if is_connection_target(value):
        return value["value"]
    return str(value)


def _is_section(value: object) -> bool:
    return isinstance(value, Mapping) and not is_schema_value(value) and not is_connection_target(value)


def build_translation_placeholders(subentry: ConfigSubentry) -> dict[str, str]:
    """Return translation placeholders for the entities of an element.

    Every configured field is available by its name, including the fields inside
    sections such as a connection's ``endpoints``. A top-level field takes
    precedence over a section field of the same name, and ``name`` defaults to
    the element's title.
    """
    placeholders = {key: _format_placeholder(value) for key, value in subentry.data.items() if not _is_section(value)}
    for section in subentry.data.values():
        if _is_section(section):
            for key, value in section.items():
                placeholders.setdefault(key, _format_placeholder(value))
    placeholders.setdefault("name", subentry.title)
    return placeholders


__all__ = ["build_translation_placeholders"]
