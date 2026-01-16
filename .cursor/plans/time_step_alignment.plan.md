# Time Step Alignment Implementation

## Overview

This feature dynamically adjusts tier step counts to align optimization boundaries with forecast data boundaries, eliminating interpolation artifacts in tiers 2-4 while maintaining consistent solver performance.

## Key Design Decisions

- **Reuse existing keys**: `tier_X_count` keys are reinterpreted as minimum counts (no migration of keys needed)
- **T1-T3**: Expand step counts to reach the next tier's natural boundary (respecting minimums)
- **Variance absorption strategy**: Extra steps added as 30-min blocks to T3 (even count) or T3 + one trailing 30-min in T4 (odd count), keeping T3 on hour boundaries
- **Computed total steps**: Based on worst-case alignment scenario, calculated once at configuration time
- **Choose selector for horizon**: UI presents 3 mutually exclusive number inputs (days/hours/minutes), stored as `horizon_duration_minutes`

---

## Implementation Steps

### 1. Constants and Configuration Model

**File**: [custom_components/haeo/const.py](custom_components/haeo/const.py)

**Reuse existing tier keys** - Reinterpret `tier_X_count` semantically as minimum counts (no key changes needed). Add only the horizon configuration:

```python
# New configuration key - single source of truth for horizon length
CONF_HORIZON_DURATION_MINUTES: Final = "horizon_duration_minutes"

# New default (5 days = 7200 minutes)
DEFAULT_HORIZON_DURATION_MINUTES: Final = 5 * 24 * 60
```

**Existing keys reinterpreted**:

- `tier_1_count` -> minimum T1 steps (default 5)
- `tier_2_count` -> minimum T2 steps (default 6, changed from 11)
- `tier_3_count` -> minimum T3 steps (default 4, changed from 46)
- `tier_4_count` -> **removed from config** (computed at runtime to absorb variance)

---

### 2. Core Alignment Algorithm

**File**: [custom_components/haeo/util/forecast_times.py](custom_components/haeo/util/forecast_times.py)

Create new functions for dynamic alignment:

```python
def calculate_aligned_tier_counts(
    start_time: datetime,
    tier_durations: tuple[int, int, int, int],  # (1, 5, 30, 60) minutes
    min_counts: tuple[int, int, int],  # (5, 6, 4)
    total_steps: int,
    horizon_minutes: int,
) -> tuple[list[int], list[int]]:
    """
    Calculate tier step counts aligned to forecast boundaries.

    Returns:
        Tuple of (period_durations_seconds, tier_counts)
    """
```

The algorithm:

1. **T1 alignment**: Calculate steps from start_time to next 5-minute boundary

    - Example: 14:43 -> 14:50 = 7 steps (minimum 5)
    - `steps = max(min_count, minutes_to_boundary(start, 5))`

2. **T2 alignment**: Calculate steps from T1 end to next 30-minute boundary

    - Example: 14:50 -> 15:30 = 8 steps (minimum 6)
    - `steps = max(min_count, minutes_to_boundary(t1_end, 30) / 5)`

3. **T3 alignment**: Calculate steps from T2 end to next 60-minute boundary

    - Example: 15:30 -> 16:00 = 1 step (minimum 4)
    - `steps = max(min_count, minutes_to_boundary(t2_end, 60) / 30)`

4. **T4 variance absorption**: Extend T3 and/or add trailing 30-min step to T4

    ```python
    remaining_steps = total_steps - (t1 + t2 + t3)
    remaining_duration = horizon_end - t3_end

    # How many steps would T4 need if purely 60-min?
    base_t4_steps = remaining_duration // 60

    # Extra steps that must be 30-min instead of 60-min
    extra_steps = remaining_steps - base_t4_steps

    if extra_steps % 2 == 0:
        # Even: add all extra steps as 30-min to T3
        t3 += extra_steps
        t4 = base_t4_steps  # pure 60-min steps
        t4_trailing_30 = False
    else:
        # Odd: add (extra-1) 30-min steps to T3, one 30-min at end of T4
        t3 += extra_steps - 1
        t4 = base_t4_steps  # 60-min steps
        t4_trailing_30 = True  # one 30-min step at end
    ```

**Why even/odd matters**: Adding an even number of 30-min steps to T3 maintains hour-boundary alignment (2 × 30 = 60 min). The odd case places the leftover 30-min step at the end of T4 to preserve T3's hour alignment.

**Result**: T3 absorbs most variance, T4 stays clean with 60-min steps (plus at most one trailing 30-min step)

Also add:

```python
def calculate_worst_case_total_steps(
    min_counts: tuple[int, int, int],
    tier_durations: tuple[int, int, int, int],
    horizon_minutes: int,
) -> int:
    """Calculate total step count based on worst-case alignment."""
```

---

### 3. Update Horizon Manager

**File**: [custom_components/haeo/horizon.py](custom_components/haeo/horizon.py)

Modify to use dynamic alignment:

```python
def _update_timestamps(self) -> None:
    """Update cached timestamps with aligned tier counts."""
    now = dt_util.utcnow()

    # Calculate aligned periods based on current time
    periods_seconds = calculate_aligned_periods(
        start_time=now,
        min_counts=(self._min_t1, self._min_t2, self._min_t3),
        tier_durations=(1, 5, 30, 60),
        total_steps=self._total_steps,
        horizon_minutes=self._horizon_minutes,
    )

    self._periods_seconds = periods_seconds
    self._forecast_timestamps = generate_forecast_timestamps(periods_seconds)
```

Key changes:

- Store min_counts instead of fixed counts from config
- Store horizon_minutes computed from config
- Recalculate `_periods_seconds` on each update (not just timestamps)
- `periods_seconds` becomes dynamic (changes per optimization run)

---

### 4. Update Config Flows and Presets

**File**: [custom_components/haeo/flows/__init__.py](custom_components/haeo/flows/__init__.py)

**Remove old preset system**: The `HORIZON_PRESETS` dictionary and `CONF_HORIZON_PRESET` are no longer needed. The Choose selector replaces preset selection with direct horizon duration input.

**Update `_create_horizon_preset()`** (still useful for default config generation):

```python
def _create_default_tier_config(horizon_minutes: int) -> dict[str, int]:
    """Create default tier configuration for a given horizon."""
    return {
        CONF_TIER_1_COUNT: 5,  # minimum T1 steps
        CONF_TIER_1_DURATION: 1,
        CONF_TIER_2_COUNT: 6,  # minimum T2 steps
        CONF_TIER_2_DURATION: 5,
        CONF_TIER_3_COUNT: 4,  # minimum T3 steps
        CONF_TIER_3_DURATION: 30,
        CONF_TIER_4_DURATION: 60,  # no count - computed at runtime
        CONF_HORIZON_DURATION_MINUTES: horizon_minutes,
    }


# Default for new installations: 5 days
DEFAULT_CONFIG = _create_default_tier_config(5 * 24 * 60)
```

**Horizon UI with Choose Selector**: Replace the preset dropdown with a Choose selector containing 3 number inputs:

```python
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

# Choose selector structure - user picks a unit, then enters a number
vol.Required(CONF_HORIZON_DURATION_MINUTES): vol.Any(
    # Option 1: Days (shows number input for days)
    vol.All(
        {"days": NumberSelector(NumberSelectorConfig(min=2, max=14, step=1, mode=NumberSelectorMode.BOX))},
        lambda x: x["days"] * 24 * 60,
    ),
    # Option 2: Hours (shows number input for hours)
    vol.All(
        {"hours": NumberSelector(NumberSelectorConfig(min=48, max=336, step=1, mode=NumberSelectorMode.BOX))},
        lambda x: x["hours"] * 60,
    ),
    # Option 3: Minutes (shows number input for minutes)
    vol.All(
        {"minutes": NumberSelector(NumberSelectorConfig(min=2880, max=20160, step=60, mode=NumberSelectorMode.BOX))},
        lambda x: x["minutes"],
    ),
)
```

The Choose selector presents three mutually exclusive options. The user selects a unit type (days/hours/minutes), then enters a value. The result is always stored as `horizon_duration_minutes`.

**Remove from flows/init.py**:

- `HORIZON_PRESET_*` constants
- `HORIZON_PRESETS` dictionary
- `CONF_HORIZON_PRESET` usage
- `get_tier_config()` function (no longer needed)

**File**: [custom_components/haeo/flows/options.py](custom_components/haeo/flows/options.py)

Update to:

- Use new Choose selector for horizon
- Remove preset dropdown logic
- Remove `CONF_TIER_4_COUNT` from custom tiers step

---

### 5. Migration Support

**File**: [custom_components/haeo/__init__.py](custom_components/haeo/__init__.py)

Add config entry migration to compute `horizon_duration_minutes` from existing configuration. Must handle both preset-based and custom configurations:

```python
async def async_migrate_entry(hass, config_entry) -> bool:
    """Migrate config entry to add horizon_duration_minutes."""
    if config_entry.version == 1:
        data = dict(config_entry.data)

        # Check if using a preset (format: "{N}_days")
        horizon_preset = data.get("horizon_preset")

        if horizon_preset and horizon_preset != "custom" and horizon_preset.endswith("_days"):
            # Parse days from preset string (e.g., "5_days" -> 5)
            days = int(horizon_preset.split("_")[0])
            horizon_minutes = days * 24 * 60
        else:
            # Custom config: compute total horizon from tier configuration
            horizon_minutes = (
                data["tier_1_count"] * data["tier_1_duration"]
                + data["tier_2_count"] * data["tier_2_duration"]
                + data["tier_3_count"] * data["tier_3_duration"]
                + data["tier_4_count"] * data["tier_4_duration"]
            )

        data[CONF_HORIZON_DURATION_MINUTES] = horizon_minutes

        # Remove tier_4_count (now computed at runtime)
        data.pop("tier_4_count", None)

        # Remove old horizon_preset key (replaced by horizon_duration_minutes)
        data.pop("horizon_preset", None)

        hass.config_entries.async_update_entry(config_entry, data=data, version=2)
    return True
```

**Migration behavior:**

- If `horizon_preset` is set to a known preset (2_days, 3_days, etc.), use the preset's duration directly
- If `horizon_preset` is "custom" or missing, compute duration from tier counts
- Remove both `tier_4_count` and `horizon_preset` (superseded by `horizon_duration_minutes`)

---

### 6. Translations

**File**: [custom_components/haeo/translations/en.json](custom_components/haeo/translations/en.json)

**Remove old preset translations**:

```json
// DELETE this section:
"selector": {
  "horizon_preset": {
    "options": { "2_days": "2 days", "3_days": "3 days", ... }
  }
}
```

**Update tier count labels** to clarify they are minimums:

```json
{
  "data": {
    "tier_1_count": "Tier 1 Minimum Steps (fine-grained)",
    "tier_2_count": "Tier 2 Minimum Steps (short-term)",
    "tier_3_count": "Tier 3 Minimum Steps (medium-term)"
  }
}
```

**Add labels for Choose selector** horizon options:

```json
{
  "data": {
    "horizon_duration_minutes": "Planning Horizon",
    "horizon_days": "Days",
    "horizon_hours": "Hours",
    "horizon_minutes": "Minutes"
  }
}
```

---

### 7. Tests

**File**: [tests/util/test_forecast_times.py](tests/util/test_forecast_times.py)

Add comprehensive tests for alignment logic:

```python
class AlignmentTestCase(TypedDict):
    start_minute: int  # minute within hour (0-59)
    expected_t1_count: int
    expected_t2_count: int
    expected_t3_count: int

ALIGNMENT_TEST_CASES = {
    "aligned_to_hour": {"start_minute": 0, ...},
    "worst_case_t1": {"start_minute": 26, ...},  # 4 min to :30
    "worst_case_t2": {"start_minute": 1, ...},   # 29 min to :30
}
```

**File**: [tests/test_horizon.py](tests/test_horizon.py) (new)

Test that HorizonManager produces aligned timestamps.

**File**: Update [tests/flows/test_options_flow.py](tests/flows/test_options_flow.py)

Update tests to:

- Remove `tier_4_count` from test configs
- Add `horizon_duration_minutes` to test configs
- Verify Choose selector behavior

---

## Variance Analysis Summary

From the issue document:

| Start Time | T1 Steps | T2 Steps | T1+T2 Total | Duration |

|\------------|----------|----------|-------------|----------|

| :55 (best) | 5 | 6 | 11 steps | 35 min |

| :26 (worst)| 9 | 11 | 20 steps | 64 min |

- Maximum variance: 9 steps, ~30 minutes
- **Absorption strategy**: Up to 9 extra 30-min steps added to T3 (or 8 to T3 + 1 trailing in T4 if odd)
- T3 can extend by up to 4.5 hours in best-case alignment scenarios
- T4 remains clean: pure 60-min steps with at most one trailing 30-min step

---

## Files to Modify

1. `custom_components/haeo/const.py` - Add `CONF_HORIZON_DURATION_MINUTES`, remove `CONF_HORIZON_PRESET`, update defaults
2. `custom_components/haeo/util/forecast_times.py` - Core alignment algorithm
3. `custom_components/haeo/horizon.py` - Use dynamic alignment
4. `custom_components/haeo/flows/__init__.py` - Remove preset system, add Choose selector schema, update defaults
5. `custom_components/haeo/flows/options.py` - Replace preset dropdown with Choose selector, remove tier_4_count
6. `custom_components/haeo/__init__.py` - Add migration (handles both presets and custom configs)
7. `custom_components/haeo/translations/en.json` - Remove preset translations, add Choose selector labels
8. `tests/util/test_forecast_times.py` - Add alignment tests
9. Various test files - Remove preset references, add horizon_duration_minutes
