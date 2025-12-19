---
name: Fix Required Energy Algorithm
overview: Update the required energy calculation to use maximum drawdown approach, which accounts for solar recharging the battery and gives a more realistic battery capacity requirement.
todos:
  - id: update-algorithm
    content: Update calculate_required_energy() to use maximum drawdown approach
    status: completed
  - id: update-tests
    content: Update tests to verify new algorithm behavior with solar recharge scenarios
    status: completed
  - id: update-snapshots
    content: Update scenario snapshots with new values
    status: completed
---

# Fix Required Energy Algorithm

## Problem

The current algorithm calculates the **total** deficit energy over the horizon, ignoring solar surplus periods that recharge the battery. This can produce values that exceed battery capacity and don't reflect the actual battery requirement.

## Solution

Use the **maximum drawdown** approach: for each timestep, find the deepest point the battery would drain to before solar recharges it.

## Algorithm Change

**Current (incorrect):**

```python
net_power = solar - load
deficit_power = max(0, -net_power)  # Only deficits
deficit_energy = deficit_power * period
required_energy = reverse_cumsum(deficit_energy)  # Sum of all future deficits
```

**New (correct):**

```python
net_power = solar - load  # Can be positive (surplus) or negative (deficit)
net_energy = net_power * period

for t in range(n_periods + 1):
    # Calculate running balance from t forward
    future_net = net_energy[t:]
    if len(future_net) == 0:
        required_energy[t] = 0
    else:
        running_balance = cumsum(future_net)
        # Maximum drawdown is the most negative point
        max_drawdown = min(0, min(running_balance))
        required_energy[t] = abs(max_drawdown)
```

## Example Verification

| Period | Load | Solar | Net Energy | Running Balance | Max Drawdown |

|\--------|------|-------|------------|-----------------|--------------|

| 6-8pm | 2kW | 0kW | -4 kWh | [-4, +4, +1] | 4 kWh |

| 8-12am | 1kW | 3kW | +8 kWh | [+8, +5] | 0 kWh |

| 12-6am | 0.5kW| 0kW | -3 kWh | [-3] | 3 kWh |

Result: `[4, 0, 3, 0]` instead of `[7, 3, 3, 0]`

## Files to Modify

1. **[`custom_components/haeo/data/__init__.py`](custom_components/haeo/data/__init__.py)** - Update `calculate_required_energy()` function

2. **[`tests/data/test_required_energy.py`](tests/data/test_required_energy.py)** - Update tests to verify new behavior

## Implementation

### Updated Algorithm (`data/__init__.py`)

```python
def calculate_required_energy(
    participants: Mapping[str, ElementConfigData],
    periods_hours: Sequence[float],
) -> list[float]:
    n_periods = len(periods_hours)
    if n_periods == 0:
        return [0.0]

    # Aggregate load and solar forecasts
    total_load = np.zeros(n_periods)
    total_solar = np.zeros(n_periods)
    # ... aggregation code ...

    # Calculate NET power (positive = surplus, negative = deficit)
    net_power = total_solar - total_load
    net_energy = net_power * np.array(periods_hours)

    # For each timestep, find the maximum drawdown from that point forward
    required_energy = []
    for t in range(n_periods + 1):
        if t >= n_periods:
            required_energy.append(0.0)
        else:
            future_net = net_energy[t:]
            running_balance = np.cumsum(future_net)
            max_drawdown = min(0.0, float(np.min(running_balance)))
            required_energy.append(abs(max_drawdown))

    return required_energy
```

### Key Test Cases

1. **Solar surplus in middle recharges battery** - required energy is peak drawdown, not total
2. **No solar** - behaves same as before (all deficit)
3. **Solar always exceeds load** - required energy is 0
4. **Overnight scenario** - captures peak before sunrise
