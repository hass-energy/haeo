# Reactive Model Architecture Plan

## Overview

Refactor the model layer to use a reactive/signal-based architecture where:

1. Model elements declare updateable parameters
2. Setting parameters invalidates cached constraint expressions
3. At `optimize()` time, recompute only invalidated expressions and apply changes to HiGHS
4. Automatic dependency tracking (like MobX) avoids manual invalidation declarations

## Goals

- **Declarative**: Parameters are properties that cascade updates automatically
- **Lazy**: Constraint expressions are only recomputed when accessed after invalidation
- **Efficient**: Only changed coefficients/bounds are pushed to HiGHS
- **HA-Agnostic**: Model layer remains pure Python with no Home Assistant dependencies

## HiGHS API Reference

The following APIs allow in-place model modification for warm start:

| API                                  | Purpose                              | Parameters                      |
| ------------------------------------ | ------------------------------------ | ------------------------------- |
| `changeCoeff(row, col, value)`       | Modify constraint matrix coefficient | row index, col index, new value |
| `changeColCost(col, cost)`           | Modify objective coefficient         | column index, new cost          |
| `changeRowBounds(row, lower, upper)` | Modify constraint bounds             | row index, lb, ub               |
| `changeColBounds(col, lower, upper)` | Modify variable bounds               | column index, lb, ub            |

Access patterns for indices:

- `highs_var.index` → column index
- `highs_cons.index` → row index
- `highs_linear_expression.idxs` → list of variable indices
- `highs_linear_expression.vals` → list of coefficients
- `highs_linear_expression.bounds` → tuple of (lower, upper) bounds

## Architecture Design

### Core Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                        Network                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Elements Dict                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │   │
│  │  │  Battery   │  │    Grid    │  │  PowerConnection   │  │   │
│  │  │            │  │            │  │                    │  │   │
│  │  │ capacity ──┼──┼────────────┼──┼─► _invalidated     │  │   │
│  │  │ init_chg ──┼──┼────────────┼──┼─► constraint cache │  │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    optimize()                             │   │
│  │  1. For each element with _invalidated constraints:       │   │
│  │     a. Recompute constraint expressions                   │   │
│  │     b. Apply to HiGHS (add new or update existing)        │   │
│  │  2. Run solver                                            │   │
│  │  3. Return results                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Tracking Strategy

**Automatic tracking** (preferred per user request):

1. Each constraint method is decorated with `@cached_constraint`
2. First call records which parameters were accessed during execution
3. Subsequent calls return cached expression unless any accessed parameter changed
4. Parameter access tracked via descriptor `__get__` recording to thread-local context

**Implementation approach**:

```python
# Context for tracking parameter access during constraint computation
_tracking_context: ContextVar[set[str] | None] = ContextVar("tracking", default=None)


class TrackedParam[T]:
    """Descriptor that tracks access for automatic dependency detection."""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        self._private = f"_param_{name}"

    def __get__(self, obj: object | None, objtype: type) -> T:
        if obj is None:
            return self  # type: ignore
        # Record access if tracking is active
        tracking = _tracking_context.get()
        if tracking is not None:
            tracking.add(self._name)
        return getattr(obj, self._private)

    def __set__(self, obj: object, value: T) -> None:
        old = getattr(obj, self._private, None)
        setattr(obj, self._private, value)
        if old is not None and old != value:
            # Invalidate any constraints that depend on this param
            obj._invalidate_dependents(self._name)


class cached_constraint:
    """Decorator that caches constraint expressions with automatic dependency tracking."""

    def __init__(self, fn: Callable) -> None:
        self._fn = fn
        self._name = fn.__name__

    def __get__(self, obj: object | None, objtype: type) -> Callable:
        if obj is None:
            return self._fn
        return partial(self._call, obj)

    def _call(self, obj: object) -> highs_linear_expression | list[highs_linear_expression]:
        cache = getattr(obj, "_constraint_cache", None)
        if cache is None:
            cache = {}
            obj._constraint_cache = cache

        # Return cached if not invalidated
        if self._name in cache and self._name not in obj._invalidated:
            return cache[self._name]

        # Track parameter access during computation
        tracking: set[str] = set()
        token = _tracking_context.set(tracking)
        try:
            result = self._fn(obj)
        finally:
            _tracking_context.reset(token)

        # Store result and dependencies
        cache[self._name] = result
        obj._constraint_deps[self._name] = tracking
        obj._invalidated.discard(self._name)

        return result
```

### Constraint Application

When `optimize()` is called, apply pending constraint changes:

```python
def apply_constraints(self, solver: Highs) -> None:
    """Apply any invalidated constraints to the solver."""
    for constraint_name in list(self._invalidated):
        # Get cached constraint method
        method = getattr(self, constraint_name)
        expr = method()  # Calls @cached_constraint, recomputes if needed

        existing = self._constraints.get(constraint_name)
        if existing is None:
            # First time: add constraint
            if isinstance(expr, list):
                self._constraints[constraint_name] = solver.addConstrs(expr)
            else:
                self._constraints[constraint_name] = solver.addConstr(expr)
        else:
            # Update existing constraint(s)
            self._update_constraint(solver, existing, expr)


def _update_constraint(
    self,
    solver: Highs,
    existing: highs_cons | list[highs_cons],
    expr: highs_linear_expression | list[highs_linear_expression],
) -> None:
    """Update existing constraint(s) with new expression(s)."""
    if isinstance(existing, list):
        for cons, exp in zip(existing, expr):
            self._update_single_constraint(solver, cons, exp)
    else:
        self._update_single_constraint(solver, existing, expr)


def _update_single_constraint(
    self,
    solver: Highs,
    cons: highs_cons,
    expr: highs_linear_expression,
) -> None:
    """Update a single constraint with new expression."""
    # Update bounds
    if expr.bounds is not None:
        solver.changeRowBounds(cons.index, expr.bounds[0], expr.bounds[1])

    # Update coefficients
    # Get existing expression to compare
    old_expr = solver.getExpr(cons)
    old_coeffs = dict(zip(old_expr.idxs, old_expr.vals))
    new_coeffs = dict(zip(expr.idxs, expr.vals))

    # Apply coefficient changes
    all_vars = set(old_coeffs) | set(new_coeffs)
    for var_idx in all_vars:
        old_val = old_coeffs.get(var_idx, 0.0)
        new_val = new_coeffs.get(var_idx, 0.0)
        if old_val != new_val:
            solver.changeCoeff(cons.index, var_idx, new_val)
```

## Implementation Plan

### Phase 1: Core Infrastructure (`model/reactive.py`) ✅ COMPLETE

Created the reactive parameter and constraint caching infrastructure:

1. ✅ `TrackedParam[T]` descriptor for parameters
2. ✅ `cached_constraint` decorator for constraint methods
3. ✅ `cached_cost` decorator for cost methods
4. ✅ `_tracking_context` for automatic dependency detection
5. ✅ `ReactiveElement` base class with:
    - `_invalidated: set[str]` - constraint names needing recomputation
    - `_constraint_cache: dict[str, Any]` - cached constraint expressions
    - `_constraint_deps: dict[str, set[str]]` - param names each constraint depends on
    - `invalidate_dependents(param_name)` - mark dependent constraints invalid
    - `apply_constraints(solver)` - apply all pending changes
    - `apply_costs(solver)` - apply pending cost changes

Tests: `tests/model/test_reactive.py` (18 passing tests)

### Phase 2: Refactor Battery (`model/battery.py`)

Convert Battery to use reactive parameters:

1. Convert `capacity`, `initial_charge` to `TrackedParam` descriptors
2. Convert constraint-building code to `@cached_constraint` methods:
    - `soc_max_constraint()` → returns SOC max expression
    - `initial_charge_constraint()` → returns initial charge expression
    - etc.
3. Remove `build_constraints()` method
4. Remove `update()` method
5. Update `__init__` to initialize reactive infrastructure

### Phase 3: Refactor PowerConnection (`model/power_connection.py`)

Convert PowerConnection to use reactive parameters:

1. Convert `price_source_target`, `price_target_source`, `max_power_source_target`, `max_power_target_source`, `efficiency` to `TrackedParam`
2. Convert constraint methods to `@cached_constraint`
3. Convert `cost()` to `@cached_cost` (similar pattern for objective)
4. Remove `update()` method

### Phase 4: Refactor Network (`model/network.py`)

Update Network to use reactive apply pattern:

1. Remove `_constraints_built` flag
2. Update `optimize()` to call `apply_constraints()` on all elements before solving
3. Apply cost expressions similarly
4. Handle first-run vs update cases transparently

### Phase 5: Wire to Coordinator (`coordinator.py`)

Connect input entity changes to model parameters:

1. When input entity state changes, coordinator sets corresponding model parameter
2. The `TrackedParam` descriptor invalidates dependent constraints automatically
3. Next `optimize()` call applies changes and solves

### Phase 6: Testing

1. Update existing warm start tests to use new pattern
2. Add tests for automatic dependency tracking
3. Add tests for constraint update efficiency (only changed coefficients)
4. Add tests for mixed add/update scenarios

## File Changes Summary

| File                                  | Changes                                                             | Status      |
| ------------------------------------- | ------------------------------------------------------------------- | ----------- |
| `model/reactive.py`                   | NEW - TrackedParam, cached_constraint, cached_cost, ReactiveElement | ✅ Complete |
| `stubs/highspy/__init__.pyi`          | Add getExpr, changeCoeff, expression attributes                     | ✅ Complete |
| `tests/model/test_reactive.py`        | NEW - tests for reactive infrastructure                             | ✅ Complete |
| `model/element.py`                    | Update base class to use ReactiveElement mixin                      | 🔲 Pending  |
| `model/battery.py`                    | Convert to reactive params, @cached_constraint methods              | 🔲 Pending  |
| `model/power_connection.py`           | Convert to reactive params and constraints                          | 🔲 Pending  |
| `model/battery_balance_connection.py` | Convert to reactive params (if applicable)                          | 🔲 Pending  |
| `model/network.py`                    | Update optimize() to use apply_constraints() pattern                | 🔲 Pending  |
| `coordinator.py`                      | Wire input entity changes to model parameters                       | 🔲 Pending  |
| `tests/model/test_warm_start.py`      | Update tests for new architecture                                   | 🔲 Pending  |

## Open Questions

1. **Cost expressions**: Should we use `@cached_cost` or include costs in constraint apply?
2. **Structural changes**: How to detect and handle structural changes (new elements, removed connections)?
3. **Error handling**: What happens if constraint update fails mid-way?
4. **Thread safety**: Is `ContextVar` sufficient or need additional locking?

## Success Criteria

- [x] Core reactive infrastructure implemented and tested
- [ ] All existing tests pass after full refactor
- [ ] Warm start optimization works with parameter updates
- [x] No manual dependency declaration required (automatic tracking)
- [x] Coefficient updates are efficient (only changed values via changeCoeff)
- [x] Model layer remains HA-agnostic
- [x] Clean separation between expression computation and HiGHS application
