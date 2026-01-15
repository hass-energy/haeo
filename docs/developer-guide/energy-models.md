# Implementing Energy Models

Guide for adding new element types to HAEO's optimization engine.

## Architecture Overview

HAEO uses a [layered architecture](architecture.md#layered-architecture):

- **Model Layer**: Mathematical building blocks that form the LP problem
- **Device Layer**: User-configured elements that compose Model Layer elements via the [Adapter Layer](adapter-layer.md)

When adding a new element type, decide which layer it belongs to:

- **Model Layer**: New mathematical formulation not representable by existing models
- **Device Layer**: New user-facing element that composes existing Model Layer elements

Most new elements will be Device Layer elements that compose `node` and `connection` models with different parameter mappings.

## Workflow overview

### Adding a Device Layer element

1. Design how existing Model Layer elements combine to achieve the desired behavior
2. Define the configuration schema in `custom_components/haeo/elements/`
3. Implement `create_model_elements()` to transform config into Model Layer specifications
4. Implement `outputs()` to map Model Layer results to user-friendly device outputs
5. Register in `ELEMENT_TYPES` and add translations
6. Write tests covering configuration and output mapping

### Adding a Model Layer element

1. Design the mathematical behavior: variables, constraints, cost contributions
2. Implement the model class in `custom_components/haeo/model/elements/` deriving from `Element`
3. Use `TrackedParam` for parameters that can change between optimizations
4. Use `@constraint` decorator for constraint methods
5. Use `@cost` decorator for cost contribution methods
6. Use `@output` decorator for output extraction methods
7. Register in the `ELEMENTS` registry in `model/elements/__init__.py`
8. Update Device Layer elements to use the new model
9. Write model tests and integration tests

## Implementing Model Elements

### Element structure

Model elements derive from the `Element` base class and use decorators to declare their constraints, costs, and outputs.

### TrackedParam for parameters

Parameters that can change between optimizations (forecasts, capacities, prices) should use `TrackedParam`:

```python
from custom_components.haeo.model.reactive import TrackedParam


class Battery(Element[BatteryOutputName]):
    # Declare parameters as TrackedParam descriptors
    capacity: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_charge: TrackedParam[float] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        capacity: Sequence[float] | float,
        initial_charge: float,
    ):
        super().__init__(name=name, periods=periods, solver=solver, output_names=BATTERY_OUTPUT_NAMES)

        # Set parameter values
        self.capacity = broadcast_to_sequence(capacity, self.n_periods + 1)
        self.initial_charge = initial_charge
```

When a `TrackedParam` value changes, the system automatically invalidates dependent constraints for rebuilding.

### @constraint decorator

Use `@constraint` to declare constraint methods.
The decorator caches expressions and manages the solver lifecycle:

```python
from custom_components.haeo.model.reactive import constraint


@constraint(output=True, unit="$/kWh")
def battery_soc_max(self) -> list[highs_linear_expression]:
    """Constraint: stored energy cannot exceed capacity.

    Output: shadow price indicating the marginal value of additional capacity.
    """
    return list(self.stored_energy[1:] <= self.capacity[1:])
```

Parameters:

- `output=True`: Expose constraint shadow prices as outputs (default `False`)
- `unit`: Unit for shadow price outputs (default `"$/kW"`)

### @cost decorator

Use `@cost` to declare cost contribution methods:

```python
from custom_components.haeo.model.reactive import cost


@cost
def cost_source_target(self) -> highs_linear_expression | None:
    """Cost for power flow from source to target."""
    if self.price_source_target is None:
        return None
    return Highs.qsum(self.power_source_target * self.price_source_target * self.periods)
```

The network automatically sums all `@cost` methods across all elements.

### @output decorator

Use `@output` to declare output extraction methods:

```python
from custom_components.haeo.model.reactive import output
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.const import OutputType


@output
def battery_power_charge(self) -> OutputData:
    """Output: power being consumed to charge the battery."""
    return OutputData(
        type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
    )
```

The network discovers outputs via reflection on `@output` and `@constraint(output=True)` decorated methods.

## Modeling guidelines

### Stay linear

The solver uses pure linear programming, so every constraint and cost must be linear in the decision variables.
Approximate nonlinear behaviour with piecewise constants or external preprocessing when necessary.
The default solvers also support mixed-integer linear programming, but treat binary or integer variables as a last resort because they increase solve time dramatically.
Before you add discrete decisions, look for linear encodings such as mutually dependent constraints, large penalty weights, or auxiliary slack variables that approximate the choice without integer branching.
If MILP is truly required, keep the integer variable count minimal and document the trade-offs so reviewers understand the performance impact.

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

**Expected outputs by element type:**

- **Battery models**: `power_charge`, `power_discharge`, `energy_stored`
- **Connection models**: `power_source_target`, `power_target_source`, costs, shadow prices
- **Node models**: `power_in`, `power_out` (if applicable)

Keeping the output contract consistent means new model components immediately surface in Home Assistant without changes to the sensor platform.
See existing implementations in `custom_components/haeo/model/elements/` for examples:

- `battery.py` - Energy storage with SOC tracking
- `connection.py` - Composable connection segments for flow and pricing
- `node.py` - Power balance points

## Connections and nodes

Connections remain responsible for enforcing flow limits and tying elements together through node balance constraints.
When introducing a new element, ensure it connects through existing nodes or provide a clear reason to add a specialised node variant.

The current implementations are in `custom_components/haeo/model/elements/connection.py` and `custom_components/haeo/model/elements/node.py`.

## Cost modelling

Only add costs that reflect real trade-offs.
If the element interacts with external tariffs or degradation models, expose the relevant coefficients through configuration and ensure the objective contribution uses each period's duration for scaling (available via `self.periods[t]`).

## Related Documentation

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
