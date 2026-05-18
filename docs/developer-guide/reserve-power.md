# Reserve Power System — Design Document

## Goal

Ensure batteries hold enough stored energy to survive a grid blackout.
The system computes a per-period reserve requirement and injects it as a
SOC floor via the battery undercharge partition.

## Core Concept: Island

An "island" is the set of elements that remain connected during a blackout
(everything except grid). The user selects which elements are in the core island.
Sheddable loads can be excluded.

- **Island loads**: non-discretionary loads that must be served during blackout
- **Island generation**: solar/wind that still produces during blackout
- **Island storage**: batteries/EVs that provide the backup energy
- **Excluded**: grid connections, sheddable loads

## Configuration

- User selects which elements participate in the reserve group
- Configurable window W (default: full horizon, can be 24h, 48h, etc.)
- Reserve group can exclude specific loads (sheddable) and grid

## Mathematical Formulation

### Net demand per period
```
net_demand[t] = (Σ island_loads[t] - Σ island_gen[t]) × Δt[t]    [kWh]
```

Loads can be LP variables (schedulable) or constants (fixed forecast).
Generation is typically constant (solar forecast).

### Cumulative net demand
```
cum[t] = Σ_{k=0}^{t} net_demand[k]    [kWh, running sum]
```

### Running maximum (O(n) chain)
```
max_cum[t] ≥ max_cum[t-1]    (monotonically non-decreasing)
max_cum[t] ≥ cum[t]          (tracks current cumulative demand)
```

This is the LP-native prefix maximum — 2 constraints per period.
The undercharge cost on batteries naturally minimizes max_cum (pulls it tight
to the true running max).

### Reserve requirement
```
reserve[t] = max_cum[N-1] - cum[t-1]    (full horizon)
```

Where cum[-1] = 0. This gives the maximum remaining net deficit from time t
to the end of the horizon. The reserve DECREASES over time as more demand
has been served.

### Battery group SOC floor (energy constraint)
```
Σ_batteries stored_energy[t] × η_battery ≥ reserve[t]
```

Where η is the discharge path efficiency from battery to island loads.
This replaces the constant undercharge floor with the dynamic reserve variable.

### Power constraint
```
Σ_batteries discharge_limit[t] ≥ max_instantaneous_load[t]
```

Ensures the batteries can physically deliver enough power to cover the load.
Handles EV disconnection (discharge_limit = 0 when disconnected).

## Key Properties

- **O(n) constraints**: running max chain + reserve + SOC floor = ~4n constraints
- **Handles solar recovery**: peak drawdown may occur mid-horizon, not at end
- **Reserve can exceed capacity**: signals insufficient backup, priced via undercharge
- **Schedulable loads interact**: LP can shift loads to reduce reserve requirement
- **Multiple batteries pooled**: LP decides how to allocate reserve across batteries
- **Efficiency-aware**: discharge path losses reduce effective stored energy

## Windowed Version

For a sliding window of W hours, reset the running max chain every W periods:
```
max_cum_w[t] = cum[t]                    if t is a window boundary
max_cum_w[t] ≥ max_cum_w[t-1]           otherwise
max_cum_w[t] ≥ cum[t]                   always
```

Creates one "max" per window rather than one for the full horizon.

## Integration with HAEO

1. **Pre-computation**: Walk network graph to find path efficiencies from
   each battery to each island load (Dijkstra/BFS on efficiency product)
2. **Network.add_reserve()**: Accepts island element names + window config,
   creates reserve variables and constraints on the solver
3. **Undercharge partition**: Replace constant floor with reserve[t] variable
4. **Post-solve**: Extract per-battery reserve allocation for display

## Open Questions

- How to integrate with the undercharge partition's existing cost structure
- Whether to expose reserve[t] as a sensor output
- Per-battery reserve allocation strategy for display (proportional to capacity?)
- Whether the power constraint should be per-period or worst-case-in-window

## File locations

- `custom_components/haeo/core/model/reserve.py` -- reserve formulation (running max chain + windowed + soft/hard SOC floor)
- `custom_components/haeo/core/model/reserve_graph.py` -- island discovery + path efficiencies
- `custom_components/haeo/core/model/elements/segments/soc_pricing.py` -- updated to accept LP variable thresholds
- `custom_components/haeo/core/model/network.py` -- `Network.add_reserve()` API
- `custom_components/haeo/core/model/tests/test_reserve.py` -- 12 unit tests
- `custom_components/haeo/core/model/tests/test_reserve_graph.py` -- 6 graph walk tests
- `custom_components/haeo/core/model/tests/test_reserve_e2e.py` -- 5 end-to-end tests (realistic 24h topology)

## Status (experiment/reserve-power branch, 10 commits)

### Complete
- [x] Core formulation: running max chain, O(n) for full horizon
- [x] Sliding window mode: O(n*W) for W-period windows
- [x] Soft vs hard SOC floor: hard_soc_floor parameter controls enforcement
- [x] soc_pricing accepts LP variable thresholds (backwards-compatible)
- [x] Graph walk: auto-discovers island (batteries, loads, generators)
- [x] Path efficiency: BFS with efficiency product tracking (multi-hop)
- [x] Multi-battery pooling: LP allocates reserve across batteries
- [x] Network.add_reserve() one-liner API
- [x] Post-solve outputs: reserve_energy_requirement + reserve_peak_deficit
- [x] Sheddable load exclusion (manual exclude_elements)
- [x] Realistic e2e tests: 24h topology with inverter, solar, EV, multiple loads
- [x] 23 tests passing, 6 scenario tests unbroken, all lint clean

### TODO
- [ ] Coordinator integration: call add_reserve() after network creation
- [ ] Configuration schema: reserve section on hub entry (enable, window_hours, exclude_elements)
- [ ] Sensor entities: expose reserve_energy_requirement as HA sensor
- [ ] Per-battery reserve allocation for dashboard display
