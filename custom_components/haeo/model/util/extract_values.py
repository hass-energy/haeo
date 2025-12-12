"""Extract numeric values from sequences of LP variables, constraints, and floats."""

from collections.abc import Sequence
from typing import Any

from pulp import LpAffineExpression, LpConstraint, LpVariable
from pulp import value as pulp_value

# Type alias for extractable LP values (excludes str which should pass through)
type LpValue = float | LpConstraint | LpAffineExpression | LpVariable


def extract_values(sequence: Sequence[Any] | None) -> tuple[Any, ...]:
    """Convert a sequence of PuLP types to resolved values.

    Args:
        sequence: A sequence of LP variables, constraints, expressions, floats, or other values.
            - LpConstraint: Extracts shadow price via .pi (defaults to 0.0 if None)
            - LpVariable/LpAffineExpression: Uses pulp.value() to resolve
            - float/int: Converts to float
            - Other types (e.g., str): Passes through unchanged

    Returns:
        A tuple of resolved values.

    """
    if sequence is None:
        return ()

    resolved: list[Any] = []
    for item in sequence:
        if isinstance(item, LpConstraint):
            # Extract shadow price from constraint
            resolved.append(item.pi if item.pi is not None else 0.0)
        elif isinstance(item, (LpVariable, LpAffineExpression)):
            # Resolve LP variable/expression to float
            resolved.append(float(pulp_value(item)))
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            # Convert numeric types to float
            resolved.append(float(item))
        else:
            # Pass through other types unchanged (e.g., strings)
            resolved.append(item)
    return tuple(resolved)
