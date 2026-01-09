"""Utility functions for HAEO schema system."""

from collections.abc import Iterable
from enum import StrEnum
import re

# Type alias for unit specifications
type UnitSpec = str | type[StrEnum] | Iterable[str]


def matches_unit_spec(unit: str, spec: UnitSpec) -> bool:
    """Check if a unit string matches a unit specification.

    Args:
        unit: The unit string to check (e.g., "$/kWh", "kW")
        spec: Unit specification which can be:
            - A string: "kW" (exact match only)
            - An Enum class: UnitOfPower (matches any enum value)
            - An iterable of strings: ("*", "/", "kWh") (pattern match with wildcards)

    Returns:
        True if the unit matches the specification

    Examples:
        >>> matches_unit_spec("kW", "kW")
        True
        >>> matches_unit_spec("kW", UnitOfPower)
        True
        >>> matches_unit_spec("$/kWh", ('*', '/', "kWh"))
        True

    """
    # Handle string - exact match only
    if isinstance(spec, str):
        return unit == spec

    # Handle Enum class - check if unit matches any enum value
    if isinstance(spec, type):
        return unit in (member.value for member in spec)

    # Handle iterable of strings (tuple, etc.) - build regex pattern and match
    # At this point, spec must be Iterable[str] since we've handled list and Enum above
    pattern_parts = [("[^/]+" if part == "*" else re.escape(part)) for part in spec]
    pattern = f"^{''.join(pattern_parts)}$"
    return bool(re.match(pattern, unit))
