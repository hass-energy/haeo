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


def extract_unit_wildcard(unit: str, specs: Iterable[Iterable[str]]) -> str | None:
    """Extract the first wildcard (``*``) match from *unit* against *specs*.

    Each spec is a tuple-style unit pattern (e.g. ``("*", "/", "kWh")``).
    Returns the text matched by the first ``*`` in the first matching spec,
    or ``None`` if no spec matches.

    Examples:
        >>> extract_unit_wildcard("£/kWh", [("*", "/", "kWh"), ("*", "/", "MWh")])
        '£'
        >>> extract_unit_wildcard("kW", [("*", "/", "kWh")])  # no match
        None

    """
    for spec in specs:
        parts = list(spec)
        pattern_parts = [("([^/]+)" if part == "*" else re.escape(part)) for part in parts]
        m = re.match(f"^{''.join(pattern_parts)}$", unit)
        if m:
            return m.group(1)
    return None
