---
name: Add time param to optimize
overview: Add an optional `time` parameter to the `haeo.optimize` service that allows running optimization against historical data from the recorder, using the same pattern as the existing `save_diagnostics` service.
todos:
  - id: move-state-providers
    content: Create state/ directory and move state providers from diagnostics/
    status: completed
  - id: forecast-times
    content: Add optional start_time parameter to tiers_to_periods_seconds()
    status: completed
  - id: coordinator-historical
    content: Add target_time parameter to async_run_optimization() and historical state loading
    status: completed
  - id: service-schema
    content: Add time field to optimize service schema (conditional on recorder)
    status: completed
  - id: services-yaml
    content: Add time field definition to services.yaml
    status: completed
  - id: tests
    content: Add tests for historical optimization
    status: completed
---

# Add Time Parameter to Optimize Service

Add an optional `time` parameter to the `haeo.optimize` service, enabling historical optimization against recorder data. This follows the same pattern as `save_diagnostics`.

## Key Changes

### 1. Move State Providers to Shared Location

Create a new `state/` directory and move state provider files from `diagnostics/`:

- Create `custom_components/haeo/state/` directory
- Move [diagnostics/state_provider.py](custom_components/haeo/diagnostics/state_provider.py) to `state/state_provider.py`
- Move [diagnostics/historical_state_provider.py](custom_components/haeo/diagnostics/historical_state_provider.py) to `state/historical_state_provider.py`
- Create `state/__init__.py` with exports for `StateProvider`, `CurrentStateProvider`, `HistoricalStateProvider`
- Update imports in [diagnostics/__init__.py](custom_components/haeo/diagnostics/__init__.py) and [services.py](custom_components/haeo/services.py)

### 2. Service Layer ([services.py](custom_components/haeo/services.py))

- Add `time` field to the optimize schema (conditional on recorder availability, like save_diagnostics)
- In the handler, create a `HistoricalStateProvider` if time is provided
- Pass the target timestamp to the coordinator's optimization method

### 3. Coordinator ([coordinator/coordinator.py](custom_components/haeo/coordinator/coordinator.py))

- Modify `async_run_optimization()` to accept an optional `target_time: datetime | None` parameter
- When `target_time` is provided:
    - Generate forecast timestamps from that time instead of current time
    - Use `HistoricalStateProvider` to load input entity states from the recorder
- Add a new method `_load_from_historical_states()` that reads historical state for input entities using the state provider

### 4. Forecast Times Utility ([util/forecast_times.py](custom_components/haeo/util/forecast_times.py))

- Modify `tiers_to_periods_seconds()` to accept an optional `start_time` parameter
- When provided, use that time instead of `dt_util.utcnow()` for tier alignment calculations

### 5. Services YAML ([services.yaml](custom_components/haeo/services.yaml))

- Add the `time` field definition to the optimize service (same as save_diagnostics)

## Implementation Notes

- State providers move to new `state/` directory so they can be imported by both diagnostics and coordinator
- Input entity states are stored in the `forecast` attribute - the historical provider will retrieve these
- Historical optimization should validate that all required entity states exist at the target time (like save_diagnostics does)
- The service should raise `ServiceValidationError` if historical data is missing

## Error Handling

- Missing historical data should produce a clear error message listing which entities are missing
- Reuse the existing `no_history_at_time` translation key from save_diagnostics
