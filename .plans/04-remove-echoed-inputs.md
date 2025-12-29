# Phase 4: Remove Echoed Inputs from Model Outputs

## Goal

Clean up model layer and element adapters to only output computed values from optimization. Input values are now exposed via input entities, so echoing them as outputs is redundant.

## Prerequisites

- Phase 3 complete (network coordinator reads from input entities)
- Input entities expose all configurable values

## Deliverables

1. Updated `model/power_connection.py` - Remove echoed outputs
2. Updated element adapters - Remove echoed output mappings
3. Updated translations - Remove unused keys

## Values to Remove

### From `model/power_connection.py` outputs()

Currently echoed (REMOVE):

- `CONNECTION_POWER_MAX_SOURCE_TARGET` - constructor param
- `CONNECTION_POWER_MAX_TARGET_SOURCE` - constructor param
- `CONNECTION_PRICE_SOURCE_TARGET` - constructor param
- `CONNECTION_PRICE_TARGET_SOURCE` - constructor param

Keep (computed by optimization):

- `CONNECTION_POWER_SOURCE_TARGET` - LP variable result
- `CONNECTION_POWER_TARGET_SOURCE` - LP variable result
- `CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET` - constraint dual
- `CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE` - constraint dual
- `CONNECTION_TIME_SLICE` - constraint dual

### From `elements/grid.py` outputs()

Currently echoed (REMOVE):

- `GRID_POWER_MAX_IMPORT` - from connection max_power
- `GRID_POWER_MAX_EXPORT` - from connection max_power
- `GRID_PRICE_IMPORT` - from connection price
- `GRID_PRICE_EXPORT` - from connection price

Keep (computed):

- `GRID_POWER_IMPORT` - from connection power flow
- `GRID_POWER_EXPORT` - from connection power flow
- `GRID_POWER_ACTIVE` - derived from power flows
- `GRID_POWER_MAX_IMPORT_PRICE` - shadow price
- `GRID_POWER_MAX_EXPORT_PRICE` - shadow price

### From `elements/solar.py` outputs()

Currently echoed (REMOVE):

- `SOLAR_POWER_AVAILABLE` - forecast limit
- `SOLAR_PRICE` - production price

Keep (computed):

- `SOLAR_POWER` - actual generation
- `SOLAR_FORECAST_LIMIT` - shadow price

### From `elements/load.py` outputs()

Currently echoed (REMOVE):

- `LOAD_POWER_POSSIBLE` - forecast limit

Keep (computed):

- `LOAD_POWER` - actual consumption
- `LOAD_FORECAST_LIMIT_PRICE` - shadow price

### From `elements/inverter.py` outputs()

Currently echoed (REMOVE):

- `INVERTER_MAX_POWER_DC_TO_AC` - max power
- `INVERTER_MAX_POWER_AC_TO_DC` - max power

Keep (computed):

- `INVERTER_POWER_DC_TO_AC` - actual power flow
- `INVERTER_POWER_AC_TO_DC` - actual power flow
- `INVERTER_POWER_ACTIVE` - net power
- `INVERTER_DC_BUS_POWER_BALANCE` - shadow price
- `INVERTER_MAX_POWER_DC_TO_AC_PRICE` - shadow price
- `INVERTER_MAX_POWER_AC_TO_DC_PRICE` - shadow price

### From `elements/connection.py` outputs()

Currently echoed (REMOVE):

- `CONNECTION_POWER_MAX_SOURCE_TARGET` - max power
- `CONNECTION_POWER_MAX_TARGET_SOURCE` - max power
- `CONNECTION_PRICE_SOURCE_TARGET` - price
- `CONNECTION_PRICE_TARGET_SOURCE` - price

Keep (computed):

- `CONNECTION_POWER_SOURCE_TARGET` - power flow
- `CONNECTION_POWER_TARGET_SOURCE` - power flow
- `CONNECTION_POWER_ACTIVE` - net power
- `CONNECTION_SHADOW_POWER_MAX_*` - shadow prices
- `CONNECTION_TIME_SLICE` - shadow price

### From `elements/battery.py` outputs()

Battery is more complex due to sections. Review:

- Section charge/discharge prices may be computed from early_charge_incentive
- Keep SOC outputs (computed)
- Keep power outputs (computed)
- Keep shadow prices (computed)

## Implementation Steps

### 1. Update model/power_connection.py

```python
def outputs(self) -> Mapping[PowerConnectionOutputName, OutputData]:
    """Return output specifications for the connection.

    Only returns computed values from optimization.
    Input parameters (prices, limits) are exposed via input entities.
    """
    outputs: dict[PowerConnectionOutputName, OutputData] = {
        CONNECTION_POWER_SOURCE_TARGET: OutputData(...),  # LP variable
        CONNECTION_POWER_TARGET_SOURCE: OutputData(...),  # LP variable
    }

    # Shadow prices (only if constraints exist)
    for constraint_name in self._constraints:
        outputs[constraint_name] = OutputData(
            type=OUTPUT_TYPE_SHADOW_PRICE,
            unit="$/kW",
            values=self.extract_values(self._constraints[constraint_name]),
        )

    return outputs
```

### 2. Update element adapter outputs()

Remove lines that echo input values:

```python
# REMOVE these patterns:
if CONNECTION_POWER_MAX_SOURCE_TARGET in connection:
    grid_outputs[GRID_POWER_MAX_IMPORT] = connection[CONNECTION_POWER_MAX_SOURCE_TARGET]

if CONNECTION_PRICE_SOURCE_TARGET in connection:
    grid_outputs[GRID_PRICE_IMPORT] = connection[CONNECTION_PRICE_SOURCE_TARGET]
```

### 3. Update OUTPUT_NAMES constants

Remove echoed output names from frozensets:

```python
# Before:
GRID_OUTPUT_NAMES = frozenset(
    (
        GRID_POWER_IMPORT,
        GRID_POWER_EXPORT,
        GRID_POWER_MAX_IMPORT,  # REMOVE
        GRID_POWER_MAX_EXPORT,  # REMOVE
        GRID_PRICE_IMPORT,  # REMOVE
        GRID_PRICE_EXPORT,  # REMOVE
        ...,
    )
)

# After:
GRID_OUTPUT_NAMES = frozenset(
    (
        GRID_POWER_IMPORT,
        GRID_POWER_EXPORT,
        GRID_POWER_ACTIVE,
        GRID_POWER_MAX_IMPORT_PRICE,
        GRID_POWER_MAX_EXPORT_PRICE,
    )
)
```

### 4. Update translations/en.json

Remove translation keys for removed outputs. These values are now exposed as input entities with their own translations.

### 5. Update tests

- Update test_data/elements/\*.py to remove expected echoed outputs
- Update test cases that check for removed outputs

## Testing Considerations

- Verify optimization still works without echoed outputs
- Verify input entities expose the values that were previously echoed
- Verify shadow prices still work (they depend on constraints, not echoed values)
- Verify visualization/diagnostics still function

## Acceptance Criteria

1. Model outputs() only returns computed values
2. Element adapter outputs() only maps computed values
3. No unused translation keys
4. Tests updated and passing
5. Input entities expose all previously-echoed values

## Notes

This is a breaking change for any external code relying on echoed output sensors. Since we're treating this as greenfield development, that's acceptable.
