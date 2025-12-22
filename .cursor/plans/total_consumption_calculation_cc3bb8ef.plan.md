# Calculate Total Consumption from Energy Flows

## Problem

The current implementation only fetches **grid import** data, which doesn't represent total household consumption. Users with solar + battery see near-zero values during the day when solar covers their load.

## Solution

Modify the historical load loader to calculate total consumption using the formula:

```javascript
Total Load = Grid Import + Solar Production - Grid Export
```

This accounts for:

- Power drawn from the grid
- Solar power consumed locally (production minus what was exported)

## Implementation

### 1. Update `get_energy_consumption_entities` to return categorized entities

Instead of returning just a list of entity IDs, return a dict with entity categories:

```python
async def get_energy_entities(hass: HomeAssistant) -> dict[str, list[str]]:
    """Get energy entity IDs from the Energy dashboard configuration."""
    # Returns:
    # {
    #   "grid_import": ["sensor.grid_import_energy"],
    #   "grid_export": ["sensor.grid_export_energy"],
    #   "solar": ["sensor.solar_production_energy"],
    # }
```

Extract from the Energy Manager:

- Grid sources → `flow_from` → `stat_energy_from` (imports)
- Grid sources → `flow_to` → `stat_energy_to` (exports)
- Solar sources → `stat_energy_from` (production)

### 2. Update `build_forecast_from_history` to combine flows

Modify the function to accept categorized statistics and calculate:

```python
def build_forecast_from_history(
    statistics: dict[str, Mapping[str, Sequence[StatisticsRow]]],
    history_days: int,
) -> ForecastSeries:
    """
    For each hour:
      total_load = grid_import + solar_production - grid_export
    """
```



### 3. Update the loader's `load` method

Update to use the new categorized entity fetching and calculation.

## Files to Modify