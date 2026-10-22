# Implementing energy models

Guide for adding new element types to HAEO's optimization engine.

## Architecture overview

HAEO uses a [layered architecture](architecture.md#layered-architecture):

- **Model layer**: Mathematical building blocks that form the LP problem
- **Device layer**: User-configured elements that compose model layer elements via the [adapter layer](adapter-layer.md)

When adding a new element type, decide which layer it belongs to:

- **Model layer**: New mathematical formulation not representable by existing models
- **Device layer**: New user-facing element that composes existing model layer elements

Most new elements are device layer elements that compose existing model elements with different parameter mappings.

## Workflow overview

### Adding a device layer element

1. Design how existing model layer elements combine to achieve the desired behavior
2. Define the configuration schema in `core/schema/elements/`
3. Implement the adapter's `model_elements()` to transform config into model layer element configs
4. Implement `outputs()` to map model layer results to user-friendly device outputs
5. Register the adapter in `ELEMENT_TYPES`, add the flow, and add translations
6. Write tests covering configuration and output mapping

[Adding element types](architecture.md#adding-element-types) lists every registry the type joins.

### Adding a model layer element

1. Design the mathematical behavior: variables, constraints, cost contributions
2. Implement the model class in `custom_components/haeo/core/model/elements/` deriving from `Element`, or from `NetworkElement` if it takes part in power balance
3. Use `TrackedParam` for parameters that can change between optimizations
4. Use `@constraint` decorator for constraint methods
5. Use `@cost` decorator for cost contribution methods
6. Use `@output` decorator for output extraction methods
7. Register an `ElementSpec` in the `ELEMENTS` registry in `core/model/elements/__init__.py`, with its output names and `add_order`
8. If the element reads other elements' flows, give its spec a later `add_order` than those elements and an `arguments` hook that resolves the elements it names
9. Update device layer elements to use the new model
10. Write model tests and integration tests

## Implementing model elements

### Element structure

Model elements derive from the `Element` base class and use decorators to declare their constraints, costs, and outputs.
`Element` and connection segments share the `ModelComponent` base in `core/model/component.py`, which discovers those decorated methods by reflection.

### Linear expressions

Variables and expressions are `LinearArray` values from `core/model/linear.py`, with one linear expression per period.
Each array stores its terms as a column index matrix and a coefficient matrix, so arithmetic on a whole horizon is a few numpy operations rather than one Python object per period.
Create variables with `solver.add_variables(count, name=...)` and combine them with `+`, `-`, and multiplication by a scalar or one value per row.
Comparing an array with `<=`, `>=`, or `==` produces `Rows`, which a `@constraint` method returns.
`total()` sums every row into a single row, which is the form a `@cost` method returns.
When each row reaches several rows of another array with varying coefficients, build the coefficient matrix with numpy and write `matrix @ array`.
`solver.describe(rows)` shows each row as an expression over named columns, such as `Battery.energy_in[3] - Battery.energy_in[4] <= 0`.

### TrackedParam for parameters

Parameters that can change between optimizations (forecasts, capacities, prices) should use `TrackedParam`:

```python
from custom_components.haeo.core.model.reactive import TrackedParam


class Battery(Element[BatteryOutputName]):
    # Declare parameters as TrackedParam descriptors
    capacity: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_charge: TrackedParam[float] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Solver,
        capacity: NDArray[np.floating[Any]],
        initial_charge: float,
    ):
        super().__init__(name=name, periods=periods, solver=solver, output_names=BATTERY_OUTPUT_NAMES)

        # Set parameter values
        self.capacity = broadcast_to_sequence(capacity, self.n_periods + 1)
        self.initial_charge = initial_charge
```

When a `TrackedParam` value changes, the system automatically invalidates dependent constraints for rebuilding.
Dependencies are recorded per object, so a constraint that reads another element's parameter is invalidated too.
Use `@computed` for a cached value computed from parameters that constraints and costs build on, such as a segment's transformed flow.
Anything that reads a `@computed` method depends on it and is rebuilt when it changes.

A constraint returns the same rows on every call so the LP keeps its shape and later optimizations still warm start.
When part of a constraint does not currently apply, such as a power limit with no maximum set,
return those rows from the expression's `free()` method.
They are added as free rows that do not bind, and become binding later by changing only their bounds.
A constraint whose rows are all free has no shadow price and is not listed by `constraints()`.
A constraint with no rows at all returns `Rows.concat([])`; returning anything other than `Rows` is an error.

### @constraint decorator

Use `@constraint` to declare constraint methods.
The decorator caches expressions and manages the solver lifecycle:

```python
from custom_components.haeo.core.model.reactive import constraint


@constraint(output=True, unit="$/kWh")
def battery_soc_max(self) -> Rows:
    """Constraint: stored energy cannot exceed capacity.

    Output: shadow price indicating the marginal value of additional capacity.
    """
    return self.stored_energy[1:] <= self.capacity[1:]
```

Parameters:

- `output=True`: Expose constraint shadow prices as outputs (default `False`)
- `unit`: Unit for shadow price outputs (default `"$/kWh"`)

### @cost decorator

Use `@cost` to declare cost contribution methods.
Each `@cost` method returns a single expression for the primary objective:

```python
from custom_components.haeo.core.model.reactive import cost


@cost
def cost_source_target(self) -> LinearArray | None:
    """Cost for power flow from source to target."""
    if self.price_source_target is None:
        return None
    return (self.power_source_target * self.price_source_target * self.periods).total()
```

The element's `cost()` aggregator collects all `@cost` methods and sums them into a single primary expression.
A constant term in a cost, one that reads no variable, is allowed and goes to the objective's offset.
The time-preference objective comes from `secondary_cost()`, which only `Connection` overrides.
The network sums the primary and secondary contributions separately across all elements and solves them as one blended objective, as [Solution process](../modeling/index.md#solution-process) describes.

### @output decorator

Use `@output` to declare output extraction methods:

```python
from custom_components.haeo.core.model.reactive import output
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.const import OutputType


@output
def battery_power_charge(self) -> OutputData:
    """Output: power being consumed to charge the battery."""
    return OutputData(
        type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
    )
```

The network discovers outputs via reflection on `@output` and `@constraint(output=True)` decorated methods.
Use `@output(name="...")` to expose a custom output name when the method name is not the desired output key.

## Modeling guidelines

### Stay linear

The solver uses pure linear programming, so every constraint and cost must be linear in the decision variables.
Approximate nonlinear behaviour with piecewise constants or external preprocessing when necessary.
HiGHS also supports mixed-integer linear programming, but HAEO treats **MILP as a tool of last resort**: prefer pure LP for performance, and add integers only when no linear formulation can achieve the same outcome.
Before introducing discrete variables, try linear encodings—mutually dependent constraints, large penalty weights, or auxiliary slack variables that approximate the behaviour without branching.
If MILP is unavoidable, keep the integer count as small as possible and document why LP was insufficient so reviewers understand the performance trade-off.

### Keep units consistent

All internal calculations use kW for power, kWh for energy, and hours for time steps.
Use the shared unit conversion helpers if you introduce new inputs to keep numerical magnitudes aligned.

### Use variable bounds wisely

When defining new decision variables, apply sensible lower and upper bounds at creation time.
This reduces the number of explicit constraints you need and improves solver performance.

### Expose element outputs

Each element uses the `@output` decorator to mark methods that extract optimization results.
The network discovers these methods via reflection and calls them to populate sensor data.

Return `OutputData` objects with:

- `type`: Output type (POWER, ENERGY, STATE_OF_CHARGE, COST, PRICE, SHADOW_PRICE, etc.)
- `unit`: Unit string (kW, kWh, $, $/kWh, etc.)
- `values`: Tuple of floats for the time series
- `direction`: Optional "+" (production) or "-" (consumption)

Extract solution values from HiGHS variables using `self.extract_values()`.

Each element's output names are declared beside its class in its `ElementSpec`, and the adapters map them to device outputs.
Keeping the output contract consistent means new model components surface in Home Assistant without changes to the sensor platform.
See the existing implementations in [`core/model/elements/`](https://github.com/hass-energy/haeo/tree/main/custom_components/haeo/core/model/elements) for examples.

## Element power protocol

Every model element can declare its external power via two methods:

- `element_power_produced()`: Power injected into the network (≥ 0). Default returns 0.
- `element_power_consumed()`: Power absorbed from the network (≥ 0). Default returns 0.

The Element base class uses these to build per-tag power balance constraints with [tagged power](../modeling/tagged-power.md) routing.
Elements accept `outbound_tags` and `inbound_tags` parameters that control how production and consumption map to tags.

Elements that produce and consume power (e.g., Battery) override both methods.
Source-only elements (e.g., solar Node) override `element_power_produced()`.
Sink-only elements (e.g., load Node) override `element_power_consumed()`.
Elements that neither produce nor consume return 0 for both (the default).

See the [tagged power formulation](../modeling/tagged-power.md) for the mathematical details.

## Connections and segments

Connections create the **only LP variables** for power flow (one per time step).
Each connection is unidirectional (source → target). Bidirectional paths use two connections.
Segments are functional transforms that read a `power_in` flow from their upstream, the segment before them,
and expose a `power_out` flow. Most segments are identity transforms that add
constraints or costs as side effects. Subclasses that transform the flow
override the output expression, computing it in a `@computed` method so that
downstream constraints are rebuilt when the transforming parameter changes.

When adding a new segment type, implement `__init__` accepting its `upstream`
and pass it to `Segment`. Read `self.power_in` inside constraint and cost methods rather
than storing the flow, so the dependency on upstream parameters is recorded. Avoid creating
power flow LP variables — the Connection owns those. Auxiliary variables
(e.g., slack variables for penalty terms) are acceptable.

When introducing a new element, ensure it connects through existing nodes or provide a clear reason to add a specialised node variant.

The current implementations are in `custom_components/haeo/core/model/elements/connection.py` and `custom_components/haeo/core/model/elements/node.py`.

## Cost modeling

Only add costs that reflect real trade-offs.
If the element interacts with external tariffs or degradation models, expose the relevant coefficients through configuration and ensure the objective contribution uses each period's duration for scaling (available via `self.periods[t]`).

The objective has two parts.
The primary objective, the sum of every `@cost` method, captures real monetary costs.
The secondary objective, the sum of every `secondary_cost()`, breaks ties between equally cheap plans.
Add new cost terms as `@cost` methods; only tie-breaking belongs in `secondary_cost()`.

## Related documentation

<div class="grid cards" markdown>

- :material-sitemap:{ .lg .middle } **Architecture**

    ---

    High-level system structure.

    [:material-arrow-right: Architecture guide](architecture.md)

- :material-database:{ .lg .middle } **Data Loading**

    ---

    Forecast and sensor ingestion.

    [:material-arrow-right: Data loading guide](data-loading.md)

- :material-battery-charging:{ .lg .middle } **Battery Model**

    ---

    Example of a storage formulation.

    [:material-arrow-right: Battery modeling](../modeling/model-layer/elements/battery.md)

- :material-test-tube:{ .lg .middle } **Testing**

    ---

    Expectations for unit and integration tests.

    [:material-arrow-right: Testing guide](testing.md)

</div>
