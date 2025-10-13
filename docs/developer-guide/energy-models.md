# Implementing Energy Models

Guide to creating new entity types in HAEO.

## Element Base Class

All entities inherit from `Element`:

```python
@dataclass
class Element:
    name: str
    period: float  # hours
    n_periods: int

    power_consumption: Sequence[LpVariable | float] | None = None
    power_production: Sequence[LpVariable | float] | None = None
    energy: Sequence[LpVariable | float] | None = None

    price_consumption: Sequence[float] | None = None
    price_production: Sequence[float] | None = None

    efficiency: float = 1.0
    forecast: Sequence[float] | None = None

    def constraints(self) -> Sequence[LpConstraint]:
        return []

    def cost(self) -> float:
        # Base implementation handles pricing
        pass
```

## Minimal Implementation

```python
from pulp import LpVariable
from .element import Element


class MyEntity(Element):
    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
        *,
        my_limit: float,
    ) -> None:
        # Create decision variables
        power_production = [LpVariable(f"{name}_power_{i}", lowBound=0, upBound=my_limit) for i in range(n_periods)]

        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_production=power_production,
        )
```

## Integration Checklist

1. **Model class**: Create in `custom_components/haeo/model/my_entity.py`
2. **Config schema**: Add in `types/entity_config.py`
3. **Network builder**: Update `_create_entity()` in `coordinator.py`
4. **Config flow**: Add step in `flows/options.py`
5. **Tests**: Add in `tests/test_model.py`
6. **Documentation**: Add modeling and user guide pages

## Best Practices

**Units**: Always kW (power), kWh (energy), hours (time)

**Variables**: Use `LpVariable` with bounds for optimizable values, constants for fixed

**Constraints**: Keep linear. Set bounds in variable creation when possible (more efficient)

**Names**: Include entity name and time index: `f"{name}_power_{t}"`

## Example Test

```python
def test_my_entity():
    entity = MyEntity(
        name="test",
        period=1.0,
        n_periods=24,
        my_limit=10.0,
    )

    assert len(entity.power_production) == 24
    assert entity.constraints() == []
```

## Common Patterns

**Fixed generation** (no curtailment):

```python
power_production = forecast  # List of floats
```

**Bounded generation** (with curtailment):

```python
power_production = [LpVariable(f"{name}_power_{i}", lowBound=0, upBound=forecast[i]) for i in range(n_periods)]
```

**Bidirectional power**:

```python
power_consumption = [LpVariable(f"{name}_consume_{i}", lowBound=0, upBound=max_c) ...]
power_production = [LpVariable(f"{name}_produce_{i}", lowBound=0, upBound=max_p) ...]
```

## Related Documentation

- [Architecture](architecture.md)
- [Battery Model](../modeling/battery.md)
- [Testing](testing.md)
