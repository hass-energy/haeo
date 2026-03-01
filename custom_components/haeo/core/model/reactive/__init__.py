"""Reactive parameter and constraint caching infrastructure for warm start optimization.

This module provides automatic dependency tracking for model elements, enabling
efficient warm start optimization where only changed constraints are updated.

The pattern is inspired by reactive frameworks like MobX:
- Parameters are declared as TrackedParam descriptors
- Constraint methods are decorated with @constraint
- Dependencies are tracked automatically during first execution
- Parameter changes invalidate only dependent constraints
"""

from .decorators import OutputMethod, ReactiveConstraint, ReactiveCost, ReactiveMethod, constraint, cost, output
from .protocols import ReactiveHost
from .tracked_param import TrackedParam

__all__ = [
    "OutputMethod",
    "ReactiveConstraint",
    "ReactiveCost",
    "ReactiveHost",
    "ReactiveMethod",
    "TrackedParam",
    "constraint",
    "cost",
    "output",
]
