# Model Layer Simplification Plan

This plan outlines refactoring the model layer to simplify the architecture, fix constraint application, and enable incremental parameter updates.

## Goals

1. **Single Element base class** - Merge ReactiveElement into Element, eliminating the separate inheritance layer
2. **Decorator-based declarations** - Use `@constraint`, `@cost`, and `@output` decorators for all declarative element behavior
3. **Fix constraint application** - Elements return constraint expressions; infrastructure calls `addConstrs()`
4. **Dict-style parameter access** - `element["param_name"] = value` for setting TrackedParams
5. **Empty element construction** - Elements created with just structural params, values set later
6. **Incremental coordinator updates** - First update does full load, subsequent updates are incremental
7. **Directory reorganization** - Cleaner structure with `model/elements/` subdirectory

## Current Architecture Problems

### Constraint Application Bug

Currently `@constraint` methods call `h.addConstrs()` directly:

```python
@constraint
def soc_upper_constraint(self) -> list[highs_cons]:
    h = self._solver
    return h.addConstrs(self.soc[t] <= self.capacity[t] for t in range(self.n_periods + 1))
```

This is wrong because:
- The constraint is added to the solver immediately
- When the constraint invalidates and rebuilds, we can't delete the old one properly
- `apply_constraints()` stores the returned `highs_cons` but the constraint is already added

The fix: `@constraint` methods return expressions, `apply_constraints()` calls `addConstrs()`.

### Dual Inheritance Complexity

```
ReactiveElement (reactive.py) - caching, TrackedParam, @constraint/@cost
    └── Element (element.py) - name, periods, solver, connections, outputs
```

Since all elements are now reactive, this separation adds complexity without benefit.

### load_network Complexity

The coordinator calls `load_network()` which:
1. Iterates all participants
2. Calls adapter `create_model_elements()` for each
3. Passes `existing_network` for warm start

This is complex because:
- Network building and parameter loading are intertwined
- Adapters return full element configs each time
- Hard to do incremental updates

## New Architecture

### Single Element Base Class

Merge ReactiveElement into Element:

```python
class Element(Generic[OutputNameT]):
    """Base class for all model elements with reactive parameter tracking."""
    
    # From ReactiveElement
    _cache: dict[CachedKind, dict[str, Any]]
    _deps: dict[CachedKind, dict[str, set[str]]]
    _invalidated: dict[CachedKind, set[str]]
    _applied_constraints: dict[str, highs_cons | list[highs_cons]]
    _applied_costs: dict[str, highs_linear_expression | list[highs_linear_expression] | None]
    
    # Element-specific
    name: str
    periods: NDArray[np.float64]
    _solver: Highs
    _connections: list[tuple[Connection, Literal["source", "target"]]]
    
    def __getitem__(self, key: str) -> Any: ...
    def __setitem__(self, key: str, value: Any) -> None: ...
```

### Decorator Pattern

Three decorators for element behavior:

```python
@constraint  # Returns highs_linear_expression, apply_constraints() calls addConstrs()
def soc_upper_constraint(self) -> highs_linear_expression | list[highs_linear_expression]:
    return (self.soc[t] <= self.capacity[t] for t in range(self.n_periods + 1))

@cost  # Returns cost expression for objective
def import_cost(self) -> highs_linear_expression:
    return Highs.qsum(self.power[t] * self.price[t] * self.periods[t] for t in range(self.n_periods))

@output  # Returns OutputData, discovered by reflection
def power_consumed(self) -> OutputData:
    return OutputData(type=OutputType.POWER, unit="kW", values=tuple(self.power.value()))
```

### Dict-Style Parameter Access

Elements support `__getitem__` and `__setitem__`:

```python
# Get parameter value
current_capacity = element["capacity"]

# Set parameter (triggers invalidation)
element["capacity"] = np.array([10.0, 10.0, 10.0, 10.0])

# Coordinator can iterate adapter output
for param_name, value in loaded_data.items():
    element[param_name] = value
```

Implementation uses `getattr`/`setattr` on TrackedParam descriptors.

### Empty Element Construction

Elements created with only structural parameters:

```python
# Battery needs: name, periods, solver
battery = Battery(name="battery", periods=periods, solver=solver)

# Values set later via dict access
battery["capacity"] = np.array([10.0, 10.0, 10.0, 10.0])
battery["initial_charge"] = 5.0
battery["max_charge_power"] = np.array([5.0, 5.0, 5.0])
```

TrackedParams have `_UNSET` sentinel as default - constraints that depend on unset params are skipped or return None.

### Coordinator Flow

**First `_async_update_data`:**
1. Create Network with horizon periods
2. Create elements from config subentries via `network.add()`
3. Full load: iterate all input entities, load values, set on elements
4. Run optimization

**Subsequent `_handle_input_state_change`:**
1. Identify which element changed (by entity → element name mapping)
2. Load new values from input entity
3. Set on element via dict access (TrackedParam invalidates dependents)
4. Trigger optimization (debounced)

### Directory Structure

```
model/
├── __init__.py          # Re-exports public API
├── element.py           # Element base class (merged with reactive)
├── network.py           # Network orchestration
├── const.py             # OutputType enum
├── output_data.py       # OutputData dataclass
├── elements/
│   ├── __init__.py      # Re-exports element classes
│   ├── battery.py
│   ├── node.py
│   ├── connection.py
│   ├── power_connection.py
│   └── battery_balance_connection.py
└── util/
    ├── __init__.py
    ├── broadcast_to_sequence.py
    └── percentage_to_ratio.py
```

## Implementation Steps

### Phase 1: Fix Constraint Application

1. Update `apply_constraints()` to call `h.addConstrs()` on returned expressions
2. Change all `@constraint` methods to return expressions instead of calling `addConstrs()`
3. Handle both single expression and generator/list returns
4. Run tests to verify constraints still work

### Phase 2: Add @output Decorator

1. Create `output` decorator in element.py (after merge)
2. Add `CachedKind.OUTPUT` if needed for discovery
3. Convert `outputs()` methods to individual `@output` methods
4. Update `outputs()` to discover and call all `@output` methods
5. Run tests to verify outputs work

### Phase 3: Merge ReactiveElement into Element

1. Move all ReactiveElement code into Element
2. Update Element to not inherit from ReactiveElement
3. Delete ReactiveElement class (keep TrackedParam and decorators)
4. Update all element imports
5. Run tests

### Phase 4: Add Dict-Style Parameter Access

1. Implement `__getitem__` on Element
2. Implement `__setitem__` on Element
3. Handle TrackedParam lookup by name
4. Add tests for dict access

### Phase 5: Enable Empty Element Construction

1. Make TrackedParams optional with `_UNSET` default
2. Update element constructors to only require structural params
3. Update `@constraint` methods to handle unset params (skip or return None)
4. Update Network.add() to create empty elements
5. Update Network.add() to return created elements
6. Run tests

### Phase 6: Simplify Coordinator

1. Remove `load_network()` from data/__init__.py
2. Add network creation on first `_async_update_data`
3. Add full load logic after network creation
4. Update `_handle_input_state_change` to do incremental updates
5. Update adapter interface if needed
6. Run integration tests

### Phase 7: Reorganize Directory Structure

1. Create model/elements/ directory
2. Move element files to model/elements/
3. Update all imports
4. Update model/__init__.py exports
5. Update external imports (adapters, coordinator, tests)
6. Run all tests

## Testing Strategy

Each phase should leave tests passing:

- **Phase 1-2**: Model tests (`tests/model/`) verify constraint/output behavior
- **Phase 3-5**: Model tests verify Element functionality
- **Phase 6**: Integration tests verify coordinator flow
- **Phase 7**: All tests verify imports work

Use `uv run pytest tests/model/ -v` for quick feedback during model changes.

## Risk Mitigation

1. **Constraint bugs**: Phase 1 is highest risk. Run full test suite after each constraint method change.

2. **Import breakage**: Phase 7 will break imports. Let Python errors guide fixes.

3. **Coordinator complexity**: Phase 6 touches core integration. Test with scenario tests.

4. **TrackedParam edge cases**: Empty elements with unset params need careful handling. Add explicit tests for this.

## Success Criteria

- [ ] All 1000+ tests pass
- [ ] Pyright reports 0 errors
- [ ] Ruff reports no issues
- [ ] Constraint rebuild works correctly (warm start tests pass)
- [ ] Incremental updates work (state change triggers optimization)
- [ ] Directory structure is cleaner
- [ ] Code is simpler to understand
