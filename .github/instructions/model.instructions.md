---
applyTo: custom_components/haeo/model/**
description: Model layer LP formulation standards
globs: [custom_components/haeo/model/**]
alwaysApply: false
---

# Model layer development

The model layer contains the linear programming formulation for energy optimization.

## Units

Use SI-derived units scaled for numerical stability throughout all model calculations:

- **Power**: kilowatts (kW)
- **Energy**: kilowatt-hours (kWh)
- **Time**: hours (model layer uses hours; rest of codebase uses seconds)

This scaling keeps values in the ideal range for LP solvers (0.01 to 1000).
The adapter layer handles conversion between model time (hours) and Home Assistant time (seconds).
See [units.md](../../docs/developer-guide/units.md) for rationale and conversion utilities.

When model updates or documentation changes are made, ensure the corresponding documentation in `docs/modeling/` is updated.

## Model patterns

- Inherit from base `Element` class
- Implement decision variables for power and energy
- Use `Network.add()` to add elements
- Linear programming constraints only - keep models simple for solver efficiency

## Constraints

- Express all constraints as linear inequalities or equalities
- Document physical meaning of each constraint
- Use descriptive variable names that reflect physical quantities

## Cost functions

- Costs must be linear in decision variables
- Document the economic interpretation
- Use consistent sign conventions (positive = cost, negative = revenue)

## Optimization

- Catch optimization failures gracefully
- Return appropriate status indicators
- Log solver diagnostics at debug level

## Testing

- Test each element type independently
- Verify constraints are satisfied in solutions
- Test edge cases (zero power, full/empty battery, etc.)
