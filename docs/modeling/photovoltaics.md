# Photovoltaics Modeling

Solar generation with optional curtailment for negative export price scenarios.

## Model Formulation

### Decision Variables

**Without curtailment** (default):

None - generation follows forecast.

**With curtailment enabled**:

- $P_{\text{solar}}(t)$: Actual generation (kW) - `{name}_power_{t}`

### Parameters

- $P_{\text{forecast}}(t)$: Solar forecast (kW) - from `forecast` sensors
- $c_{\text{production}}$: Production price (\$/kWh) - from `production_price` config (optional, default 0)

### Constraints

#### Without Curtailment

$$
P_{\text{solar}}(t) = P_{\text{forecast}}(t) \quad \forall t
$$

Generation exactly matches forecast.

**Implementation**:

```python
power_production = forecast  # List of constants
```

#### With Curtailment

$$
0 \leq P_{\text{solar}}(t) \leq P_{\text{forecast}}(t) \quad \forall t
$$

Generation can be reduced below forecast.

**Implementation**:

```python
power_production = [
    LpVariable(f"{name}_power_{i}", lowBound=0, upBound=forecast[i])
    for i in range(n_periods)
]
```

### Cost Contribution

$$
C_{\text{solar}} = \sum_{t=0}^{T-1} P_{\text{solar}}(t) \cdot c_{\text{production}} \cdot \Delta t
$$

Usually $c_{\text{production}} = 0$ (solar is free).

## Physical Interpretation

**No curtailment**: Standard operation - use all available solar.

**Curtailment**: Reduce generation when:
- Export prices are negative (you pay to export)
- Export limits prevent sending power to grid
- Battery full and load satisfied

Curtailment requires inverter with active power limiting.

## Configuration Impact

| Parameter | Impact |
|-----------|--------|
| Curtailment disabled | Solar always at forecast, simplest |
| Curtailment enabled | Can reduce generation, needs compatible inverter |
| Production price > 0 | Models feed-in tariff (rare) |
| Production price < 0 | Models solar contract costs (very rare) |

**Negative export prices**: Curtailment becomes economically beneficial.

**Forecast accuracy**: Directly affects optimization quality - inaccurate forecasts lead to sub-optimal decisions.

## Related Documentation

- [Photovoltaics Configuration](../user-guide/entities/photovoltaics.md)
- [Grid Modeling](grid.md)
- [Objective Function](objective-function.md)
