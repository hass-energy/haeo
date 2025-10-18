# Implementing Energy Models

Guide for adding new element types to HAEO's optimization engine.

## Integration Points

HAEO uses linear programming (PuLP) to optimize energy networks.
Elements contribute decision variables, constraints, and costs to the optimization problem.

**Model Classes**: `custom_components/haeo/model/*.py` - Create your element class inheriting from `Element`

**Configuration Schema**: `custom_components/haeo/elements/<element>.py` - Define `TypedDict` schemas and defaults for your element

**Network Builder**: `coordinator.py` `_create_entity()` - Add case to instantiate your element from config

**Config Flow**: `flows/options.py` - Add step functions for UI configuration

**Tests**: `tests/test_model.py` and `tests/scenarios/` - Verify element behavior

## Element Base Class

Inherit from `Element` which provides:

- `power_consumption` / `power_production` sequences - Use `LpVariable` for controllable power, floats for fixed
- `energy` sequence - Optional state tracking (batteries need this)
- `price_consumption` / `price_production` - Optional pricing data for cost optimization
- `period` (hours) and `n_periods` - Time structure for optimization horizon
- `constraints()` method - Override to add linear constraints
- `cost()` method - Override to add costs beyond basic pricing

Variable naming: Include element name and time index (`f"{name}_power_{t}"`) for uniqueness.

## HAEO Constraints

### Units

All optimization uses kW (power), kWh (energy), hours (time).
Data loading in `coordinator.py` converts Home Assistant's W/Wh automatically.

### Linear Programming Only

PuLP requires linear constraints.
No variable multiplication or exponents.
Use constant efficiency instead of curves, linearize nonlinear physics.

### Variable Bounds vs Constraints

Set bounds during `LpVariable()` creation when possible - more efficient than separate constraints.

## Connections

Connections enforce Kirchhoff's Current Law between elements.
Created in `coordinator.py`, not as separate model classes.
Node elements enforce the constraints.

Properties: source, target, power flow variables, optional capacity limit, optional efficiency (transmission losses).

## Common Patterns

### Constraints

Override `constraints()` to return list of linear constraints:

- **State bounds**: Energy storage limits (battery SOC 0-100%)
- **Ramp rates**: Limit power change between consecutive periods
- **Mutual exclusivity**: Binary variables for mode selection (expensive, avoid if possible)
- **Minimum runtime**: Binary variables ensuring minimum on/off duration (expensive)

### Costs

Override `cost()` to add to optimization objective:

- **Energy pricing**: `sum(power[t] * price[t] * period)` for each time period
- **Degradation**: Add throughput costs (battery cycles)
- **Demand charges**: Add peak demand variable + constraints
- **Opportunity costs**: Lost revenue from curtailment/flexibility

## Related Documentation

- [Architecture](architecture.md) - System overview
- [Data Loading](data-loading.md) - How forecast data flows into models
- [Coordinator](coordinator.md) - Network building and optimization
- [Battery Model](../modeling/battery.md) - Complete battery implementation
- [Grid Model](../modeling/grid.md) - Import/export with pricing
- [Load Model](../modeling/loads.md) - Fixed and flexible loads
- [Node Model](../modeling/node.md) - Kirchhoff's law enforcement
- [Testing](testing.md) - Model testing patterns
