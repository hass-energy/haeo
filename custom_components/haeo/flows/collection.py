"""Helpers for multi-step flows that collect a named collection of items.

This module supports a common pattern where a flow needs to collect a list of
user-defined item names first, and then iteratively ask for configuration for
each named item.
"""

from __future__ import annotations

from collections.abc import Sequence

from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
import voluptuous as vol


def build_collection_names_schema(text_label: str) -> vol.Schema:
    """Build a schema for collecting item names (one per line).

    Args:
        text_label: The field key used in the resulting schema.

    Returns:
        A voluptuous schema containing a single multiline text field.

    """

    return vol.Schema({vol.Required(text_label): TextSelector(TextSelectorConfig(multiline=True))})


def parse_collection_names(text: str) -> list[str]:
    """Parse a multiline text box into a list of names.

    - One name per line
    - Leading/trailing whitespace removed
    - Empty lines ignored

    Args:
        text: Raw multiline string from the UI.

    Returns:
        List of cleaned names in the order provided.

    """

    return [line.strip() for line in text.splitlines() if line.strip()]


def validate_collection_names(names: Sequence[str]) -> dict[str, str] | None:
    """Validate a list of collection item names.

    Validation rules:
    - At least one name
    - Names must be unique (case-sensitive)

    Returns:
        None when valid, otherwise an errors mapping suitable for config flows.

    """

    if not names:
        return {"base": "required"}

    seen: set[str] = set()
    for name in names:
        if name in seen:
            return {"base": "duplicate_names"}
        seen.add(name)

    return None


__all__ = [
    "build_collection_names_schema",
    "parse_collection_names",
    "validate_collection_names",
]
