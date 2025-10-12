# Data Update Coordinator

HAEO uses Home Assistant's `DataUpdateCoordinator` pattern.

## Purpose

The coordinator:

- Manages optimization cycles
- Loads data from sensors
- Builds network model
- Runs LP solver
- Updates sensors with results

## Implementation

Located in `coordinator.py`:

```python
class HaeoDataUpdateCoordinator(DataUpdateCoordinator):
    async def _async_update_data(self):
        # Load current data
        # Build network
        # Run optimization
        # Return results
        pass
```

## Update Interval

Determined by integration, not user-configurable (following HA best practices).

See `coordinator.py` for full implementation.
