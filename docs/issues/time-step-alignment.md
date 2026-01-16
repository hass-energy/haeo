## Problem

HAEO's optimization time steps are often misaligned with external forecast data, leading to displeasing interpolation outside tier 1 timesteps.

Misalignment occurs when the optimization is ran off clock boundaries:

Pricing forecasts typically use fixed intervals aligned to clock boundaries:

- Wholesale electricity prices: 5-minute or 30-minute intervals starting on the hour (e.g., 14:00, 14:05, 14:10...)
- Time-of-use rates: Change at specific times (e.g., 15:00, 21:00)

When the optimization runs at an arbitrary time (e.g., 14:03), the time steps become offset from these natural boundaries:

- Optimization boundaries: 14:03, 14:08, 14:13, 14:18...
- Forecast boundaries: 14:00, 14:05, 14:10, 14:15...

Every optimization boundary is 3 minutes out of phase with the forecast data, requiring interpolation at every step.

### Impact

This actually doesn't have much impact as we have 1 minute intervals in tier 1, meaning once it gets close enough to make decisions, we will be correctly aligned and no interpolating is taking place.

However, its unnecessarily annoying and obfuscates the underlying data when plotting the plan as a table.

## Proposed Solution

Dynamically adjust the number of time steps in each tier to align with forecast boundaries, while maintaining:

- Minimum step counts per tier
- A consistent total number of steps
- A fixed total duration (e.g., 5 days)

### Approach

**Tiers 1-3 align to forecast boundaries:**

Each tier adjusts its step count to end on the next tier's natural boundary, while respecting minimums.

Starting at 14:43 with forecast boundaries at 5-minute and 30-minute intervals:

| Tier | Step Size | Steps  | Range         | Notes                             |
| ---- | --------- | ------ | ------------- | --------------------------------- |
| T1   | 1 min     | 7      | 14:43 → 14:50 | Aligns to 5-min boundary (min 5)  |
| T2   | 5 min     | 8      | 14:50 → 15:30 | Aligns to 30-min boundary (min 6) |
| T3   | 30 min    | varies | 15:30 → hour  | Aligns to 60-min boundary         |

**Tier 4 absorbs the variance:**

T4 adjusts both step count and step size to:

1. Maintain a fixed total step count across all optimizations
2. Reach the same end time (fixed total duration)

For example, if T1-T3 ends 45 minutes earlier in one scenario vs another:

- T4 covers 45 more minutes of duration
- T4 uses a mix of step sizes (e.g., some 30-min, some 60-min steps) to fill the gap while keeping total step count constant

### Variance Analysis

**T1 (1-min steps, min 5, aligning to 5-min):**

- Range: 5-9 steps depending on start minute

**T2 (5-min steps, min 6, aligning to 30-min):**

- Range: 6-11 steps depending on T1 end position

**Combined T1+T2:**

- Best case (start at :55): 5 + 6 = 11 steps, 35 minutes
- Worst case (start at :26): 9 + 11 = 20 steps, 64 minutes
- Variance: 9 steps, ~30 minutes

T4 must absorb this variance through flexible step sizing.

### Constraints

1. **Minimum step counts**: Each tier maintains a minimum number of steps to ensure adequate near-term resolution

2. **Fixed total step count**: Every optimization uses the same number of steps for consistent solver performance

3. **Fixed total duration**: Every optimization covers the same time horizon (e.g., 5 days from start)

4. **Standard tier progression**: Maintain the progression from fine to coarse resolution (1-minute → 5-minute → 30-minute → 60-minute)

## Configuration Changes

### Current Configuration

The current tier configuration uses fixed counts and durations:

```python
# From const.py defaults
CONF_TIER_1_COUNT = 5  # 5 × 1-min = 5 minutes
CONF_TIER_1_DURATION = 1
CONF_TIER_2_COUNT = 11  # 11 × 5-min = 55 minutes (cumulative: 1 hour)
CONF_TIER_2_DURATION = 5
CONF_TIER_3_COUNT = 46  # 46 × 30-min = 23 hours (cumulative: 24 hours)
CONF_TIER_3_DURATION = 30
CONF_TIER_4_COUNT = 48  # 48 × 60-min = 48 hours (cumulative: 72 hours)
CONF_TIER_4_DURATION = 60

# Total: 110 periods, 72 hours
```

Presets calculate T4 count dynamically based on horizon:

```python
CONF_TIER_4_COUNT = (total_minutes - 1440) // 60  # Remainder after first 24 hours
```

### Proposed Configuration

Replace fixed tier counts with:

1. **Tier durations** (unchanged): 1, 5, 30, 60 minutes
2. **Minimum tier counts**: Minimum steps per tier for near-term resolution
3. **Total step count**: Fixed number of steps across all optimizations
4. **Total duration**: Fixed horizon length (e.g., 5 days)

```python
# New configuration model
CONF_TIER_1_DURATION = 1
CONF_TIER_1_MIN_COUNT = 5  # At least 5 × 1-min steps

CONF_TIER_2_DURATION = 5
CONF_TIER_2_MIN_COUNT = 6  # At least 6 × 5-min steps

CONF_TIER_3_DURATION = 30
CONF_TIER_3_MIN_COUNT = 4  # At least 4 × 30-min steps

CONF_TIER_4_DURATION = 60  # T4 absorbs variance, no minimum

CONF_HORIZON_DURATION = 5  # Horizon length
CONF_HORIZON_UNIT = "days"  # Unit selector: "minutes", "hours", "days"
```

The horizon duration should have a unit selector in the UI (minutes/hours/days) to make it easier to configure common horizons like "5 days" or "72 hours".

The total step count is computed at runtime based on the worst-case alignment scenario, ensuring consistent solver performance without requiring user configuration.

At runtime, the system calculates actual tier counts based on start time:

1. T1 count: Steps needed to reach 5-min boundary (respecting minimum)
2. T2 count: Steps needed to reach 30-min boundary (respecting minimum)
3. T3 count: Steps needed to reach 60-min boundary (respecting minimum)
4. T4: Fills remaining steps with mixed sizing to reach target duration
