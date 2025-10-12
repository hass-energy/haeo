# Connection Modeling

Connections model power flow paths between entities with optional limits.

## Model Formulation

### Decision Variables

For each time step $t$:

- $P_c(t)$: Power flow on connection (kW) - `{name}_power_{t}`

### Parameters

- $P_{\min}$: Minimum power (kW) - from `min_power` config (can be negative for bidirectional)
- $P_{\max}$: Maximum power (kW) - from `max_power` config
- Source entity: Where power flows from
- Target entity: Where power flows to

### Constraints

#### Power Limits

$$
P_{\min} \leq P_c(t) \leq P_{\max} \quad \forall t
$$

**Implementation**:

```python
power = [
    LpVariable(f"{name}_power_{i}", lowBound=min_power, upBound=max_power)
    for i in range(n_periods)
]
```

#### Direction Convention

- **Positive flow**: Source → Target (forward direction)
- **Negative flow**: Target → Source (reverse direction, if $P_{\min} < 0$)

#### Power Balance Integration

Connection power participates in net entity balance:

- **At source net**: Connection is outflow
- **At target net**: Connection is inflow

## Physical Interpretation

**Unidirectional** ($P_{\min} = 0$):
- Solar → Net (generation only)
- Net → Load (consumption only)

**Bidirectional** ($P_{\min} < 0$):
- Grid ↔ Net (import/export)
- Battery ↔ Net (charge/discharge)
- Inverter between AC/DC nets

**Power limits**:
- Wire capacity
- Inverter rating
- Circuit breaker limits

## Configuration Impact

| Parameter | Impact |
|-----------|--------|
| $P_{\max}$ only | Unidirectional with limit |
| $P_{\min} < 0, P_{\max} > 0$ | Bidirectional (e.g., ±8 kW inverter) |
| No limits | Unlimited (e.g., direct grid connection) |

**Inverter modeling**: Connection with ±max_power between DC and AC nets.

## Related Documentation

- [Connections Guide](../user-guide/connections.md)
- [Net Entity Modeling](net-entity.md)
- [Power Balance](power-balance.md)
