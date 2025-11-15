from collections.abc import Sequence
from typing import cast

from pulp import LpVariable
from pulp import value as pulp_value


def extract_values(sequence: Sequence[LpVariable | float] | None) -> tuple[float, ...]:
    """Convert a sequence of PuLP variables or floats to a tuple of floats."""

    if sequence is None:
        return ()

    resolved: list[float] = []
    for item in sequence:
        if isinstance(item, LpVariable):
            resolved.append(pulp_value(item))
        else:
            resolved.append(cast("float", item))
    return tuple(resolved)
