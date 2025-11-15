"""Extract numeric values from sequences of LP variables and floats."""

from collections.abc import Sequence

from pulp import LpAffineExpression, LpVariable
from pulp import value as pulp_value


def extract_values(sequence: Sequence[LpVariable | LpAffineExpression | float] | None) -> tuple[float, ...]:
    """Convert a sequence of PuLP variables or floats to a tuple of floats."""

    if sequence is None:
        return ()

    resolved: list[float] = []
    for item in sequence:
        if isinstance(item, (LpVariable, LpAffineExpression)):
            resolved.append(pulp_value(item))
        else:
            resolved.append(item)
    return tuple(resolved)
