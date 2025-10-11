# Implementing Energy Models

Guide to creating new entity types in HAEO.

## Entity Base Class

All entities inherit from `Element`:

```python
from model.element import Element

class MyEntity(Element):
    def __init__(self, name: str, period: float, n_periods: int, ...):
        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_consumption=[...],  # LP variables
            power_production=[...],  # LP variables
            energy=[...],  # LP variables or constants
        )
```

## Required Implementation

See existing entities in `custom_components/haeo/model/` for examples.

## Adding to Network

Update `network.py` to support your new entity type.

## Testing

Create tests in `tests/test_model.py`:

```python
def test_my_entity():
    entity = MyEntity(name="test", period=1.0, n_periods=24)
    assert entity is not None
    # ... more tests
```
