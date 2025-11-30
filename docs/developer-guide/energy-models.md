# Implementing Energy Models

Guide for adding new element types to HAEO's optimization engine.

## Workflow overview

1. Design the mathematical behaviour for your element: required variables, constraints, and cost contributions.
2. Implement the model class in `custom_components/haeo/model/` by deriving from the shared `Element` base.
3. Define the configuration schema and defaults in `custom_components/haeo/elements/` so the UI can collect the necessary inputs.
4. Register the element with the network builder so the coordinator can instantiate it from configuration.
5. Extend the element config flow and add tests that cover both the mathematical formulation and the user-facing configuration.

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

Each element must implement `outputs()` so the Home Assistant integration can discover the sensor data automatically.
Return a tuple of `ElementOutput` dataclasses where `values` is the full time series as floats.
Use `pulp.value()` to convert decision variables into numeric values and provide copies of any underlying lists so callers cannot mutate internal state.

The base `Element` implementation already reports net power in kilowatts.
Override the method when you need to expose extra information such as stored energy, state of charge, or forecast capacity.

**Expected outputs by element type:**

- **Battery models**: `power`, `energy`, and `soc`
- **Photovoltaic models**: `power` and `available_power` (based on forecast limits)
- **Load models**: `power` only
- **Grid models**: `power` and `cost`

Keeping the output contract consistent means new model components immediately surface in Home Assistant without changes to the sensor platform.
See existing implementations in `custom_components/haeo/model/` for examples:

- `battery.py` - Energy storage with SOC tracking
- `photovoltaics.py` - Solar generation with forecast limits
- `grid.py` - Grid import/export with pricing
- `constant_load.py` - Fixed power consumption
- `forecast_load.py` - Time-varying consumption

## Connections and nodes

Connections remain responsible for enforcing flow limits and tying elements together through node balance constraints.
When introducing a new element, ensure it connects through existing nodes or provide a clear reason to add a specialised node variant.

The current implementations are in `custom_components/haeo/model/connection.py` and `custom_components/haeo/model/node.py`.

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

    [:material-arrow-right: Battery modeling](../modeling/battery.md)

- :material-test-tube:{ .lg .middle } **Testing**

    ---

    Expectations for unit and integration tests.

    [:material-arrow-right: Testing guide](testing.md)

</div>
