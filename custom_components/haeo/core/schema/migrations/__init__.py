"""Schema migration transformations with no Home Assistant dependencies."""

from collections.abc import Mapping


def section_dict(data: Mapping[str, object], section: str) -> dict[str, object]:
    """Return a copy of a config section, empty when the config has none."""
    section_data = data.get(section, {})
    return dict(section_data) if isinstance(section_data, Mapping) else {}


__all__ = ["section_dict"]
