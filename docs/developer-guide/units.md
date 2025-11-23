# Units and Numerical Stability

HAEO uses specific unit conventions for numerical stability and solver performance.

## Unit System

HAEO uses SI-derived units scaled for energy systems:

| Quantity | Unit                     | Rationale                          |
| -------- | ------------------------ | ---------------------------------- |
| Power    | kilowatts (kW)           | Typical household range: 0.1-20 kW |
| Energy   | kilowatt-hours (kWh)     | Battery capacities: 5-100 kWh      |
| Time     | hours (h)                | Natural for energy calculations    |
| Price    | dollars per kWh (\$/kWh) | Standard electricity pricing       |

## Why Not Watts and Watt-hours?

Using watts would create numerical issues:

❌ **Bad: Using Watts**

```python
capacity = 13500  # Wh
power = 5000  # W
time = 0.0833  # hours (5 minutes)
```

✅ **Good: Using Kilowatts**

```python
capacity = 13.5  # kWh
power = 5  # kW
time = 0.0833  # hours
```

## Numerical Stability

Linear programming solvers work best when:

1. **Variables have similar magnitudes** (0.01 to 1000)
2. **Avoiding very large numbers** (> 10⁶)
3. **Avoiding very small numbers** (< 10⁻⁶)

Our unit choice keeps values in the ideal range:

- Battery energy: 5-100 kWh
- Power flows: 0.1-20 kW
- Time steps: 0.0833-1 hours
- Prices: 0.05-0.50 \$/kWh

## Energy Calculations

With our units, energy calculations are natural:

```python
# Energy = Power × Time
energy_kwh = power_kw * time_hours

# Example: 5 kW for 0.5 hours = 2.5 kWh
energy = 5.0 * 0.5  # = 2.5 kWh
```

No conversion factors needed!

## Cost Calculations

```python
# Cost = Energy × Price
cost = energy_kwh * price_per_kwh

# Example: 10 kWh at $0.25/kWh = $2.50
cost = 10.0 * 0.25  # = $2.50
```

Again, no conversions!

## Converting External Data

When loading data from Home Assistant sensors:

```python
from homeassistant.const import UnitOfPower, UnitOfEnergy


def convert_to_kw(value: float, unit: str) -> float:
    """Convert power to kW."""
    if unit == UnitOfPower.WATT:
        return value / 1000.0
    elif unit == UnitOfPower.KILOWATT:
        return value
    else:
        raise ValueError(f"Unsupported unit: {unit}")
```

See `const.py` for actual implementation.

## Implementation Guidelines

When adding new features:

1. **Store in kW/kWh/hours**: Always use standard units internally
2. **Convert at boundaries**: Convert only when interfacing with HA
3. **Document units**: Comment units for all variables
4. **Validate ranges**: Check values are in expected ranges

Example:

```python
def add_battery(
    self,
    capacity: float,  # kWh
    max_power: float,  # kW
    period: float,  # hours
) -> None:
    """Add battery to network.

    Args:
        capacity: Battery capacity in kWh (typical: 5-100)
        max_power: Maximum power in kW (typical: 3-10)
        period: Time step in hours (typical: 0.083-1.0)
    """
    # Validate ranges
    assert 0 < capacity < 1000, "Capacity should be in kWh"
    assert 0 < max_power < 100, "Power should be in kW"
    # ... rest of implementation
```

## Related Documentation

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery Modeling**

    ---

    See units in context of battery formulation.

    [:material-arrow-right: Battery modeling](../modeling/battery.md)

- :material-transmission-tower:{ .lg .middle } **Grid Modeling**

    ---

    Price units and grid formulation.

    [:material-arrow-right: Grid modeling](../modeling/grid.md)

</div>
