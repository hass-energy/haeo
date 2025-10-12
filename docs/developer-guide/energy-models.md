# Implementing Energy Models

This guide explains how to create new entity types in HAEO's optimization model.

## Overview

Adding a new entity type involves:

1. Creating the entity model class
2. Defining configuration schema
3. Updating network builder
4. Adding config flow steps
5. Writing comprehensive tests
6. Documenting the new entity

## Entity Base Class

All entities inherit from `Element` base class:

```python
from collections.abc import Sequence
from dataclasses import dataclass

from pulp import LpConstraint, LpVariable


@dataclass
class Element:
    """Base class for all energy entities."""

    name: str
    period: float  # Time step duration in hours
    n_periods: int  # Number of time steps

    # Power variables (kW) - sequences of LpVariable or float
    power_consumption: Sequence[LpVariable | float] | None = None
    power_production: Sequence[LpVariable | float] | None = None

    # Energy variables (kWh) - for storage entities
    energy: Sequence[LpVariable | float] | None = None

    # Pricing ($/kWh) - for cost calculation
    price_consumption: Sequence[float] | None = None
    price_production: Sequence[float] | None = None

    # Efficiency (0-1) - for losses
    efficiency: float = 1.0

    # Forecast data (kW) - for sensor exposure
    forecast: Sequence[float] | None = None

    def constraints(self) -> Sequence[LpConstraint]:
        """Return entity-specific constraints."""
        return []

    def cost(self) -> float:
        """Return cost contribution to objective function."""
        # Default implementation in base class
        pass
```

## Step-by-Step Implementation

### Step 1: Create Entity Class

Create file in `custom_components/haeo/model/my_entity.py`:

```python
"""My custom entity for electrical system modeling."""

from collections.abc import Sequence

import numpy as np
from pulp import LpConstraint, LpVariable

from .element import Element


class MyEntity(Element):
    """My custom entity for specific energy application."""

    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
        *,
        my_parameter1: float,
        my_parameter2: float | None = None,
        my_prices: Sequence[float] | float | None = None,
    ) -> None:
        """Initialize entity.

        Args:
            name: Name of the entity
            period: Time period in hours
            n_periods: Number of time periods
            my_parameter1: First parameter (required)
            my_parameter2: Second parameter (optional)
            my_prices: Price sequence or constant (optional)

        """
        # Store entity-specific parameters
        self.my_parameter1 = my_parameter1
        self.my_parameter2 = my_parameter2 or 0.0

        # Create decision variables
        power_production = [
            LpVariable(
                name=f"{name}_power_{i}",
                lowBound=0,  # Non-negative production
                upBound=my_parameter1,  # Limited by parameter
            )
            for i in range(n_periods)
        ]

        # Convert prices to array if needed
        ones = np.ones(n_periods)
        prices = (ones * my_prices).tolist() if my_prices is not None else None

        # Initialize base class
        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_production=power_production,
            price_production=prices,
        )

    def constraints(self) -> Sequence[LpConstraint]:
        """Return entity-specific constraints."""
        constraints = []

        # Example: Add ramping constraint
        if self.power_production:
            for t in range(self.n_periods - 1):
                ramp_limit = self.my_parameter2
                constraints.append(
                    self.power_production[t + 1] - self.power_production[t] <= ramp_limit
                )
                constraints.append(
                    self.power_production[t] - self.power_production[t + 1] <= ramp_limit
                )

        return constraints
```

**Key design decisions**:

- **Power direction**: Use `power_consumption` for loads, `power_production` for sources, both for bidirectional
- **Variables vs constants**: LpVariable for optimizable values, float for fixed values
- **Bounds**: Set via `lowBound`/`upBound` in LpVariable creation
- **Units**: Always kW for power, kWh for energy, hours for time

### Step 2: Define Configuration Schema

Create type definition in `types/entity_config.py`:

```python
from dataclasses import dataclass


@dataclass
class MyEntityConfig:
    """Configuration for MyEntity."""

    name: str
    my_parameter1: float
    my_parameter2: float | None = None
    my_price: float | None = None

    def validate(self) -> None:
        """Validate configuration."""
        if self.my_parameter1 <= 0:
            msg = "my_parameter1 must be positive"
            raise ValueError(msg)

        if self.my_parameter2 is not None and self.my_parameter2 < 0:
            msg = "my_parameter2 must be non-negative"
            raise ValueError(msg)

        if not self.name:
            msg = "name is required"
            raise ValueError(msg)
```

### Step 3: Update Network Builder

In `coordinator.py`, add factory method:

```python
def _create_entity(self, config: dict, data: dict) -> Element:
    """Create entity from configuration."""
    entity_type = config["type"]

    if entity_type == "my_entity":
        return MyEntity(
            name=config["name"],
            period=self.period,
            n_periods=self.n_periods,
            my_parameter1=config["my_parameter1"],
            my_parameter2=config.get("my_parameter2"),
            my_prices=data.get(f"{config['name']}_prices"),  # From sensor
        )
    # ... existing entity types
```

### Step 4: Add Config Flow Steps

In `flows/options.py`:

```python
# Add to ELEMENT_TYPES
ELEMENT_TYPES = [
    # ... existing types
    "my_entity",
]

# Create configuration method
async def async_step_configure_my_entity(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Configure MyEntity."""
    errors = {}

    if user_input is not None:
        try:
            # Validate input
            config = MyEntityConfig(**user_input)
            config.validate()

            # Save configuration
            return self.async_create_entry(
                title=user_input["name"],
                data=user_input,
            )
        except ValueError as err:
            errors["base"] = str(err)

    # Show form
    return self.async_show_form(
        step_id="configure_my_entity",
        data_schema=vol.Schema({
            vol.Required("name"): cv.string,
            vol.Required("my_parameter1"): vol.Coerce(float),
            vol.Optional("my_parameter2"): vol.Coerce(float),
            vol.Optional("my_price", default=0): vol.Coerce(float),
        }),
        errors=errors,
    )
```

### Step 5: Write Tests

In `tests/test_model.py`:

```python
def test_my_entity_creation():
    """Test creating MyEntity."""
    entity = MyEntity(
        name="test_entity",
        period=1.0,
        n_periods=24,
        my_parameter1=10.0,
        my_parameter2=2.0,
    )

    assert entity.name == "test_entity"
    assert entity.my_parameter1 == 10.0
    assert len(entity.power_production) == 24


def test_my_entity_constraints():
    """Test MyEntity constraints."""
    entity = MyEntity(
        name="test",
        period=1.0,
        n_periods=24,
        my_parameter1=10.0,
        my_parameter2=2.0,
    )

    constraints = entity.constraints()
    # Should have ramping constraints: 2 * (n_periods - 1)
    assert len(constraints) == 2 * (24 - 1)


def test_my_entity_in_network():
    """Test MyEntity in network optimization."""
    network = Network(name="test", period=1.0, n_periods=24)

    entity = MyEntity(
        name="my_entity",
        period=1.0,
        n_periods=24,
        my_parameter1=10.0,
    )

    network.elements["my_entity"] = entity

    # Add connections and other entities
    # ...

    # Should optimize successfully
    cost = network.optimize()
    assert cost >= 0
```

### Step 6: Document the Entity

Create user guide documentation (see Phase 2 examples) and modeling documentation (see Phase 1 examples).

## Best Practices

### Naming Conventions

**Variables**:

- Use descriptive names: `{name}_power_{t}`, `{name}_energy_{t}`
- Include entity name to avoid collisions
- Include time index `t`

**Parameters**:

- Use clear, descriptive names
- Match industry terminology where applicable
- Document units in docstrings

### Unit Consistency

**Always use**:

- Power: kW (kilowatts)
- Energy: kWh (kilowatt-hours)
- Time: hours
- Price: $/kWh

**Never use**:

- Watts, megawatts (use kW)
- Watt-hours (use kWh)
- Seconds, minutes (use hours)

### Variable Bounds

**Set bounds at creation**:

```python
# Good
power = LpVariable(name="power_0", lowBound=0, upBound=max_power)

# Avoid adding separate constraints
# (bounds are more efficient)
```

**Common patterns**:

- Non-negative: `lowBound=0`
- Limited: `upBound=max_value`
- Bidirectional: `lowBound=-max_reverse, upBound=max_forward`

### Constraint Types

**Equality** (`==`):

- Power balance: `inflow == outflow`
- Energy balance: `E(t+1) == E(t) + delta_E`

**Inequality** (`<=` or `>=`):

- Limits: `P(t) <= P_max`
- Minimum: `P(t) >= P_min`

**Bounds** (via variable creation):

- More efficient than separate constraints
- Use when possible

### Efficiency Modeling

For entities with losses:

```python
# Symmetric efficiency (like battery)
efficiency_factor = math.sqrt(efficiency)

# One-way efficiency
efficiency_factor = efficiency
```

Store as `self.efficiency` and use in constraints or cost calculation.

### Cost Calculation

Override `cost()` method only if custom logic needed:

```python
def cost(self) -> float:
    """Return custom cost calculation."""
    # Base class handles standard pricing
    base_cost = super().cost()

    # Add custom costs
    custom_cost = lpSum([
        some_calculation(t) for t in range(self.n_periods)
    ])

    return base_cost + custom_cost
```

Otherwise, use base class implementation with `price_consumption` and `price_production`.

## Common Patterns

### Pattern 1: Fixed Generation

No decision variables, just constant values:

```python
# Solar without curtailment
power_production = forecast  # List of floats, not variables
```

### Pattern 2: Bounded Generation

Variable with forecast as upper bound:

```python
# Solar with curtailment
power_production = [
    LpVariable(name=f"{name}_power_{i}", lowBound=0, upBound=forecast[i])
    for i in range(n_periods)
]
```

### Pattern 3: Bidirectional Power

Separate consumption and production variables:

```python
# Grid or battery
power_consumption = [LpVariable(name=f"{name}_consume_{i}", lowBound=0, upBound=max_consume) ...]
power_production = [LpVariable(name=f"{name}_produce_{i}", lowBound=0, upBound=max_produce) ...]
```

### Pattern 4: Energy Storage

Track energy level over time:

```python
# Battery
energy = [
    initial_energy,  # t=0 fixed
    *[
        LpVariable(
            name=f"{name}_energy_{i}",
            lowBound=min_energy,
            upBound=max_energy,
        )
        for i in range(n_periods - 1)
    ],
]
```

Then add energy balance constraints linking power and energy.

## Troubleshooting

### Infeasible Models

If your entity causes infeasible optimization:

1. Check constraint compatibility
2. Verify bounds are not too tight
3. Ensure power/energy relationships are correct
4. Test entity in isolation

### Poor Performance

If optimization is slow with your entity:

1. Minimize number of variables
2. Use bounds instead of separate constraints
3. Avoid redundant constraints
4. Check for numerical issues (large numbers)

### Incorrect Results

If optimization succeeds but results are wrong:

1. Verify variable signs (consumption vs production)
2. Check unit consistency
3. Validate constraint formulations
4. Test with simple known scenarios

## Related Documentation

- [Architecture](architecture.md) - How entities fit into system
- [Battery Model](../modeling/battery.md) - Complete example entity
- [Testing Guide](testing.md) - How to test entities
- [Units](units.md) - Unit conventions

## Next Steps

- Review existing entity implementations in `model/`
- Study [battery.py](../modeling/battery.md) as reference implementation
- Write comprehensive tests for new entities
- Document thoroughly (modeling + user guide)

[:octicons-arrow-right-24: Continue to Testing Guide](testing.md)
