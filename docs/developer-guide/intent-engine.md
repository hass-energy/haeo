---
title: Intent engine
---

# Intent engine

The intent engine derives hardware control signals from LP sensitivity analysis.
After optimization, each connection variable carries ranging information from HiGHS that answers:
"what should the physical device actually do?"

## Core concept

An LP optimal solution tells you the best power flow for each period.
But the hardware needs a **control signal** — not just a target value, but whether to actively limit or let the device run free.

HiGHS column ranging provides two pieces of information per variable:

- **Reduced cost**: the marginal cost of changing the variable by one unit ($/kWh).
- **Bound range** `[bdn, bup]`: how far the variable can move before the reduced cost changes.

The intent engine combines these with the forecast upper bound to produce one of two actionable signals:

| Intent | Meaning | Hardware action |
|--------|---------|-----------------|
| **UNLIMIT** | Any output up to physical max is acceptable | Remove limits, let device self-regulate |
| **SET** | Must actively limit to the recommended value | Set hardware limit to `bup` |

## Decision rule

```
IF forecast_max > 0:
    IF bup ≥ forecast_max AND reduced_cost ≤ 0:
        → UNLIMIT
    ELSE:
        → SET limit to bup
ELSE (zero forecast):
    IF power_limit constraint shadow price < 0:
        → UNLIMIT (device would reduce cost if it produced)
    ELSE:
        → SET 0 (device not wanted)
```

The zero-forecast case uses the power limit constraint's shadow price to disambiguate:
a negative shadow price means the constraint is the bottleneck (the device would help if it existed),
while zero or positive means the device wouldn't improve cost.

## Flexibility band

Each intent includes a band `[band_min, band_max]` — the range of power levels where the cost doesn't change.
Hardware can safely operate anywhere within this band without degrading optimization quality.

This enables:

- Real-time grid response without re-optimization
- Battery rate limiting for hardware protection
- Solar following actual irradiance within the band

## Reduced cost direction

The reduced cost sign indicates the preferred direction within the band:

- **Positive**: lower output is better (each additional kWh costs money)
- **Negative**: higher output is better (each additional kWh saves money)
- **Zero**: indifferent within the band

## Examples

### Solar with negative feed-in tariff

Solar forecast is 6 kW, load is 2 kW, export costs $0.03/kWh.

The optimizer produces 2 kW (self-consumption), but the column range extends to 6 kW.
Intent: **UNLIMIT** — the inverter can load-follow freely.
If load increases, solar covers it without re-optimization.

### Solar during grid oversupply

Solar forecast is 6 kW, load is 2 kW, grid pays $0.05/kWh to absorb.

The optimizer produces 0 kW, column range is `[0, 2]`.
Intent: **SET 2 kW** — must actively curtail solar above load level.
Each kWh of solar displaces paid grid import.

### Zero solar forecast, normal prices

No solar forecast, import costs $0.30/kWh.
Power limit constraint shadow price is -$0.27/kWh (negative = solar would help).
Intent: **UNLIMIT** — if solar appears unexpectedly, it's valuable.

### Zero solar forecast, grid pays to absorb

No solar forecast, grid pays $0.05/kWh to import.
Power limit constraint shadow price is $0.00 (solar not wanted).
Intent: **SET 0** — any solar would displace paid imports.

## Source

- [`custom_components/haeo/core/model/intent.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/intent.py)
