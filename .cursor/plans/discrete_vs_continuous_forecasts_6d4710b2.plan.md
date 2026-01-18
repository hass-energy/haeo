---
name: Discrete vs Continuous Forecasts
overview: Add a `step_function` flag to differentiate discrete data (prices - hold value until next point) from continuous data (power - interpolate between points), threading this through the data loading pipeline.
todos:
  - id: add-field-info-attr
    content: "Add step_function: bool = False attribute to InputFieldInfo dataclass"
    status: pending
  - id: update-fuser
    content: Add step_function parameter to fuse_to_intervals() with conditional logic
    status: pending
    dependencies:
      - add-field-info-attr
  - id: update-loader
    content: Add step_function parameter to TimeSeriesLoader.load_intervals()
    status: pending
    dependencies:
      - update-fuser
  - id: update-entity
    content: Pass step_function from field_info to loader in HaeoInputNumber
    status: pending
    dependencies:
      - update-loader
  - id: update-adapters
    content: Set step_function=True for price fields in grid, connection, and solar adapters
    status: pending
    dependencies:
      - add-field-info-attr
  - id: update-tests
    content: Update tests to cover both step_function modes
    status: pending
    dependencies:
      - update-fuser
---

# Discrete vs Continuous Forecast Handling

## Problem

The recent commit (1c4d178b) hardcoded step-function behavior in `fuse_to_intervals()` that extends the present value to all intervals before the first forecast point. This is correct for **prices** (discrete/step data) but incorrect for **power forecasts** (continuous/interpolated data).

## Solution

Add a `step_function: bool` flag that threads through the data loading pipeline:

```mermaid
flowchart LR
    A[InputFieldInfo] -->|step_function| B[HaeoInputNumber]
    B -->|step_function| C[TimeSeriesLoader]
    C -->|step_function| D[fuse_to_intervals]
```

## Key Changes

### 1. Add `step_function` attribute to InputFieldInfo

In [`custom_components/haeo/elements/input_fields.py`](custom_components/haeo/elements/input_fields.py):

```python
@dataclass(frozen=True, slots=True)
class InputFieldInfo[T]:
    # ... existing fields ...
    step_function: bool = (
        False  # True for discrete data (prices), False for continuous (power)
    )
```

### 2. Add parameter to fuse_to_intervals()

In [`custom_components/haeo/data/util/forecast_fuser.py`](custom_components/haeo/data/util/forecast_fuser.py):

```python
def fuse_to_intervals(
    present_value: float | None,
    forecast_series: ForecastSeries,
    horizon_times: Sequence[float],
    step_function: bool = False,  # New parameter
) -> list[float]:
```

When `step_function=False`, skip the logic that extends `present_value` to intervals before the first forecast point.

### 3. Thread through TimeSeriesLoader

In [`custom_components/haeo/data/loader/time_series_loader.py`](custom_components/haeo/data/loader/time_series_loader.py):

Add `step_function: bool = False` parameter to `load_intervals()` and pass it to `fuse_to_intervals()`.

### 4. Pass from entity to loader

In [`custom_components/haeo/entities/haeo_number.py`](custom_components/haeo/entities/haeo_number.py):

Pass `self._field_info.step_function` when calling `load_intervals()`.

### 5. Update price field definitions

In the following adapters, set `step_function=True` for price fields:

- [`custom_components/haeo/elements/grid/adapter.py`](custom_components/haeo/elements/grid/adapter.py) - `import_price`, `export_price`
- [`custom_components/haeo/elements/connection/adapter.py`](custom_components/haeo/elements/connection/adapter.py) - `price_source_target`, `price_target_source`
- [`custom_components/haeo/elements/solar/adapter.py`](custom_components/haeo/elements/solar/adapter.py) - `price_production`

## Behavior Summary

| Data Type | `step_function` | Behavior |

| \------------------------- | ----------------- | ------------------------------------------------------------------ |

| Prices | `True` | Present value extends to all intervals before first forecast point |

| Power, Efficiency, Limits | `False` (default) | Standard interpolation, present value only at position 0 |