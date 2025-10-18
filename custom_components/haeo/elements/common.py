"""Common type definitions and type guards for HAEO integration.

This module provides type-level guarantees for invariants that hold due to
architectural constraints, eliminating the need for defensive runtime checks.
"""

from typing import Literal, Required, TypedDict, TypeGuard

from homeassistant.config_entries import ConfigEntry

# Exhaustive list of element types - using Literal ensures type safety
ElementType = Literal[
    "battery",
    "connection",
    "photovoltaics",
    "grid",
    "constant_load",
    "forecast_load",
    "node",
]


class SubentryDataDict(TypedDict, total=False):
    """Typed dictionary for subentry data with required name_value field.

    This TypedDict enforces that name_value must always be present when
    a subentry is created through our config flows, eliminating defensive
    None checks throughout the codebase.
    """

    name_value: Required[str]  # All element subentries MUST have a name
    type: str  # Element type


def has_limits(import_limit: float | None, export_limit: float | None) -> TypeGuard[tuple[float | None, float | None]]:
    """Type guard to check if at least one limit is set.

    This enables the type checker to understand that within the guarded block,
    at least one of the values is not None.

    Args:
        import_limit: Optional import power limit
        export_limit: Optional export power limit

    Returns:
        True if at least one limit is set

    """
    return import_limit is not None or export_limit is not None


def assert_config_entry_exists(entry: ConfigEntry | None, entry_id: str) -> ConfigEntry:
    """Assert that a config entry exists.

    This is used at boundaries where we control the entry IDs and the entry
    must exist by design. If it doesn't, it's a programming error, not a
    recoverable runtime condition.

    Args:
        entry: The config entry or None
        entry_id: The entry ID for error reporting

    Returns:
        The config entry (guaranteed non-None)

    Raises:
        RuntimeError: If entry is None (programming error)

    """
    if entry is None:
        msg = f"Config entry {entry_id} must exist"
        raise RuntimeError(msg)
    return entry


def assert_subentry_has_name(name: str | None, subentry_id: str) -> str:
    """Assert that a subentry has a name_value field.

    This is used after subentry creation where our config flows guarantee
    that name_value is always set. If it's missing, it's a programming error.

    Args:
        name: The name value or None
        subentry_id: The subentry ID for error reporting

    Returns:
        The name (guaranteed non-None)

    Raises:
        RuntimeError: If name is None (programming error)

    """
    if name is None:
        msg = f"Subentry {subentry_id} must have name_value"
        raise RuntimeError(msg)
    return name
