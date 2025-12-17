---
applyTo: custom_components/haeo/model/**
---

# Model layer development

The model layer contains the linear programming formulation for energy optimization.

## Units (SI internally)

Use SI units throughout all model calculations:

- **Power**: Watts (W)
- **Energy**: Watt-hours (Wh)
- **Time**: seconds

Only convert to user-friendly units (kW, kWh, hours) at the boundary when:

- Displaying to users
- Accepting user input
- Interfacing with external APIs that use different units

See [units.md](../../docs/developer-guide/units.md) for conversion utilities.

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
